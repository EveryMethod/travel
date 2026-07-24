"""Small HTTP MCP-style gateway for travel supplier tools."""

import math
import re
import time
from datetime import date, datetime, timedelta
from threading import Lock
from typing import Any

import httpx
from fastapi import FastAPI, HTTPException

from src.app.core.config import settings
from src.app.core.tracing import trace_call

app = FastAPI(title="Travel MCP Gateway")

_amadeus_access_token = ""
_amadeus_access_token_expires_at = 0.0
_amadeus_token_lock = Lock()

_VARIFLIGHT_CITY_CODES = {
    "北京": "BJS",
    "上海": "SHA",
    "广州": "CAN",
    "深圳": "SZX",
    "成都": "CTU",
    "重庆": "CKG",
    "杭州": "HGH",
    "南京": "NKG",
    "武汉": "WUH",
    "西安": "SIA",
    "长沙": "CSX",
    "昆明": "KMG",
    "厦门": "XMN",
    "青岛": "TAO",
    "天津": "TSN",
    "郑州": "CGO",
    "三亚": "SYX",
    "海口": "HAK",
    "大连": "DLC",
    "沈阳": "SHE",
    "哈尔滨": "HRB",
    "济南": "TNA",
    "福州": "FOC",
    "南宁": "NNG",
    "贵阳": "KWE",
    "乌鲁木齐": "URC",
    "拉萨": "LXA",
    "呼和浩特": "HET",
    "银川": "INC",
    "兰州": "LHW",
    "太原": "TYN",
    "石家庄": "SJW",
    "合肥": "HFE",
    "南昌": "KHN",
    "宁波": "NGB",
    "温州": "WNZ",
    "珠海": "ZUH",
    "西双版纳": "JHG",
    "大理": "DLU",
    "桂林": "KWL",
    "烟台": "YNT",
    "泉州": "JJN",
    "长春": "CGQ",
    "西宁": "XNN",
    "香港": "HKG",
    "澳门": "MFM",
}


@app.post("/mcp/tools/{tool_name}")
def call_tool(tool_name: str, arguments: dict[str, Any]) -> dict[str, Any]:
    tools = {
        "amap_search_poi": _search_poi,
        "amap_geocode": _geocode,
        "amap_route_distance": _route_distance,
        "amap_weather": _weather,
        "amap_place_detail": _place_detail,
        "ticket_price_search": _ticket_price_search,
        "juhe_flight_offer_search": _juhe_flight_offer_search,
        "variflight_flight_offer_search": _variflight_flight_offer_search,
        "amadeus_flight_offer_search": _amadeus_flight_offer_search,
        "juhe_train_offer_search": _juhe_train_offer_search,
    }
    tool = tools.get(tool_name)
    if not tool:
        raise HTTPException(status_code=404, detail="Unknown MCP tool.")

    try:
        return trace_call(
            "tool.execute",
            tool_name,
            arguments,
            {"gateway": "travel-mcp", "source": _tool_source(tool_name)},
            lambda: tool(arguments),
        )
    except httpx.HTTPError as exc:
        raise HTTPException(status_code=502, detail="Supplier request failed.") from exc


def _tool_source(tool_name: str) -> str:
    if tool_name == "ticket_price_search":
        return "tavily"
    if tool_name.startswith("amadeus_"):
        return "amadeus"
    if tool_name.startswith("variflight_"):
        return "variflight"
    if tool_name.startswith("juhe_"):
        return "juhe"
    return "amap"


def _amap_get(path: str, params: dict[str, Any]) -> dict[str, Any]:
    if not settings.amap_api_key:
        raise HTTPException(status_code=500, detail="AMAP_API_KEY is not configured.")
    response = httpx.get(
        f"https://restapi.amap.com/v3/{path}",
        params={**params, "key": settings.amap_api_key, "output": "JSON"},
        timeout=settings.mcp_timeout_seconds,
    )
    response.raise_for_status()
    data = response.json()
    if data.get("status") != "1":
        raise HTTPException(status_code=502, detail=data.get("info", "AMap request failed."))
    return data


def _search_poi(arguments: dict[str, Any]) -> dict[str, Any]:
    return _amap_get(
        "place/text",
        {
            "keywords": arguments.get("keywords", ""),

            "city": arguments.get("city", ""),
            "types": arguments.get("types", ""),
            "offset": arguments.get("offset", 10),
            "page": 1,
        },
    )


def _geocode(arguments: dict[str, Any]) -> dict[str, Any]:
    return _amap_get("geocode/geo", {"address": arguments.get("address", ""), "city": arguments.get("city", "")})


def _route_distance(arguments: dict[str, Any]) -> dict[str, Any]:
    return _amap_get(
        "direction/driving",
        {
            "origin": arguments.get("origin", ""),
            "destination": arguments.get("destination", ""),
        },
    )


def _weather(arguments: dict[str, Any]) -> dict[str, Any]:
    return _amap_get("weather/weatherInfo", {"city": arguments.get("city", ""), "extensions": "base"})


def _place_detail(arguments: dict[str, Any]) -> dict[str, Any]:
    return _amap_get("place/detail", {"id": arguments.get("id", "")})


def _ticket_price_search(arguments: dict[str, Any]) -> dict[str, Any]:
    if not settings.tavily_api_key:
        return {"query": arguments.get("query", ""), "results": []}

    response = httpx.post(
        settings.tavily_search_url,
        json={
            "api_key": settings.tavily_api_key,
            "query": arguments.get("query", ""),
            "search_depth": "basic",
            "max_results": arguments.get("max_results", 5),
        },
        timeout=settings.mcp_timeout_seconds,
    )
    response.raise_for_status()
    return response.json()


def _juhe_train_offer_search(arguments: dict[str, Any]) -> dict[str, Any]:
    origin = _required_text(arguments, "origin")
    destination = _required_text(arguments, "destination")
    travel_date = _required_iso_date(arguments, "date")
    train_filter = arguments.get("filter", "")
    if not isinstance(train_filter, str):
        raise HTTPException(status_code=422, detail="filter is invalid.")
    if not settings.juhe_train_api_key:
        raise HTTPException(status_code=500, detail="JUHE_TRAIN_API_KEY is not configured.")
    response = httpx.get(
        settings.juhe_train_api_url,
        params={
            "key": settings.juhe_train_api_key,
            "search_type": 1,
            "departure_station": origin,
            "arrival_station": destination,
            "date": travel_date,
            "filter": train_filter.strip(),
            "enable_booking": 2,
        },
        timeout=settings.mcp_timeout_seconds,
    )
    response.raise_for_status()
    data = _supplier_json(response)
    if data.get("error_code") != 0:
        raise HTTPException(status_code=502, detail="Juhe request failed.")
    trains = _dict_items(data.get("result") or [])
    offers = [
        normalized
        for train in trains
        if (normalized := _normalize_juhe_train(train)) is not None
    ]
    return {
        "provider": "juhe",
        "data_quality": "provider_live",
        "offers": offers,
    }


def _normalize_juhe_train(train: dict[str, Any]) -> dict[str, Any] | None:
    service_number = _supplier_text(train.get("train_no"))
    departure_station = _supplier_text(train.get("departure_station"))
    arrival_station = _supplier_text(train.get("arrival_station"))
    departure_time = _supplier_text(train.get("departure_time"))
    arrival_time = _supplier_text(train.get("arrival_time"))
    if not all((service_number, departure_station, arrival_station, departure_time, arrival_time)):
        return None
    seats = [
        {
            "name": name,
            "price": _scalar_text(seat.get("price")),
            "availability": _scalar_text(seat.get("num")),
        }
        for seat in _dict_items(train.get("prices") or [])
        if (name := _supplier_text(seat.get("seat_name")))
    ]
    return {
        "service_number": service_number,
        "departure_station": departure_station,
        "arrival_station": arrival_station,
        "departure_time": departure_time,
        "arrival_time": arrival_time,
        "duration": _supplier_text(train.get("duration")),
        "bookable": train.get("enable_booking") == "Y",
        "seats": seats,
    }


def _juhe_flight_offer_search(arguments: dict[str, Any]) -> dict[str, Any]:
    origin = _variflight_city_code(_required_text(arguments, "origin"))
    destination = _variflight_city_code(_required_text(arguments, "destination"))
    departure_date = _required_iso_date(arguments, "departure_date")
    return_date = _required_iso_date(arguments, "return_date")
    if return_date < departure_date:
        raise HTTPException(status_code=422, detail="return_date cannot be before departure_date.")
    adults = _passenger_count(arguments, "adults", 1, 1, 9)
    children = _passenger_count(arguments, "children", 0, 0, 8)
    infants = _passenger_count(arguments, "infants", 0, 0, 9)
    if infants > adults:
        raise HTTPException(status_code=422, detail="infants cannot exceed adults.")
    if not settings.juhe_flight_api_key:
        raise HTTPException(status_code=500, detail="JUHE_FLIGHT_API_KEY is not configured.")
    if children or infants:
        return {"provider": "juhe_flight", "data_quality": "provider_live", "offers": []}

    outbound = _juhe_flight_prices(origin, destination, departure_date, "去程")
    returning = _juhe_flight_prices(destination, origin, return_date, "返程")
    offers = []
    for outward in outbound[:5]:
        for inward in returning[:5]:
            total = (outward["price"] + inward["price"]) * adults
            offers.append(
                {
                    "id": f"{outward['service_number']}-{inward['service_number']}",
                    "total_price": _format_number(total),
                    "currency": "CNY",
                    "itineraries": [outward["itinerary"], inward["itinerary"]],
                    "fare_details": [outward["fare_detail"], inward["fare_detail"]],
                }
            )
    return {"provider": "juhe_flight", "data_quality": "provider_live", "offers": offers}


def _juhe_flight_prices(
    origin: str, destination: str, travel_date: str, direction: str
) -> list[dict[str, Any]]:
    response = httpx.get(
        settings.juhe_flight_api_url,
        params={
            "key": settings.juhe_flight_api_key,
            "departure": origin,
            "arrival": destination,
            "departureDate": travel_date,
            "maxSegments": "2",
        },
        timeout=settings.mcp_timeout_seconds,
    )
    response.raise_for_status()
    payload = _supplier_json(response)
    if payload.get("error_code") != 0:
        raise HTTPException(status_code=502, detail="Juhe flight request failed.")
    result = payload.get("result")
    flights = _dict_items(result.get("flightInfo")) if isinstance(result, dict) else []
    normalized = [
        offer
        for flight in flights
        if (offer := _normalize_juhe_flight(flight, direction)) is not None
    ]
    return sorted(normalized, key=lambda offer: offer["price"])


def _normalize_juhe_flight(flight: dict[str, Any], direction: str) -> dict[str, Any] | None:
    service_number = _supplier_text(flight.get("flightNo"))
    price = _positive_number(flight.get("ticketPrice"))
    duration = _juhe_duration_minutes(flight.get("duration"))
    raw_segments = _dict_items(flight.get("segments")) or [flight]
    segments = [
        segment
        for raw_segment in raw_segments
        if (segment := _normalize_juhe_flight_segment(raw_segment)) is not None
    ]
    if not service_number or price is None or duration is None or len(segments) != len(raw_segments):
        return None
    return {
        "service_number": service_number,
        "price": price,
        "fare_detail": f"{direction} 成人单人参考价 ¥{_format_number(price)}",
        "itinerary": {
            "departure_at": segments[0]["departure_at"],
            "arrival_at": segments[-1]["arrival_at"],
            "duration_minutes": duration,
            "transfer_count": len(segments) - 1,
            "segments": segments,
        },
    }


def _normalize_juhe_flight_segment(segment: dict[str, Any]) -> dict[str, Any] | None:
    service_number = _supplier_text(segment.get("flightNo"))
    carrier = _supplier_text(segment.get("airlineName")) or _supplier_text(segment.get("airline"))
    origin = _supplier_text(segment.get("departure"))
    destination = _supplier_text(segment.get("arrival"))
    departure = _juhe_datetime(segment.get("departureDate"), segment.get("departureTime"))
    arrival = _juhe_datetime(segment.get("arrivalDate"), segment.get("arrivalTime"))
    if not all((service_number, carrier, origin, destination, departure, arrival)):
        return None
    return {
        "service_number": service_number,
        "carrier": carrier,
        "departure_at": departure.isoformat(),
        "arrival_at": arrival.isoformat(),
        "from_airport": origin,
        "to_airport": destination,
    }


def _juhe_datetime(day: Any, clock: Any) -> datetime | None:
    if not isinstance(day, str) or not isinstance(clock, str):
        return None
    try:
        return datetime.fromisoformat(f"{day.strip()}T{clock.strip()}")
    except ValueError:
        return None


def _juhe_duration_minutes(value: Any) -> int | None:
    if not isinstance(value, str):
        return None
    match = re.fullmatch(r"(?:(\d+)h)?(?:(\d+)m)?", value.strip())
    if not match or not any(match.groups()):
        return None
    minutes = int(match.group(1) or 0) * 60 + int(match.group(2) or 0)
    return minutes or None


def _variflight_flight_offer_search(arguments: dict[str, Any]) -> dict[str, Any]:
    origin = _variflight_city_code(_required_text(arguments, "origin"))
    destination = _variflight_city_code(_required_text(arguments, "destination"))
    departure_date = _required_iso_date(arguments, "departure_date")
    return_date = _required_iso_date(arguments, "return_date")
    if return_date < departure_date:
        raise HTTPException(status_code=422, detail="return_date cannot be before departure_date.")
    adults = _passenger_count(arguments, "adults", 1, 1, 9)
    children = _passenger_count(arguments, "children", 0, 0, 8)
    infants = _passenger_count(arguments, "infants", 0, 0, 9)
    if infants > adults:
        raise HTTPException(status_code=422, detail="infants cannot exceed adults.")
    if not settings.variflight_api_key:
        raise HTTPException(status_code=500, detail="VARIFLIGHT_API_KEY is not configured.")
    if children or infants:
        return {"provider": "variflight", "data_quality": "provider_live", "offers": []}

    outbound = _variflight_prices(origin, destination, departure_date, "去程")
    returning = _variflight_prices(destination, origin, return_date, "返程")
    offers = []
    for outward, inward in zip(outbound[:5], returning[:5]):
        total = (outward["price"] + inward["price"]) * adults
        offers.append(
            {
                "id": f"{outward['service_number']}-{inward['service_number']}",
                "total_price": _format_number(total),
                "currency": "CNY",
                "itineraries": [outward["itinerary"], inward["itinerary"]],
                "fare_details": [outward["fare_detail"], inward["fare_detail"]],
            }
        )
    return {"provider": "variflight", "data_quality": "provider_live", "offers": offers}


def _variflight_city_code(name: str) -> str:
    normalized = name.strip().upper()
    if re.fullmatch(r"[A-Z]{3}", normalized):
        return normalized
    code = _VARIFLIGHT_CITY_CODES.get(name.strip().removesuffix("市"))
    if not code:
        raise HTTPException(status_code=422, detail="City is not supported by VariFlight.")
    return code


def _variflight_prices(origin: str, destination: str, travel_date: str, direction: str) -> list[dict[str, Any]]:
    response = httpx.post(
        settings.variflight_api_url,
        headers={"X-VARIFLIGHT-KEY": settings.variflight_api_key},
        json={
            "endpoint": "getFlightPriceByCities",
            "params": {
                "dep_city": origin,
                "arr_city": destination,
                "dep_date": travel_date,
                "price_mode": "lowest",
            },
        },
        timeout=settings.mcp_timeout_seconds,
    )
    response.raise_for_status()
    payload = _supplier_json(response)
    if payload.get("code") not in (200, "200"):
        raise HTTPException(status_code=502, detail="VariFlight request failed.")
    flights = _variflight_data_items(payload.get("data"))
    normalized = [
        offer
        for flight in flights
        if (offer := _normalize_variflight_flight(flight, travel_date, direction)) is not None
    ]
    return sorted(normalized, key=lambda offer: offer["price"])


def _variflight_data_items(value: Any) -> list[dict[str, Any]]:
    if isinstance(value, list):
        return _dict_items(value)
    if not isinstance(value, dict):
        return []
    for key in ("flights", "flightList", "list", "rows", "data"):
        if isinstance(value.get(key), list):
            return _dict_items(value[key])
    return [value] if _first_supplier_text(value, ("FlightNo", "flightNo", "fnum")) else []


def _normalize_variflight_flight(
    flight: dict[str, Any], travel_date: str, direction: str
) -> dict[str, Any] | None:
    service_number = _first_supplier_text(flight, ("FlightNo", "flightNo", "fnum"))
    carrier = _first_supplier_text(flight, ("FlightCompany", "flightCompany", "airline"))
    origin = _first_supplier_text(flight, ("FlightDepcode", "depCode", "dep"))
    destination = _first_supplier_text(flight, ("FlightArrcode", "arrCode", "arr"))
    departure = _variflight_datetime(
        _first_supplier_text(flight, ("FlightDeptimePlanDate", "depTime", "departureTime")), travel_date
    )
    arrival = _variflight_datetime(
        _first_supplier_text(flight, ("FlightArrtimePlanDate", "arrTime", "arrivalTime")), travel_date
    )
    if not all((service_number, origin, destination, departure, arrival)):
        return None
    if arrival <= departure:
        arrival += timedelta(days=1)
    cabins = []
    for key in ("cabins", "Cabins", "cabin", "prices", "priceList"):
        if isinstance(flight.get(key), list):
            cabins = _dict_items(flight[key])
            break
    if not cabins and _positive_number(flight.get("price")) is not None:
        cabins = [flight]
    priced = [
        (price, cabin)
        for cabin in cabins
        if (price := _positive_number(cabin.get("price"))) is not None
        and _seat_is_available(cabin.get("seatnum"))
    ]
    if not priced:
        return None
    price, cabin = min(priced, key=lambda item: item[0])
    cabin_class = _first_supplier_text(cabin, ("cabinclass", "cabinClass", "name")) or "舱位"
    cabin_code = _first_supplier_text(cabin, ("cabincode", "cabinCode", "code"))
    seat_count = _scalar_text(cabin.get("seatnum")) or "待确认"
    segment = {
        "service_number": service_number,
        "carrier": carrier or service_number[:2],
        "departure_at": departure.isoformat(),
        "arrival_at": arrival.isoformat(),
        "from_airport": origin,
        "to_airport": destination,
    }
    if terminal := _first_supplier_text(flight, ("FlightDepTerminal", "depTerminal", "departureTerminal")):
        segment["from_terminal"] = terminal
    if terminal := _first_supplier_text(flight, ("FlightArrTerminal", "arrTerminal", "arrivalTerminal")):
        segment["to_terminal"] = terminal
    cabin_label = f"{cabin_class}({cabin_code})" if cabin_code else cabin_class
    return {
        "service_number": service_number,
        "price": price,
        "fare_detail": f"{direction} {cabin_label} ¥{_format_number(price)} 余票{seat_count}",
        "itinerary": {
            "departure_at": departure.isoformat(),
            "arrival_at": arrival.isoformat(),
            "duration_minutes": int((arrival - departure).total_seconds() // 60),
            "transfer_count": 0,
            "segments": [segment],
        },
    }


def _variflight_datetime(value: str, travel_date: str) -> datetime | None:
    if not value:
        return None
    normalized = value.replace(" ", "T")
    if re.fullmatch(r"\d{2}:\d{2}(?::\d{2})?", normalized):
        normalized = f"{travel_date}T{normalized}"
    try:
        return datetime.fromisoformat(normalized)
    except ValueError:
        return None


def _first_supplier_text(value: dict[str, Any], keys: tuple[str, ...]) -> str:
    return next((text for key in keys if (text := _supplier_text(value.get(key)))), "")


def _positive_number(value: Any) -> float | None:
    if type(value) in (int, float):
        number = float(value)
    elif isinstance(value, str):
        try:
            number = float(value.strip().replace(",", ""))
        except ValueError:
            return None
    else:
        return None
    return number if math.isfinite(number) and number > 0 else None


def _seat_is_available(value: Any) -> bool:
    return not (type(value) in (int, float) and value <= 0) and not (
        isinstance(value, str) and value.strip() in {"0", "无", "售罄"}
    )


def _format_number(value: float) -> str:
    return str(int(value)) if value.is_integer() else f"{value:.2f}".rstrip("0").rstrip(".")


def _amadeus_flight_offer_search(arguments: dict[str, Any]) -> dict[str, Any]:
    origin_name = _required_text(arguments, "origin")
    destination_name = _required_text(arguments, "destination")
    departure_date = _required_iso_date(arguments, "departure_date")
    return_date = _required_iso_date(arguments, "return_date")
    if return_date < departure_date:
        raise HTTPException(status_code=422, detail="return_date cannot be before departure_date.")
    adults = _passenger_count(arguments, "adults", 1, 1, 9)
    children = _passenger_count(arguments, "children", 0, 0, 8)
    infants = _passenger_count(arguments, "infants", 0, 0, 9)
    if infants > adults:
        raise HTTPException(status_code=422, detail="infants cannot exceed adults.")
    if not settings.amadeus_api_key or not settings.amadeus_api_secret:
        raise HTTPException(status_code=500, detail="Amadeus credentials are not configured.")
    origin = _amadeus_location_code(origin_name)
    destination = _amadeus_location_code(destination_name)
    data = _amadeus_get(
        "/v2/shopping/flight-offers",
        {
            "originLocationCode": origin,
            "destinationLocationCode": destination,
            "departureDate": departure_date,
            "returnDate": return_date,
            "adults": adults,
            "children": children,
            "infants": infants,
            "currencyCode": "CNY",
            "max": 20,
        },
    )
    normalized_offers = [
        normalized
        for offer in _dict_items(data.get("data"))
        if (normalized := _normalize_amadeus_offer(offer)) is not None
    ]
    return {
        "provider": "amadeus",
        "data_quality": "live" if settings.amadeus_api_base_url.rstrip("/") == "https://api.amadeus.com" else "estimate",
        "offers": normalized_offers,
    }


def _amadeus_location_code(name: str) -> str:
    data = _amadeus_get(
        "/v1/reference-data/locations",
        {"subType": "CITY,AIRPORT", "keyword": name, "page[limit]": 5},
    )
    for location in _dict_items(data.get("data")):
        if isinstance(location.get("iataCode"), str) and location["iataCode"]:
            return location["iataCode"]
    raise HTTPException(status_code=502, detail=f"Amadeus location not found: {name}")


def _amadeus_get(path: str, params: dict[str, Any]) -> dict[str, Any]:
    for attempt in range(2):
        token = _get_amadeus_access_token()
        response = httpx.get(
            f"{settings.amadeus_api_base_url.rstrip('/')}{path}",
            params=params,
            headers={"Authorization": f"Bearer {token}"},
            timeout=settings.mcp_timeout_seconds,
        )
        if response.status_code != 401 or attempt:
            response.raise_for_status()
            return _supplier_json(response)
        _clear_amadeus_access_token(token)
    raise AssertionError("unreachable")


def _get_amadeus_access_token() -> str:
    global _amadeus_access_token, _amadeus_access_token_expires_at
    with _amadeus_token_lock:
        if _amadeus_access_token and time.monotonic() < _amadeus_access_token_expires_at:
            return _amadeus_access_token
        response = httpx.post(
            f"{settings.amadeus_api_base_url.rstrip('/')}/v1/security/oauth2/token",
            data={
                "grant_type": "client_credentials",
                "client_id": settings.amadeus_api_key,
                "client_secret": settings.amadeus_api_secret,
            },
            timeout=settings.mcp_timeout_seconds,
        )
        response.raise_for_status()
        data = _supplier_json(response)
        token = data.get("access_token")
        if not isinstance(token, str) or not token:
            raise HTTPException(status_code=502, detail="Invalid supplier response.")
        raw_expires_in = data.get("expires_in")
        expires_in = (
            float(raw_expires_in)
            if type(raw_expires_in) in (int, float) and math.isfinite(raw_expires_in) and raw_expires_in > 0
            else 0.0
        )
        _amadeus_access_token = token
        _amadeus_access_token_expires_at = time.monotonic() + max(0, expires_in - 30)
        return _amadeus_access_token


def _clear_amadeus_access_token(token: str) -> None:
    global _amadeus_access_token, _amadeus_access_token_expires_at
    with _amadeus_token_lock:
        if _amadeus_access_token == token:
            _amadeus_access_token = ""
            _amadeus_access_token_expires_at = 0.0


def _normalize_amadeus_offer(offer: dict[str, Any]) -> dict[str, Any] | None:
    offer_id = _scalar_text(offer.get("id")).strip()
    if not offer_id:
        return None
    price = offer.get("price") if isinstance(offer.get("price"), dict) else {}
    raw_itineraries = offer.get("itineraries")
    if not isinstance(raw_itineraries, list) or len(raw_itineraries) != 2:
        return None
    itineraries = []
    for item in raw_itineraries:
        if not isinstance(item, dict) or (normalized := _normalize_amadeus_itinerary(item)) is None:
            return None
        itineraries.append(normalized)
    return {
        "id": offer_id,
        "total_price": _scalar_text(price.get("grandTotal")),
        "currency": _supplier_text(price.get("currency")) or "CNY",
        "itineraries": itineraries,
    }


def _normalize_amadeus_itinerary(itinerary: dict[str, Any]) -> dict[str, Any] | None:
    raw_segments = itinerary.get("segments")
    if not isinstance(raw_segments, list) or not raw_segments:
        return None
    normalized_segments = []
    for segment in raw_segments:
        if not isinstance(segment, dict) or (normalized := _normalize_amadeus_segment(segment)) is None:
            return None
        normalized_segments.append(normalized)
    return {
        "departure_at": normalized_segments[0]["departure_at"] if normalized_segments else None,
        "arrival_at": normalized_segments[-1]["arrival_at"] if normalized_segments else None,
        "duration_minutes": _iso_duration_minutes(itinerary.get("duration", "")),
        "transfer_count": max(0, len(normalized_segments) - 1),
        "segments": normalized_segments,
    }


def _normalize_amadeus_segment(segment: dict[str, Any]) -> dict[str, Any] | None:
    departure = segment.get("departure") if isinstance(segment.get("departure"), dict) else {}
    arrival = segment.get("arrival") if isinstance(segment.get("arrival"), dict) else {}
    carrier = _supplier_text(segment.get("carrierCode"))
    number = _supplier_text(segment.get("number"))
    departure_at = _supplier_text(departure.get("at"))
    arrival_at = _supplier_text(arrival.get("at"))
    from_airport = _supplier_text(departure.get("iataCode"))
    to_airport = _supplier_text(arrival.get("iataCode"))
    if not all((carrier, number, departure_at, arrival_at, from_airport, to_airport)):
        return None
    normalized = {
        "service_number": f"{carrier}{number}",
        "carrier": carrier,
        "departure_at": departure_at,
        "arrival_at": arrival_at,
        "from_airport": from_airport,
        "to_airport": to_airport,
    }
    if terminal := _supplier_text(departure.get("terminal")):
        normalized["from_terminal"] = terminal
    if terminal := _supplier_text(arrival.get("terminal")):
        normalized["to_terminal"] = terminal
    return normalized


def _iso_duration_minutes(value: Any) -> int | None:
    if not isinstance(value, str):
        return None
    match = re.fullmatch(r"PT(?:(\d+)H)?(?:(\d+)M)?", value)
    if not match or not any(match.groups()):
        return None
    return int(match.group(1) or 0) * 60 + int(match.group(2) or 0)


def _required_text(arguments: dict[str, Any], name: str) -> str:
    value = arguments.get(name)
    if not isinstance(value, str) or not value.strip():
        raise HTTPException(status_code=422, detail=f"{name} is required.")
    return value.strip()


def _required_iso_date(arguments: dict[str, Any], name: str) -> str:
    value = _required_text(arguments, name)
    try:
        parsed = date.fromisoformat(value)
    except ValueError as exc:
        raise HTTPException(status_code=422, detail=f"{name} must be an ISO date.") from exc
    if parsed.isoformat() != value:
        raise HTTPException(status_code=422, detail=f"{name} must be an ISO date.")
    return value


def _passenger_count(arguments: dict[str, Any], name: str, default: int, minimum: int, maximum: int) -> int:
    value = arguments.get(name, default)
    if type(value) is not int or not minimum <= value <= maximum:
        raise HTTPException(status_code=422, detail=f"{name} is invalid.")
    return value


def _supplier_text(value: Any) -> str:
    return value.strip() if isinstance(value, str) else ""


def _scalar_text(value: Any) -> str:
    if isinstance(value, str) or type(value) is int:
        return str(value)
    return str(value) if isinstance(value, float) and math.isfinite(value) else ""


def _dict_items(value: Any) -> list[dict[str, Any]]:
    return [item for item in value if isinstance(item, dict)] if isinstance(value, list) else []


def _supplier_json(response: Any) -> dict[str, Any]:
    try:
        data = response.json()
    except ValueError as exc:
        raise HTTPException(status_code=502, detail="Invalid supplier response.") from exc
    if not isinstance(data, dict):
        raise HTTPException(status_code=502, detail="Invalid supplier response.")
    return data
