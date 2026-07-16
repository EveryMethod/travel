"""LangGraph agent for MCP-backed trip planning."""

import json
import re
from collections.abc import Iterator
from typing import Any, TypedDict

from langgraph.graph import END, START, StateGraph
from pydantic import ValidationError

from src.app.models.trip import TripPlanRequest, TripPlanResponse
from src.app.services.llm_service import generate_json
from src.app.services.mcp_client import call_tool


class TripPlannerState(TypedDict, total=False):
    request: TripPlanRequest
    context: dict[str, Any]
    constraints: dict[str, Any]
    draft: dict[str, Any]
    plan: TripPlanResponse


_ROUTE_LEG_MAX_ITEMS_PER_DAY = 4
_ROUTE_LEG_RISK_SECONDS = 45 * 60


def plan_trip_with_graph(request: TripPlanRequest) -> TripPlanResponse:
    final_state = _trip_planner_graph.invoke({"request": request})
    return final_state["plan"]


def stream_trip_with_graph(request: TripPlanRequest) -> Iterator[dict[str, Any]]:
    state: TripPlannerState = {"request": request}
    yield {"type": "status", "message": "正在整理旅行需求..."}
    state.update(_normalize_request(state))
    yield {"type": "status", "message": "正在查询目的地、天气和路线数据..."}
    state.update(_collect_map_context(state))
    yield {"type": "context", "data": _compact_context(state["context"])}
    yield {"type": "status", "message": "正在搜索门票、车票和预算参考..."}
    state.update(_collect_price_context(state))
    yield {"type": "status", "message": "正在整理预算和偏好约束..."}
    state.update(_check_constraints(state))
    yield {"type": "status", "message": "正在让大模型生成路线草案..."}
    state.update(_draft_plan(state))
    yield {"type": "status", "message": "正在校验并整理行程格式..."}
    state.update(_validate_plan(state))
    yield {"type": "status", "message": "正在检查预算和行程可执行性..."}
    state.update(_review_plan(state))
    yield {"type": "plan", "data": state["plan"].model_dump()}
    yield {"type": "done"}


def _build_graph():
    graph = StateGraph(TripPlannerState)
    graph.add_node("normalize_request", _normalize_request)
    graph.add_node("collect_map_context", _collect_map_context)
    graph.add_node("collect_price_context", _collect_price_context)
    graph.add_node("check_constraints", _check_constraints)
    graph.add_node("draft_plan", _draft_plan)
    graph.add_node("validate_plan", _validate_plan)
    graph.add_node("review_plan", _review_plan)
    graph.add_edge(START, "normalize_request")
    graph.add_edge("normalize_request", "collect_map_context")
    graph.add_edge("collect_map_context", "collect_price_context")
    graph.add_edge("collect_price_context", "check_constraints")
    graph.add_edge("check_constraints", "draft_plan")
    graph.add_edge("draft_plan", "validate_plan")
    graph.add_edge("validate_plan", "review_plan")
    graph.add_edge("review_plan", END)
    return graph.compile()


def _normalize_request(state: TripPlannerState) -> TripPlannerState:
    request = state["request"]
    request.destination = request.destination.strip()
    request.origin = request.origin.strip()
    request.budget = request.budget.strip()
    request.budget_breakdown.transport = request.budget_breakdown.transport.strip()
    request.budget_breakdown.hotel = request.budget_breakdown.hotel.strip()
    request.budget_breakdown.food = request.budget_breakdown.food.strip()
    request.budget_breakdown.tickets = request.budget_breakdown.tickets.strip()
    request.start_date = request.start_date.strip()
    request.end_date = request.end_date.strip()
    request.must_see = request.must_see.strip()
    request.avoid = request.avoid.strip()
    request.notes = request.notes.strip()
    return {"request": request}


def _collect_map_context(state: TripPlannerState) -> TripPlannerState:
    request = state["request"]
    keywords = sorted({keyword for style in request.travel_style for keyword in _style_keywords(style)})
    context: dict[str, Any] = {"pois": [], "weather": None, "routes": []}

    for keyword in keywords:
        context["pois"].append(
            call_tool(
                "amap_search_poi",
                {"city": request.destination, "keywords": keyword, "offset": 8},
            )
        )

    context["weather"] = call_tool("amap_weather", {"city": request.destination})

    if request.origin:
        origin = call_tool("amap_geocode", {"address": request.origin})
        destination = call_tool("amap_geocode", {"address": request.destination})
        origin_location = _first_location(origin)
        destination_location = _first_location(destination)
        if origin_location and destination_location:
            context["routes"].append(
                call_tool(
                    "amap_route_distance",
                    {"origin": origin_location, "destination": destination_location},
                )
            )

    return {"request": request, "context": context}


def _collect_price_context(state: TripPlannerState) -> TripPlannerState:
    request = state["request"]
    context = state["context"]
    queries = [
        f"{request.destination} 景点 门票 价格",
        f"{request.origin} 到 {request.destination} 车票 高铁 机票 价格",
        f"{request.destination} 交通 地铁 打车 价格",
    ]
    for poi in _compact_context(context)["pois"][:3]:
        queries.append(f"{poi.get('name')} 门票 价格 预约")

    prices = []
    for query in queries[:5]:
        try:
            prices.append(call_tool("ticket_price_search", {"query": query, "max_results": 2}))
        except Exception:
            prices.append({"query": query, "results": []})

    context["prices"] = prices
    return {"request": request, "context": context}


def _check_constraints(state: TripPlannerState) -> TripPlannerState:
    request = state["request"]
    parsed_budget = _parsed_budget_breakdown(request)
    fallback_budget = _parse_budget_amount(request.budget)
    budget_total = sum(parsed_budget.values()) if parsed_budget else fallback_budget
    constraints = {
        "budget_breakdown": request.budget_breakdown.model_dump(),
        "parsed_budget": parsed_budget,
        "budget_total": budget_total,
        "pace": request.pace,
        "pace_rule": _pace_rule(request.pace),
        "companions": request.companions,
        "companions_rule": _companions_rule(request.companions),
        "must_see": request.must_see,
        "avoid": request.avoid,
    }
    return {"request": request, "context": state["context"], "constraints": constraints}


def _parse_budget_amount(value: str) -> int | None:
    numbers = re.findall(r"\d+(?:\.\d+)?", value.replace(",", ""))
    if not numbers:
        return None
    return int(max(float(number) for number in numbers))


def _parsed_budget_breakdown(request: TripPlanRequest) -> dict[str, int]:
    parsed: dict[str, int] = {}
    for key, value in request.budget_breakdown.model_dump().items():
        amount = _parse_budget_amount(str(value))
        if amount is not None:
            parsed[key] = amount
    return parsed


def _pace_rule(pace: str) -> str:
    return {
        "relaxed": "每天安排 2 到 3 个活动，减少跨区移动，保留休息时间。",
        "balanced": "每天安排 3 个左右活动，兼顾效率和休息。",
        "packed": "每天安排 3 到 4 个活动，但仍避免明显时间冲突和过度跨区。",
    }.get(pace, "每天安排 3 个左右活动，兼顾效率和休息。")


def _companions_rule(companions: str) -> str:
    return {
        "solo": "增加安全、夜间交通和独自出行提醒。",
        "couple": "保留慢节奏体验和适合两人停留的安排。",
        "friends": "安排可以灵活调整、适合集体行动的路线。",
        "family": "降低步行强度，增加休息和亲子友好提醒。",
        "seniors": "降低步行强度，减少赶路，增加休息和无障碍提醒。",
    }.get(companions, "安排可以灵活调整、适合集体行动的路线。")


def _draft_plan(state: TripPlannerState) -> TripPlannerState:
    request = state["request"]
    context = state["context"]
    constraints = state["constraints"]
    draft = generate_json(
        [
            {
                "role": "system",
                "content": (
                    "你是中文旅行规划 Agent。必须只输出 JSON object，字段严格匹配："
                    "trip_id,destination,summary,days,tips,disclaimer。"
                    "days 每项包含 day,date,title,weather,items,daily_budget,transport,notes。"
                    "items 每项包含 time,place,activity,estimated_cost,booking_hint,source_hint。"
                    "必须按具体日期和时间点安排行程，不要使用上午/下午/晚上作为固定字段。"
                    "价格只能使用搜索上下文中的参考信息或写约/区间/需查询官方渠道，不要编造精确实时票价。"
                    "必须优先满足 must_see，不安排 avoid。"
                    "必须按 pace_rule 控制每天活动数量，并按 companions_rule 调整强度和提醒。"
                    "预算建议必须参考 budget_breakdown；不确定价格写区间或需查询官方渠道。"
                ),
            },
            {
                "role": "user",
                "content": json.dumps(
                    {
                        "request": request.model_dump(),
                        "map_context": _compact_context(context),
                        "price_context": _compact_prices(context.get("prices")),
                        "constraints": {
                            "language": "zh-CN",
                            "days_count": request.days,
                            "date_range": [request.start_date, request.end_date],
                            "legacy_budget": request.budget,
                            **constraints,
                        },
                    },
                    ensure_ascii=False,
                ),
            },
        ]
    )
    return {"request": request, "context": context, "constraints": constraints, "draft": draft}


def _validate_plan(state: TripPlannerState) -> TripPlannerState:
    request = state["request"]
    draft = _normalize_plan_shape(state["draft"])

    try:
        plan = TripPlanResponse.model_validate(draft)
    except ValidationError as exc:
        repaired = generate_json(
            [
                {
                    "role": "system",
                    "content": "修复 JSON，使其严格符合 TripPlanResponse schema。只输出 JSON object。",
                },
                {
                    "role": "user",
                    "content": json.dumps(
                        {
                            "errors": [error.get("loc") for error in exc.errors()],
                            "bad_json": draft,
                            "required_days": request.days,
                        },
                        ensure_ascii=False,
                    ),
                },
            ]
        )
        plan = TripPlanResponse.model_validate(_normalize_plan_shape(repaired))

    plan.trip_id = plan.trip_id or f"llm-{_slugify(request.destination)}-{request.days}"
    plan.destination = plan.destination or request.destination
    plan.days = plan.days[: request.days]
    if len(plan.days) != request.days:
        raise ValueError("LLM returned an itinerary with the wrong number of days.")
    return {"request": request, "context": state.get("context", {}), "constraints": state.get("constraints", {}), "plan": plan}


def _review_plan(state: TripPlannerState) -> TripPlannerState:
    request = state["request"]
    plan = state["plan"]
    constraints = state.get("constraints", {})
    warnings: list[str] = []

    max_items = {"relaxed": 3, "balanced": 3, "packed": 4}.get(request.pace, 3)
    pace_label = {"relaxed": "慢游", "balanced": "适中", "packed": "紧凑"}.get(request.pace, "适中")
    for day in plan.days:
        if len(day.items) > max_items:
            warnings.append(f"第 {day.day} 天活动数量较多，可能不符合{pace_label}节奏。")
        times = [item.time.strip() for item in day.items if item.time.strip()]
        duplicate_times = sorted({time for time in times if times.count(time) > 1})
        if duplicate_times:
            warnings.append(f"第 {day.day} 天存在重复时间：{'、'.join(duplicate_times)}，出发前请调整顺序。")

    text = _plan_text(plan)
    missing_must_see = [term for term in _split_terms(str(constraints.get("must_see") or "")) if term not in text]
    if missing_must_see:
        warnings.append(f"必去地点未出现在路线中：{'、'.join(missing_must_see)}。")

    avoided = [term for term in _split_terms(str(constraints.get("avoid") or "")) if term in text]
    if avoided:
        warnings.append(f"路线中包含避开地点：{'、'.join(avoided)}，请确认是否替换。")

    budget_total = constraints.get("budget_total")
    estimated_cost = _estimate_plan_cost(plan)
    if isinstance(budget_total, int) and estimated_cost is not None and estimated_cost > budget_total * 1.15:
        warnings.append(f"可解析费用约 {estimated_cost} 元，已明显高于预算 {budget_total} 元，请压缩活动或提高预算。")

    warnings.extend(_review_route_legs(plan))

    for warning in warnings:
        if warning not in plan.tips:
            plan.tips.append(warning)

    return {"request": request, "context": state.get("context", {}), "constraints": constraints, "plan": plan}


def _normalize_plan_shape(value: dict[str, Any]) -> dict[str, Any]:
    for day in value.get("days", []):
        if isinstance(day.get("notes"), str):
            day["notes"] = [day["notes"]]
        day.setdefault("items", [])
        for item in day.get("items", []):
            item.setdefault("estimated_cost", "需查询官方渠道")
            item.setdefault("booking_hint", "出发前核实官方信息")
            item.setdefault("source_hint", "价格为搜索参考，需核实")
    return value


def _style_keywords(style: str) -> list[str]:
    return {
        "culture": ["博物馆", "历史街区", "文化景点"],
        "food": ["美食", "餐厅", "小吃"],
        "nature": ["公园", "自然风景", "观景点"],
        "family": ["亲子", "乐园", "博物馆"],
        "romantic": ["夜景", "咖啡", "老街"],
        "adventure": ["户外", "徒步", "近郊"],
        "relaxed": ["咖啡", "公园", "街区"],
    }.get(style, ["景点", "美食", "公园"])


def _first_location(data: dict[str, Any]) -> str:
    geocodes = data.get("geocodes") or []
    if not geocodes:
        return ""
    return str(geocodes[0].get("location") or "")


def _compact_context(context: dict[str, Any]) -> dict[str, Any]:
    pois = []
    for result in context.get("pois", []):
        for poi in result.get("pois", [])[:4]:
            pois.append(
                {
                    "name": poi.get("name"),
                    "type": poi.get("type"),
                    "address": poi.get("address"),
                    "location": poi.get("location"),
                }
            )
    return {
        "pois": pois[:12],
        "weather": _compact_weather(context.get("weather")),
        "routes": _compact_routes(context.get("routes")),
    }


def _compact_prices(data: Any) -> list[dict[str, Any]]:
    prices = []
    for result in data or []:
        items = []
        for item in result.get("results", [])[:3]:
            items.append(
                {
                    "title": item.get("title"),
                    "url": item.get("url"),
                    "content": str(item.get("content") or "")[:180],
                }
            )
        prices.append({"query": result.get("query"), "results": items})
    return prices


def _compact_weather(data: Any) -> list[dict[str, Any]]:
    if not isinstance(data, dict):
        return []
    return [
        {
            "city": live.get("city"),
            "weather": live.get("weather"),
            "temperature": live.get("temperature"),
            "winddirection": live.get("winddirection"),
            "windpower": live.get("windpower"),
        }
        for live in data.get("lives", [])[:2]
    ]


def _compact_routes(routes: Any) -> list[dict[str, Any]]:
    compacted = []
    for route in routes or []:
        paths = (route.get("route") or {}).get("paths") or []
        if paths:
            compacted.append({"distance": paths[0].get("distance"), "duration": paths[0].get("duration")})
    return compacted[:2]


def _split_terms(value: str) -> list[str]:
    return [term.strip() for term in re.split(r"[,，、;；\n]+", value) if term.strip()]


def _plan_text(plan: TripPlanResponse) -> str:
    parts = [plan.destination, plan.summary, " ".join(plan.tips), plan.disclaimer]
    for day in plan.days:
        parts.extend([day.title, day.weather, day.daily_budget, day.transport, " ".join(day.notes)])
        for item in day.items:
            parts.extend([item.time, item.place, item.activity, item.estimated_cost, item.booking_hint, item.source_hint])
    return "\n".join(parts)


def _estimate_plan_cost(plan: TripPlanResponse) -> int | None:
    total = 0
    found = False
    for day in plan.days:
        for item in day.items:
            amount = _parse_budget_amount(item.estimated_cost)
            if amount is None:
                continue
            found = True
            total += amount
    return total if found else None


def _review_route_legs(plan: TripPlanResponse) -> list[str]:
    warnings: list[str] = []
    for day in plan.days:
        items = day.items[:_ROUTE_LEG_MAX_ITEMS_PER_DAY]
        locations = {
            place: _geocode_place(plan.destination, place)
            for place in {item.place.strip() for item in items if item.place.strip()}
        }
        for origin, destination in zip(items, items[1:]):
            origin_place = origin.place.strip()
            destination_place = destination.place.strip()
            if not origin_place or not destination_place:
                continue
            warning = _route_leg_warning(
                day.day,
                origin_place,
                destination_place,
                locations.get(origin_place, ""),
                locations.get(destination_place, ""),
            )
            if warning:
                warnings.append(warning)
    return warnings


def _geocode_place(destination: str, place: str) -> str:
    try:
        return _first_location(call_tool("amap_geocode", {"address": f"{destination}{place}"}))
    except Exception:
        return ""


def _route_leg_warning(
    day: int,
    origin_place: str,
    destination_place: str,
    origin: str,
    destination: str,
) -> str | None:
    if not origin or not destination:
        return None

    try:
        route = call_tool("amap_route_distance", {"origin": origin, "destination": destination})
    except Exception:
        return None

    seconds = _route_duration_seconds(route)
    if seconds is None or seconds <= _ROUTE_LEG_RISK_SECONDS:
        return None

    minutes = round(seconds / 60)
    return f"第 {day} 天 {origin_place} → {destination_place} 通勤约 {minutes} 分钟，建议拆到不同日期或删除其中一个。"


def _route_duration_seconds(data: dict[str, Any]) -> int | None:
    route = data.get("route") if isinstance(data, dict) else None
    if not isinstance(route, dict):
        return None
    paths = route.get("paths")
    if not isinstance(paths, list) or not paths or not isinstance(paths[0], dict):
        return None
    try:
        return int(float(str(paths[0].get("duration"))))
    except (TypeError, ValueError):
        return None


def _slugify(value: str) -> str:
    slug = re.sub(r"[^\w]+", "-", value.strip().lower(), flags=re.UNICODE).strip("-")
    return slug or "trip"


_trip_planner_graph = _build_graph()
