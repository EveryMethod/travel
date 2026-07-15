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
    draft: dict[str, Any]
    plan: TripPlanResponse


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
    yield {"type": "status", "message": "正在让大模型生成路线草案..."}
    state.update(_draft_plan(state))
    yield {"type": "status", "message": "正在校验并整理行程格式..."}
    state.update(_validate_plan(state))
    yield {"type": "plan", "data": state["plan"].model_dump()}
    yield {"type": "done"}


def _build_graph():
    graph = StateGraph(TripPlannerState)
    graph.add_node("normalize_request", _normalize_request)
    graph.add_node("collect_map_context", _collect_map_context)
    graph.add_node("collect_price_context", _collect_price_context)
    graph.add_node("draft_plan", _draft_plan)
    graph.add_node("validate_plan", _validate_plan)
    graph.add_edge(START, "normalize_request")
    graph.add_edge("normalize_request", "collect_map_context")
    graph.add_edge("collect_map_context", "collect_price_context")
    graph.add_edge("collect_price_context", "draft_plan")
    graph.add_edge("draft_plan", "validate_plan")
    graph.add_edge("validate_plan", END)
    return graph.compile()


def _normalize_request(state: TripPlannerState) -> TripPlannerState:
    request = state["request"]
    request.destination = request.destination.strip()
    request.origin = request.origin.strip()
    request.budget = request.budget.strip()
    request.start_date = request.start_date.strip()
    request.end_date = request.end_date.strip()
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


def _draft_plan(state: TripPlannerState) -> TripPlannerState:
    request = state["request"]
    context = state["context"]
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
                    "每个日期给 2 到 4 个 items，保持简洁。"
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
                            "budget": request.budget,
                        },
                    },
                    ensure_ascii=False,
                ),
            },
        ]
    )
    return {"request": request, "context": context, "draft": draft}


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
    return {"request": request, "plan": plan}


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


def _slugify(value: str) -> str:
    slug = re.sub(r"[^\w]+", "-", value.strip().lower(), flags=re.UNICODE).strip("-")
    return slug or "trip"


_trip_planner_graph = _build_graph()
