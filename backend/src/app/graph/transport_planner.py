"""Independent LangGraph workflow for intercity transport planning."""

import copy
import json
import math
import re
import time
from concurrent.futures import Future, ThreadPoolExecutor, as_completed
from datetime import date, datetime, time as clock_time, timedelta, timezone
from threading import Lock
from typing import Any, TypedDict
from uuid import uuid4
from zoneinfo import ZoneInfo

from langgraph.graph import END, START, StateGraph

from src.app.models.trip import (
    IntercityTransportPlan,
    TransportLeg,
    TransportOption,
    TransportSegment,
    TripPlanRequest,
)
from src.app.services.llm_service import generate_json
from src.app.services.mcp_client import call_tool


class TransportPlannerState(TypedDict, total=False):
    request: TripPlanRequest
    warnings: list[str]
    provider_results: dict[str, dict[str, Any]]
    provider_query_timestamps: dict[str, datetime]
    candidates: list[TransportOption]
    candidate_timestamps: dict[str, datetime]
    recommendation: dict[str, str | None]
    plan: IntercityTransportPlan
    valid_dates: tuple[date, date] | None
    refresh_scope: str | None


_CACHE_TTL_SECONDS = 180
_SHANGHAI = ZoneInfo("Asia/Shanghai")
# ponytail: process-local TTL is enough until multiple replicas need a shared cache.
_transport_cache: dict[str, tuple[float, datetime, dict[str, Any]]] = {}
_transport_cache_lock = Lock()
_transport_inflight: dict[str, Future[tuple[dict[str, Any], datetime]]] = {}


def clear_transport_cache() -> None:
    with _transport_cache_lock:
        _transport_cache.clear()


def _shanghai_today() -> date:
    return datetime.now(_SHANGHAI).date()


def plan_transport_with_graph(
    request: TripPlanRequest, *, force_refresh: bool = False
) -> IntercityTransportPlan | None:
    copied = request.model_copy(deep=True)
    copied.origin = copied.origin.strip()
    copied.destination = copied.destination.strip()
    if not copied.origin or copied.origin == copied.destination:
        return None
    return _transport_planner_graph.invoke(
        {"request": copied, "refresh_scope": uuid4().hex if force_refresh else None}
    )["plan"]


def normalize_transport_request(state: TransportPlannerState) -> TransportPlannerState:
    request = state["request"]
    request.origin = request.origin.strip()
    request.destination = request.destination.strip()
    request.start_date = request.start_date.strip()
    request.end_date = request.end_date.strip()
    warnings: list[str] = []
    valid_dates: tuple[date, date] | None = None
    try:
        start = date.fromisoformat(request.start_date)
        end = date.fromisoformat(request.end_date)
        if start.isoformat() != request.start_date or end.isoformat() != request.end_date or end < start:
            raise ValueError
        valid_dates = start, end
    except ValueError:
        warnings.append("出行日期缺失或格式无效，已停用实时航班和火车查询。")
    return {"request": request, "warnings": warnings, "valid_dates": valid_dates}


def collect_transport_offers(state: TransportPlannerState) -> TransportPlannerState:
    request = state["request"]
    warnings = list(state.get("warnings", []))
    valid_dates = state.get("valid_dates")
    refresh_scope = state.get("refresh_scope")
    today = _shanghai_today()

    def flight() -> tuple[dict[str, Any], datetime, list[str]]:
        if not valid_dates:
            return _estimate("flight", request, "日期无效，航班仅提供搜索估算。", refresh_scope)
        arguments = {
            "origin": request.origin,
            "destination": request.destination,
            "departure_date": request.start_date,
            "return_date": request.end_date,
            **request.travelers.model_dump(),
        }
        return _provider_or_estimate(
            "flight",
            "航班",
            ("juhe_flight_offer_search", "amadeus_flight_offer_search"),
            arguments,
            request,
            refresh_scope,
        )

    def train() -> tuple[dict[str, Any], datetime, list[str]]:
        if not valid_dates:
            return _estimate("rail", request, "日期无效，火车仅提供搜索估算。", refresh_scope)
        if not all(today <= value <= today + timedelta(days=15) for value in valid_dates):
            return _estimate(
                "rail", request, "火车供应商仅支持未来15天查询，已改用搜索估算。", refresh_scope
            )
        try:
            outbound, outbound_at = _cached_call(
                "juhe_train_offer_search",
                {"origin": request.origin, "destination": request.destination, "date": request.start_date},
                refresh_scope=refresh_scope,
            )
            returning, return_at = _cached_call(
                "juhe_train_offer_search",
                {"origin": request.destination, "destination": request.origin, "date": request.end_date},
                refresh_scope=refresh_scope,
            )
            outbound_offers = outbound.get("offers")
            return_offers = returning.get("offers")
            if not isinstance(outbound_offers, list) or not isinstance(return_offers, list):
                return {"outbound": outbound, "return": returning}, min(outbound_at, return_at), []
            if not outbound_offers or not return_offers:
                raise ValueError("no round-trip rail offers")
            return {"outbound": outbound, "return": returning}, min(outbound_at, return_at), []
        except Exception:
            return _estimate("rail", request, "火车供应商查询失败，已改用搜索估算。", refresh_scope)

    def drive() -> tuple[dict[str, Any], datetime, list[str]]:
        try:
            origin, origin_at = _cached_call(
                "amap_geocode", {"address": request.origin}, refresh_scope=refresh_scope
            )
            destination, destination_at = _cached_call(
                "amap_geocode", {"address": request.destination}, refresh_scope=refresh_scope
            )
            origin_location = _first_location(origin)
            destination_location = _first_location(destination)
            if not origin_location or not destination_location:
                raise ValueError("geocode failed")
            route, route_at = _cached_call(
                "amap_route_distance",
                {"origin": origin_location, "destination": destination_location},
                refresh_scope=refresh_scope,
            )
            return route, min(origin_at, destination_at, route_at), []
        except Exception:
            return _estimate("drive", request, "驾车路线查询失败，已改用搜索估算。", refresh_scope)

    results: dict[str, dict[str, Any]] = {}
    timestamps: dict[str, datetime] = {}
    outcomes: dict[str, tuple[dict[str, Any], datetime, list[str]] | Exception] = {}
    with ThreadPoolExecutor(max_workers=3) as executor:
        futures = {executor.submit(function): mode for mode, function in (("flight", flight), ("rail", train), ("drive", drive))}
        for future in as_completed(futures):
            mode = futures[future]
            try:
                outcomes[mode] = future.result()
            except Exception as exc:
                outcomes[mode] = exc
    for mode in ("flight", "rail", "drive"):
        outcome = outcomes[mode]
        if isinstance(outcome, Exception):
            warnings.append(f"{_mode_name(mode)}查询失败，未获得可用估算。")
        else:
            result, queried_at, mode_warnings = outcome
            if isinstance(result, dict):
                results[mode] = result
                timestamps[mode] = queried_at
                warnings.extend(mode_warnings)
    return {
        "request": request,
        "warnings": warnings,
        "provider_results": results,
        "provider_query_timestamps": timestamps,
    }


def shortlist_options(state: TransportPlannerState) -> TransportPlannerState:
    request = state["request"]
    results = state.get("provider_results", {})
    warnings = list(state.get("warnings", []))
    candidates: list[TransportOption] = []
    timestamps: dict[str, datetime] = {}
    for mode in ("flight", "rail", "drive"):
        result = results.get(mode)
        if not result:
            continue
        malformed = False
        try:
            if result.get("estimate_mode"):
                options = [_estimate_option(mode, result)]
            elif mode == "flight":
                options, malformed = _flight_options(result, request)
                options = _representative_flights(options)
            elif mode == "rail":
                options, malformed = _rail_options(result, request)
            else:
                options = [_drive_option(result)]
        except Exception:
            options, malformed = [], True
        if malformed:
            warnings.append(f"{_mode_name(mode)}供应商数据格式无效，已跳过。")
        for option in options:
            candidates.append(option)
            if queried_at := state.get("provider_query_timestamps", {}).get(mode):
                timestamps[option.id] = queried_at

    deduplicated: list[TransportOption] = []
    seen: set[tuple[str, tuple[str, ...], tuple[str, ...]]] = set()
    for option in sorted(candidates, key=lambda option: _candidate_rank(option, request.travelers.adults)):
        identity = (option.mode, _services(option.outbound), _services(option.return_leg))
        if identity not in seen:
            seen.add(identity)
            deduplicated.append(option)
    return {"warnings": warnings, "candidates": deduplicated[:5], "candidate_timestamps": timestamps}


def recommend_option(state: TransportPlannerState) -> TransportPlannerState:
    candidates = state.get("candidates", [])
    fallback = {
        "recommended_option_id": candidates[0].id if candidates else None,
        "recommendation_reason": "按价格、时长、换乘和数据质量综合排序。" if candidates else "",
    }
    if not candidates:
        return {"recommendation": fallback}
    request = state["request"]
    try:
        response = generate_json(
            [
                {
                    "role": "system",
                    "content": "只能输出 recommended_option_id 和 recommendation_reason。不得新增或修改任何交通事实。",
                },
                {
                    "role": "user",
                    "content": json.dumps(
                        {
                            "candidates": [candidate.model_dump(mode="json") for candidate in candidates],
                            "budget": request.budget,
                            "travelers": request.travelers.model_dump(),
                            "pace": request.pace,
                            "companions": request.companions,
                            "notes": request.notes,
                        },
                        ensure_ascii=False,
                    ),
                },
            ]
        )
        recommended_id = response.get("recommended_option_id") if isinstance(response, dict) else None
        reason = response.get("recommendation_reason") if isinstance(response, dict) else None
        if recommended_id not in {candidate.id for candidate in candidates} or not isinstance(reason, str):
            return {"recommendation": fallback}
        return {"recommendation": {"recommended_option_id": recommended_id, "recommendation_reason": reason}}
    except Exception:
        return {"recommendation": fallback}


def validate_transport_plan(state: TransportPlannerState) -> TransportPlannerState:
    candidates = state.get("candidates", [])
    recommendation = state.get("recommendation", {})
    recommended_id = recommendation.get("recommended_option_id")
    selected = next((candidate for candidate in candidates if candidate.id == recommended_id), None)
    options = [selected] if selected else []
    remaining = [candidate for candidate in candidates if candidate is not selected]
    used_modes = {selected.mode} if selected else set()
    for candidate in remaining:
        if candidate.mode not in used_modes and len(options) < 3:
            options.append(candidate)
            used_modes.add(candidate.mode)
    options.extend(candidate for candidate in remaining if candidate not in options)
    options = options[:3]
    candidate_timestamps = state.get("candidate_timestamps", {})
    represented = [candidate_timestamps[option.id] for option in options if option.id in candidate_timestamps]
    collected = list(state.get("provider_query_timestamps", {}).values())
    searched_at = min(represented or collected or [datetime.now(timezone.utc)])
    ready_at, depart_by = _transport_window(selected) if selected else (None, None)
    plan = IntercityTransportPlan(
        origin=state["request"].origin,
        destination=state["request"].destination,
        recommended_option_id=selected.id if selected else None,
        recommendation_reason=str(recommendation.get("recommendation_reason") or ""),
        options=options,
        destination_ready_at=ready_at,
        destination_depart_by=depart_by,
        searched_at=searched_at,
        warnings=list(dict.fromkeys(state.get("warnings", []))),
    )
    return {"plan": plan}


def _build_graph():
    graph = StateGraph(TransportPlannerState)
    graph.add_node("normalize_transport_request", normalize_transport_request)
    graph.add_node("collect_transport_offers", collect_transport_offers)
    graph.add_node("shortlist_options", shortlist_options)
    graph.add_node("recommend_option", recommend_option)
    graph.add_node("validate_transport_plan", validate_transport_plan)
    graph.add_edge(START, "normalize_transport_request")
    graph.add_edge("normalize_transport_request", "collect_transport_offers")
    graph.add_edge("collect_transport_offers", "shortlist_options")
    graph.add_edge("shortlist_options", "recommend_option")
    graph.add_edge("recommend_option", "validate_transport_plan")
    graph.add_edge("validate_transport_plan", END)
    return graph.compile()


def _transport_window(option: TransportOption) -> tuple[datetime | None, datetime | None]:
    arrival_buffer, departure_buffer = {
        "flight": (90, 120),
        "rail": (45, 45),
        "drive": (30, 30),
    }[option.mode]
    ready_at = option.outbound.arrival_at + timedelta(minutes=arrival_buffer) if option.outbound.arrival_at else None
    depart_by = option.return_leg.departure_at - timedelta(minutes=departure_buffer) if option.return_leg.departure_at else None
    return ready_at, depart_by


def _cached_call(
    name: str, arguments: dict[str, Any], *, refresh_scope: str | None = None
) -> tuple[dict[str, Any], datetime]:
    key = _cache_key(name, arguments)
    inflight_key = key if refresh_scope is None else f"{key}:refresh:{refresh_scope}"
    with _transport_cache_lock:
        now = time.monotonic()
        _prune_transport_cache(now)
        cached = _transport_cache.get(key) if refresh_scope is None else None
        if cached and now - cached[0] < _CACHE_TTL_SECONDS:
            return copy.deepcopy(cached[2]), cached[1]
        inflight = _transport_inflight.get(inflight_key)
        owner = inflight is None
        if owner:
            inflight = Future()
            _transport_inflight[inflight_key] = inflight
    if not owner:
        result, queried_at = inflight.result()
        return copy.deepcopy(result), queried_at
    try:
        result = call_tool(name, arguments)
        if not isinstance(result, dict):
            raise TypeError("tool result must be an object")
        queried_at = datetime.now(timezone.utc)
        with _transport_cache_lock:
            stored = copy.deepcopy(result)
            _transport_cache[key] = (time.monotonic(), queried_at, stored)
            inflight.set_result((stored, queried_at))
            _transport_inflight.pop(inflight_key, None)
        return copy.deepcopy(result), queried_at
    except BaseException as exc:
        with _transport_cache_lock:
            inflight.set_exception(exc)
            _transport_inflight.pop(inflight_key, None)
        raise


def _cache_key(name: str, arguments: dict[str, Any]) -> str:
    return f"{name}:{json.dumps(arguments, ensure_ascii=False, sort_keys=True, separators=(',', ':'))}"


def _prune_transport_cache(now: float) -> None:
    expired = [key for key, cached in _transport_cache.items() if now - cached[0] >= _CACHE_TTL_SECONDS]
    for key in expired:
        del _transport_cache[key]


def _provider_or_estimate(
    mode: str,
    label: str,
    tools: tuple[str, ...],
    arguments: dict[str, Any],
    request: TripPlanRequest,
    refresh_scope: str | None,
) -> tuple[dict[str, Any], datetime, list[str]]:
    for tool in tools:
        try:
            result, queried_at = _cached_call(tool, arguments, refresh_scope=refresh_scope)
            offers = result.get("offers")
            if isinstance(offers, list) and offers and _flight_options(result, request)[0]:
                return result, queried_at, []
        except Exception:
            continue
    return _estimate(
        mode, request, f"{label}供应商查询失败，已改用搜索估算。", refresh_scope
    )


def _estimate(
    mode: str, request: TripPlanRequest, warning: str, refresh_scope: str | None
) -> tuple[dict[str, Any], datetime, list[str]]:
    result, queried_at = _cached_call(
        "ticket_price_search",
        {"query": f"{request.origin} 到 {request.destination} 往返{_mode_name(mode)}价格 元", "max_results": 3},
        refresh_scope=refresh_scope,
    )
    return {"estimate_mode": mode, "search": result}, queried_at, [warning]


def _estimate_option(mode: str, result: dict[str, Any]) -> TransportOption:
    return TransportOption(
        id=f"estimate-{mode}",
        mode=mode,
        provider="tavily",
        data_quality="estimate",
        estimated_price_range=_extract_yuan_price(result.get("search", {})),
        outbound=TransportLeg(direction="outbound"),
        return_leg=TransportLeg(direction="return"),
        booking_hint="价格和班次需查询供应商渠道。",
    )


def _flight_options(result: dict[str, Any], request: TripPlanRequest) -> tuple[list[TransportOption], bool]:
    options: list[TransportOption] = []
    offers = result.get("offers")
    if not isinstance(offers, list):
        return [], True
    rejected = False
    for offer in offers:
        if not isinstance(offer, dict) or not isinstance(offer.get("itineraries"), list) or len(offer["itineraries"]) != 2:
            rejected = True
            continue
        try:
            price = _number(offer.get("total_price"))
            if price is None or price <= 0:
                raise ValueError("flight price is invalid")
            outbound = _flight_leg("outbound", offer["itineraries"][0], request.start_date)
            returning = _flight_leg("return", offer["itineraries"][1], request.end_date)
            options.append(
                TransportOption(
                    id=f"flight-{offer['id']}",
                    mode="flight",
                    provider=str(result.get("provider") or "amadeus"),
                    data_quality=result.get("data_quality", "estimate"),
                    total_price=str(offer.get("total_price") or ""),
                    currency=str(offer.get("currency") or "CNY"),
                    fare_details=[
                        detail.strip()
                        for detail in offer.get("fare_details", [])
                        if isinstance(detail, str) and detail.strip()
                    ]
                    if isinstance(offer.get("fare_details"), list)
                    else [],
                    outbound=outbound,
                    return_leg=returning,
                    booking_hint=(
                        "聚合数据为成人参考票价；实际价格和余位以航空公司确认页为准。"
                        if result.get("provider") == "juhe_flight"
                        else (
                            "飞常准报价仅适用于成人；价格和余位以航空公司确认页为准。"
                            if result.get("provider") == "variflight"
                            else "价格和余位以航空公司确认页为准。"
                        )
                    ),
                )
            )
        except Exception:
            rejected = True
            continue
    return options, rejected


def _flight_leg(direction: str, itinerary: dict[str, Any], expected_date: str) -> TransportLeg:
    if not isinstance(itinerary, dict) or not isinstance(itinerary.get("segments"), list):
        raise ValueError("flight itinerary is invalid")
    departure = _iso_datetime(itinerary.get("departure_at"))
    arrival = _iso_datetime(itinerary.get("arrival_at"))
    if departure.date().isoformat() != expected_date or not _chronology_is_valid(arrival, departure):
        raise ValueError("flight itinerary chronology is invalid")
    duration = _number(itinerary.get("duration_minutes"))
    transfer_count = itinerary.get("transfer_count")
    if duration is None or duration <= 0 or not duration.is_integer():
        raise ValueError("flight duration is invalid")
    if type(transfer_count) is not int or transfer_count < 0:
        raise ValueError("flight transfer count is invalid")
    segments: list[TransportSegment] = []
    for raw_segment in itinerary["segments"]:
        if not isinstance(raw_segment, dict):
            raise ValueError("flight segment is invalid")
        segment_departure = _iso_datetime(raw_segment.get("departure_at"))
        segment_arrival = _iso_datetime(raw_segment.get("arrival_at"))
        if not _chronology_is_valid(segment_arrival, segment_departure):
            raise ValueError("flight segment chronology is invalid")
        segments.append(
            TransportSegment(
                service_number=str(raw_segment.get("service_number") or ""),
                carrier=str(raw_segment.get("carrier") or ""),
                departure_at=segment_departure,
                arrival_at=segment_arrival,
                from_terminal=_endpoint(raw_segment.get("from_airport"), raw_segment.get("from_terminal")),
                to_terminal=_endpoint(raw_segment.get("to_airport"), raw_segment.get("to_terminal")),
            )
        )
    if not segments:
        raise ValueError("flight itinerary has no segments")
    if transfer_count != len(segments) - 1:
        raise ValueError("flight transfer count is inconsistent")
    if segments[0].departure_at != departure or segments[-1].arrival_at != arrival:
        raise ValueError("flight itinerary endpoints are inconsistent")
    if any(
        not _chronology_is_valid(current.departure_at, previous.arrival_at)
        and current.departure_at != previous.arrival_at
        for previous, current in zip(segments, segments[1:])
    ):
        raise ValueError("flight connection chronology is invalid")
    return TransportLeg(
        direction=direction,
        departure_at=departure,
        arrival_at=arrival,
        duration_minutes=int(duration),
        transfer_count=transfer_count,
        segments=segments,
    )


def _iso_datetime(value: Any) -> datetime:
    if not isinstance(value, str):
        raise ValueError("datetime is invalid")
    return datetime.fromisoformat(value)


def _chronology_is_valid(later: datetime, earlier: datetime) -> bool:
    if (later.utcoffset() is None) != (earlier.utcoffset() is None):
        return False
    # Amadeus returns local wall times without offsets; supplier duration is authoritative there.
    return later > earlier if later.utcoffset() is not None else True


def _endpoint(code: Any, terminal: Any) -> str:
    code_text = str(code).strip() if isinstance(code, str) else ""
    terminal_text = str(terminal).strip() if isinstance(terminal, str) else ""
    if code_text and terminal_text:
        return f"{code_text} {terminal_text if terminal_text.upper().startswith('T') else f'T{terminal_text}'}"
    return code_text or terminal_text


def _representative_flights(options: list[TransportOption]) -> list[TransportOption]:
    if not options:
        return []
    cheapest = min(options, key=lambda option: (_amount(option.total_price), option.id))
    fastest = min(options, key=lambda option: (_duration(option), _amount(option.total_price), option.id))
    least_transfers = min(
        options,
        key=lambda option: (
            option.outbound.transfer_count + option.return_leg.transfer_count,
            _duration(option),
            _amount(option.total_price),
            option.id,
        ),
    )
    return list({option.id: option for option in (cheapest, fastest, least_transfers)}.values())


def _rail_options(result: dict[str, Any], request: TripPlanRequest) -> tuple[list[TransportOption], bool]:
    outbound_result = result.get("outbound")
    return_result = result.get("return")
    if not isinstance(outbound_result, dict) or not isinstance(return_result, dict):
        return [], True
    outbound_offers = outbound_result.get("offers")
    return_offers = return_result.get("offers")
    if not isinstance(outbound_offers, list) or not isinstance(return_offers, list):
        return [], True
    outbound, outbound_rejected = _usable_trains(outbound_offers, "outbound", request.start_date)
    returning, return_rejected = _usable_trains(return_offers, "return", request.end_date)
    options: list[TransportOption] = []
    seen: set[str] = set()
    rejected = outbound_rejected or return_rejected
    outbound_by_strategy = _representative_trains(outbound, request.travelers.adults)
    return_by_strategy = _representative_trains(returning, request.travelers.adults)
    for strategy in ("earliest", "fastest", "cheapest"):
        outward, outward_leg = outbound_by_strategy[strategy]
        back, return_leg = return_by_strategy[strategy]
        try:
            outward_number = str(outward["service_number"]).strip()
            return_number = str(back["service_number"]).strip()
            if not outward_number or not return_number:
                raise ValueError("train number is invalid")
        except (KeyError, TypeError, ValueError):
            rejected = True
            continue
        option_id = f"rail-{outward_number}-{return_number}"
        if option_id in seen:
            continue
        seen.add(option_id)
        options.append(
            TransportOption(
                id=option_id,
                mode="rail",
                provider="juhe",
                data_quality="provider_live",
                fare_details=_fare_details("去程", outward) + _fare_details("返程", back),
                outbound=outward_leg,
                return_leg=return_leg,
                booking_hint="儿童票和婴儿票价请通过12306核实，余票以提交订单时为准。",
            )
        )
    return options, rejected


def _representative_trains(
    candidates: list[tuple[dict[str, Any], TransportLeg]], adults: int
) -> dict[str, tuple[dict[str, Any], TransportLeg]]:
    def service(candidate: tuple[dict[str, Any], TransportLeg]) -> str:
        return str(candidate[0].get("service_number") or "")

    def fare(candidate: tuple[dict[str, Any], TransportLeg]) -> float:
        prices = [
            _number(seat.get("price"))
            for seat in candidate[0].get("seats", [])
            if isinstance(seat, dict) and _eligible_regular_seat(seat)
        ]
        return min((price for price in prices if price is not None), default=float("inf")) * adults

    return {
        "earliest": min(
            candidates,
            key=lambda candidate: (
                candidate[1].arrival_at or datetime.max,
                candidate[1].duration_minutes or 10**9,
                fare(candidate),
                service(candidate),
            ),
        ),
        "fastest": min(
            candidates,
            key=lambda candidate: (
                candidate[1].duration_minutes or 10**9,
                fare(candidate),
                candidate[1].arrival_at or datetime.max,
                service(candidate),
            ),
        ),
        "cheapest": min(
            candidates,
            key=lambda candidate: (
                fare(candidate),
                candidate[1].duration_minutes or 10**9,
                candidate[1].arrival_at or datetime.max,
                service(candidate),
            ),
        ),
    }


def _usable_trains(
    offers: list[Any], direction: str, travel_date: str
) -> tuple[list[tuple[dict[str, Any], TransportLeg]], bool]:
    usable: list[tuple[dict[str, Any], TransportLeg]] = []
    rejected = False
    for offer in offers:
        try:
            if not isinstance(offer, dict) or offer.get("bookable") is not True:
                raise ValueError("train is not bookable")
            seats = offer.get("seats")
            if not isinstance(seats, list) or not any(isinstance(seat, dict) and _eligible_regular_seat(seat) for seat in seats):
                raise ValueError("train fare is invalid")
            usable.append((offer, _train_leg(direction, travel_date, offer)))
        except (KeyError, TypeError, ValueError):
            rejected = True
    return usable, rejected


def _train_leg(direction: str, travel_date: str, offer: dict[str, Any]) -> TransportLeg:
    departure = datetime.combine(date.fromisoformat(travel_date), clock_time.fromisoformat(offer["departure_time"]))
    arrival_time = clock_time.fromisoformat(offer["arrival_time"])
    parsed_duration = _clock_duration(offer.get("duration"))
    if parsed_duration is None or parsed_duration <= 0:
        raise ValueError("train duration is invalid")
    expected_arrival = departure + timedelta(minutes=parsed_duration)
    if (expected_arrival.hour, expected_arrival.minute) != (arrival_time.hour, arrival_time.minute):
        raise ValueError("train duration is inconsistent")
    arrival = datetime.combine(expected_arrival.date(), arrival_time)
    segment = TransportSegment(
        service_number=str(offer["service_number"]),
        carrier="中国铁路",
        departure_at=departure,
        arrival_at=arrival,
        from_terminal=str(offer.get("departure_station") or ""),
        to_terminal=str(offer.get("arrival_station") or ""),
    )
    return TransportLeg(
        direction=direction,
        departure_at=departure,
        arrival_at=arrival,
        duration_minutes=parsed_duration,
        segments=[segment],
    )


def _drive_option(result: dict[str, Any]) -> TransportOption:
    path = _first_route_path(result)
    duration_seconds = _number(path.get("duration"))
    if duration_seconds is None or duration_seconds <= 0:
        raise ValueError("drive duration is invalid")
    duration = int(duration_seconds // 60) or None
    return TransportOption(
        id="drive-0",
        mode="drive",
        provider="amap",
        data_quality="live",
        estimated_price_range="需按油耗和路桥费核算",
        outbound=TransportLeg(direction="outbound", duration_minutes=duration),
        return_leg=TransportLeg(direction="return", duration_minutes=duration),
        booking_hint="出发前复核实时路况、油价和过路费。",
    )


def _candidate_rank(option: TransportOption, adults: int) -> tuple[float, float, float, int, str]:
    quality = 0 if option.data_quality in {"live", "provider_live"} else 1
    if option.mode == "rail":
        legs = [
            [_number(seat["price"]) for detail in option.fare_details if detail.startswith(prefix) and (seat := _fare_detail_seat(detail)) and _eligible_regular_seat(seat)]
            for prefix in ("去程", "返程")
        ]
        amount = sum(min((price for price in prices if price is not None), default=float("inf")) for prices in legs) * adults
    else:
        if option.total_price:
            parsed_amount = _number(option.total_price)
            amount = parsed_amount if parsed_amount is not None and parsed_amount > 0 else float("inf")
        else:
            amount = _amount(option.estimated_price_range)
    transfers = option.outbound.transfer_count + option.return_leg.transfer_count
    return quality, amount, _duration(option), transfers, option.id


def _eligible_regular_seat(seat: dict[str, Any]) -> bool:
    name = str(seat.get("name") or "").strip()
    availability = str(seat.get("availability") or "").strip()
    if not name or any(label in name for label in ("商务", "特等", "无座")):
        return False
    if not availability or availability in {"0", "无", "售罄", "--", "需查询"} or "无" in availability:
        return False
    price = _number(seat.get("price"))
    return (not availability.isdigit() or int(availability) > 0) and price is not None and price > 0


def _fare_detail_seat(detail: str) -> dict[str, str] | None:
    match = re.fullmatch(r"(?:去程|返程) (.+) ¥(\S+) 余票(.*)", detail)
    return {"name": match.group(1), "price": match.group(2), "availability": match.group(3)} if match else None


def _fare_details(prefix: str, offer: dict[str, Any]) -> list[str]:
    return [
        f"{prefix} {seat['name']} ¥{seat['price']} 余票{seat.get('availability') or '需查询'}"
        for seat in offer.get("seats", [])
        if isinstance(seat, dict)
        and seat.get("name")
        and (price := _number(seat.get("price"))) is not None
        and price > 0
    ]


def _duration(option: TransportOption) -> float:
    durations = [option.outbound.duration_minutes, option.return_leg.duration_minutes]
    return float(sum(durations)) if all(value is not None for value in durations) else float("inf")


def _amount(value: str) -> float:
    text = value or ""
    if re.search(r"(?<!\d)-\s*\d", text):
        return float("inf")
    match = re.search(r"\d+(?:\.\d+)?", text)
    parsed = _number(match.group() if match else None)
    return parsed if parsed is not None and parsed > 0 else float("inf")


def _number(value: Any) -> float | None:
    if isinstance(value, bool):
        return None
    try:
        number = float(value)
    except (TypeError, ValueError):
        return None
    return number if math.isfinite(number) else None


def _clock_duration(value: Any) -> int | None:
    match = re.fullmatch(r"(\d{1,2}):(\d{2})", str(value or ""))
    return int(match.group(1)) * 60 + int(match.group(2)) if match and int(match.group(2)) < 60 else None


def _extract_yuan_price(result: dict[str, Any]) -> str:
    pattern = re.compile(
        r"(?<!\d)(?:(?:¥|￥|人民币)\s*\d{2,6}(?:\s*(?:-|~|至|到)\s*\d{2,6})?\s*元?|"
        r"\d{2,6}(?:\s*(?:-|~|至|到)\s*\d{2,6})?\s*元)(?!\d)"
    )
    results = result.get("results")
    for item in results if isinstance(results, list) else []:
        if not isinstance(item, dict):
            continue
        for field in ("title", "content"):
            text = item.get(field)
            if isinstance(text, str) and (match := pattern.search(text)):
                return re.sub(r"\s+", "", match.group())
    return "需查询供应商渠道"


def _first_location(result: dict[str, Any]) -> str:
    geocodes = result.get("geocodes")
    return str(geocodes[0].get("location") or "") if isinstance(geocodes, list) and geocodes and isinstance(geocodes[0], dict) else ""


def _first_route_path(result: dict[str, Any]) -> dict[str, Any]:
    route = result.get("route")
    paths = route.get("paths") if isinstance(route, dict) else None
    return paths[0] if isinstance(paths, list) and paths and isinstance(paths[0], dict) else {}


def _services(leg: TransportLeg) -> tuple[str, ...]:
    return tuple(segment.service_number for segment in leg.segments)


def _mode_name(mode: str) -> str:
    return {"flight": "航班", "rail": "火车", "drive": "驾车"}.get(mode, mode)


_transport_planner_graph = _build_graph()
