"""LangGraph flow for revising an existing trip without overwriting it."""

import json
from collections.abc import Iterator
from typing import Any, TypedDict

from langgraph.graph import END, START, StateGraph
from pydantic import BaseModel, ValidationError

from src.app.graph.transport_planner import plan_transport_with_graph
from src.app.graph.trip_planner import (
    _check_constraints,
    _normalize_plan_shape,
    _review_plan,
    plan_trip_with_graph,
)
from src.app.models.trip import TripPlanRequest, TripPlanResponse
from src.app.services.llm_service import generate_json
from src.app.services.mcp_client import call_tool


class RevisionAnalysis(BaseModel):
    affected_days: list[int]
    affects_daily_plan: bool
    affects_intercity_transport: bool
    place_queries: list[str]
    price_queries: list[str]
    needs_map: bool
    needs_price: bool
    forbidden_change: bool
    reason: str


class TripRevisionState(TypedDict, total=False):
    request: TripPlanRequest
    original_plan: TripPlanResponse
    instruction: str
    analysis: RevisionAnalysis
    context: dict[str, Any]
    draft: dict[str, Any]
    plan: TripPlanResponse
    repair_used: bool


def revise_trip_with_graph(
    original_request: TripPlanRequest,
    original_plan: TripPlanResponse,
    instruction: str,
) -> TripPlanResponse:
    final_state = _trip_revision_graph.invoke(
        {
            "request": original_request.model_copy(deep=True),
            "original_plan": original_plan.model_copy(deep=True),
            "instruction": instruction.strip(),
            "repair_used": False,
        }
    )
    return final_state["plan"]


def stream_trip_revision(
    original_request: TripPlanRequest,
    original_plan: TripPlanResponse,
    instruction: str,
) -> Iterator[dict[str, Any]]:
    state: TripRevisionState = {
        "request": original_request.model_copy(deep=True),
        "original_plan": original_plan.model_copy(deep=True),
        "instruction": instruction.strip(),
        "repair_used": False,
    }
    yield {"type": "status", "message": "正在理解本次调整要求..."}
    state.update(_analyze_instruction(state))
    if state["analysis"].affects_intercity_transport:
        yield {"type": "status", "message": "正在重新查询往返交通方案..."}
        state.update(_replan_transport_revision(state))
        yield {"type": "status", "message": "正在根据新交通方案调整首末日..."}
        yield {"type": "plan", "data": state["plan"].model_dump()}
        yield {"type": "done"}
        return
    yield {"type": "status", "message": "正在补充本次调整需要的地点和价格信息..."}
    state.update(_collect_revision_context(state))
    yield {
        "type": "context",
        "data": {
            "affected_days": state["analysis"].affected_days,
            "map_results": len(state["context"]["map"]),
            "price_results": len(state["context"]["prices"]),
        },
    }
    yield {"type": "status", "message": "正在生成调整后的完整行程..."}
    state.update(_revise_plan(state))
    yield {"type": "status", "message": "正在校验日期、天数和未修改内容..."}
    state.update(_validate_revision(state))
    yield {"type": "plan", "data": state["plan"].model_dump()}
    yield {"type": "done"}


def _build_graph():
    graph = StateGraph(TripRevisionState)
    graph.add_node("analyze_instruction", _analyze_instruction)
    graph.add_node("replan_transport", _replan_transport_revision)
    graph.add_node("collect_revision_context", _collect_revision_context)
    graph.add_node("revise_plan", _revise_plan)
    graph.add_node("validate_revision", _validate_revision)
    graph.add_edge(START, "analyze_instruction")
    graph.add_conditional_edges(
        "analyze_instruction",
        lambda state: "replan_transport"
        if state["analysis"].affects_intercity_transport
        else "collect_revision_context",
    )
    graph.add_edge("replan_transport", END)
    graph.add_edge("collect_revision_context", "revise_plan")
    graph.add_edge("revise_plan", "validate_revision")
    graph.add_edge("validate_revision", END)
    return graph.compile()


def _analyze_instruction(state: TripRevisionState) -> TripRevisionState:
    messages = [
        {
            "role": "system",
            "content": (
                "你是行程修改指令分析器，只输出 JSON object。字段为 affected_days、affects_daily_plan、"
                "affects_intercity_transport、place_queries、price_queries、needs_map、needs_price、"
                "forbidden_change、reason。"
                "修改任意每日安排时 affects_daily_plan=true；只修改摘要、免责声明等全局文案时为 false。"
                "修改城际航班、铁路、自驾方式、去程或返程时间、车站或机场，或要求避开某种城际交通方式时，"
                "affects_intercity_transport=true；目的地内地铁、出租车或步行调整时必须为 false。"
                "修改景点、餐厅或目的地内路线时 needs_map=true；修改门票、餐饮或预算时 needs_price=true。"
                "如果用户要求修改目的地、出行日期或旅行天数，forbidden_change=true。"
                "涉及全部日期但未指定某一天时，affected_days 为空且 affects_daily_plan=true。"
            ),
        },
        {
            "role": "user",
            "content": json.dumps(
                {
                    "instruction": state["instruction"],
                    "destination": state["request"].destination,
                    "days": state["request"].days,
                    "date_range": [state["request"].start_date, state["request"].end_date],
                },
                ensure_ascii=False,
            ),
        },
    ]
    repair_used = state.get("repair_used", False)
    try:
        analysis = RevisionAnalysis.model_validate(generate_json(messages))
    except (json.JSONDecodeError, ValidationError):
        if repair_used:
            raise
        messages[0]["content"] += "前次输出无效，请补齐所有字段且只输出合法 JSON object。"
        analysis = RevisionAnalysis.model_validate(generate_json(messages))
        repair_used = True
    if analysis.forbidden_change:
        raise ValueError(analysis.reason or "第一版暂不支持修改目的地、出行日期或旅行天数。")
    if any(day < 1 or day > state["request"].days for day in analysis.affected_days):
        raise ValueError("修改指令包含无效的行程日期编号。")
    analysis.affected_days = sorted(set(analysis.affected_days))
    if analysis.affected_days:
        analysis.affects_daily_plan = True
    return {**state, "analysis": analysis, "repair_used": repair_used}


def _replan_transport_revision(state: TripRevisionState) -> TripRevisionState:
    request = state["request"].model_copy(deep=True)
    request.notes = f"{request.notes}\n{state['instruction']}".strip()[-500:]
    unavailable = "实时交通服务暂不可用，已保留原交通方案。"
    try:
        transport = plan_transport_with_graph(request)
    except Exception as exc:
        raise ValueError(unavailable) from exc
    if transport is None or not transport.options:
        raise ValueError(unavailable)

    plan = plan_trip_with_graph(request, transport_plan=transport).model_copy(deep=True)
    original = state["original_plan"]
    original_days = [(day.day, day.date) for day in original.days]
    replanned_days = [(day.day, day.date) for day in plan.days]
    if replanned_days != original_days or len(set(replanned_days)) != len(replanned_days):
        raise ValueError("重新规划后的行程日期顺序与原行程不一致。")

    if len(plan.days) > 2:
        plan.days[1:-1] = [day.model_copy(deep=True) for day in original.days[1:-1]]
    plan.destination = original.destination
    plan.intercity_transport = transport.model_copy(deep=True)
    return {**state, "plan": plan}


def _collect_revision_context(state: TripRevisionState) -> TripRevisionState:
    analysis = state["analysis"]
    context: dict[str, list[dict[str, Any]]] = {"map": [], "routes": [], "prices": []}
    if analysis.needs_map:
        candidate_locations: list[tuple[str, str]] = []
        missing_place_queries: list[str] = []
        for query in analysis.place_queries[:4]:
            result = _safe_tool(
                "amap_search_poi",
                {"city": state["request"].destination, "keywords": query, "offset": 6},
            )
            if result.get("pois"):
                context["map"].append({"query": query, "result": result})
                location = _first_location(result)
                if location:
                    candidate_locations.append((query, location))
            else:
                missing_place_queries.append(query)

        if missing_place_queries:
            raise ValueError("地点服务没有找到本次修改需要的新地点，请更换描述后重试。")

        affected_days = set(analysis.affected_days)
        if analysis.affects_daily_plan and not affected_days:
            affected_days = {day.day for day in state["original_plan"].days}
        for day in state["original_plan"].days:
            if day.day not in affected_days:
                continue
            day_locations: list[tuple[str, str]] = []
            for place in list(dict.fromkeys(item.place.strip() for item in day.items if item.place.strip()))[:6]:
                result = _safe_tool(
                    "amap_geocode",
                    {"address": place, "city": state["request"].destination},
                )
                location = _first_location(result)
                if location:
                    day_locations.append((place, location))
                    context["map"].append({"query": place, "result": result})

            for origin, destination in zip(day_locations, day_locations[1:]):
                _append_route_context(context, day.day, origin, destination)
            if day_locations:
                anchor = day_locations[-1]
                for candidate in candidate_locations:
                    _append_route_context(context, day.day, anchor, candidate)
        if not context["map"]:
            raise ValueError("地点服务暂时没有返回可用结果，请稍后重试。")
    if analysis.needs_price:
        for query in analysis.price_queries[:4]:
            result = _safe_tool("ticket_price_search", {"query": query, "max_results": 3})
            if result.get("results"):
                context["prices"].append({"query": query, "result": result})
        if not context["prices"]:
            raise ValueError("价格服务暂时没有返回可用结果，请稍后重试。")
    return {**state, "context": context}


def _first_location(result: dict[str, Any]) -> str:
    for key in ("geocodes", "pois"):
        items = result.get(key)
        if isinstance(items, list) and items and isinstance(items[0], dict):
            location = items[0].get("location")
            if isinstance(location, str):
                return location
    return ""


def _append_route_context(
    context: dict[str, list[dict[str, Any]]],
    day: int,
    origin: tuple[str, str],
    destination: tuple[str, str],
) -> None:
    if len(context["routes"]) >= 8 or origin[1] == destination[1]:
        return
    route = _safe_tool("amap_route_distance", {"origin": origin[1], "destination": destination[1]})
    if route.get("route"):
        context["routes"].append(
            {
                "day": day,
                "origin": origin[0],
                "destination": destination[0],
                "result": route,
            }
        )


def _safe_tool(name: str, arguments: dict[str, Any]) -> dict[str, Any]:
    try:
        result = call_tool(name, arguments)
    except Exception:
        return {}
    return result if isinstance(result, dict) else {}


def _revise_plan(state: TripRevisionState) -> TripRevisionState:
    messages = [
        {
            "role": "system",
            "content": (
                "你是中文行程修改 Agent，只输出完整 TripPlanResponse JSON object。"
                "只能按 instruction 修改必要内容，未涉及日期保持原样。"
                "禁止修改 destination、日期、天数和 day 编号。"
                "地图或价格查询无结果时保留原信息，不得编造精确价格、地点或路线。"
                "价格只能写约数、区间或需查询官方渠道，并保留核实提示。"
            ),
        },
        {
            "role": "user",
            "content": json.dumps(
                {
                    "request": state["request"].model_dump(),
                    "original_plan": state["original_plan"].model_dump(mode="json"),
                    "instruction": state["instruction"],
                    "affected_days": state["analysis"].affected_days,
                    "revision_context": state["context"],
                },
                ensure_ascii=False,
            ),
        },
    ]
    try:
        draft = generate_json(messages)
    except json.JSONDecodeError:
        if state.get("repair_used", False):
            raise
        messages[0]["content"] += "前次输出不是合法 JSON，请重新生成且只输出合法 JSON object。"
        draft = generate_json(messages)
        return {**state, "draft": draft, "repair_used": True}
    return {**state, "draft": draft}


def _validate_revision(state: TripRevisionState) -> TripRevisionState:
    repair_used = state.get("repair_used", False)
    try:
        plan = _validated_plan(state["draft"], state["original_plan"])
    except (ValidationError, ValueError) as exc:
        if repair_used:
            raise
        repaired = generate_json(
            [
                {
                    "role": "system",
                    "content": "修复 JSON，使其符合 TripPlanResponse，并严格保持原目的地、日期和天数。只输出 JSON object。",
                },
                {
                    "role": "user",
                    "content": json.dumps(
                        {
                            "error": str(exc),
                            "bad_json": state["draft"],
                            "original_destination": state["original_plan"].destination,
                            "original_days": [day.model_dump() for day in state["original_plan"].days],
                        },
                        ensure_ascii=False,
                    ),
                },
            ]
        )
        plan = _validated_plan(repaired, state["original_plan"])
        repair_used = True

    analysis = state["analysis"]
    affected_days = set(analysis.affected_days)
    if analysis.affects_daily_plan and not affected_days:
        affected_days = {day.day for day in state["original_plan"].days}
    plan.destination = state["original_plan"].destination
    revised_days = {day.day: day for day in plan.days}
    ordered_days = []
    for original_day in state["original_plan"].days:
        if original_day.day not in affected_days:
            ordered_days.append(original_day.model_copy(deep=True))
        else:
            revised_day = revised_days[original_day.day]
            revised_day.day = original_day.day
            revised_day.date = original_day.date
            ordered_days.append(revised_day)
    plan.days = ordered_days
    plan.intercity_transport = (
        state["original_plan"].intercity_transport.model_copy(deep=True)
        if state["original_plan"].intercity_transport
        else None
    )

    constraints = _check_constraints({"request": state["request"], "context": {}})["constraints"]
    constraints["review_routes"] = analysis.needs_map
    pre_review_days = {day.day: day.model_copy(deep=True) for day in plan.days}
    early_window_tip = "已移除早于抵达及接驳完成时间的首日活动。"
    late_window_tip = "已移除晚于返程出发缓冲时间的末日活动。"
    window_tip_counts = {
        early_window_tip: max(
            plan.tips.count(early_window_tip),
            state["original_plan"].tips.count(early_window_tip),
        ),
        late_window_tip: max(
            plan.tips.count(late_window_tip),
            state["original_plan"].tips.count(late_window_tip),
        ),
    }
    reviewed = _review_plan({"request": state["request"], "context": {}, "constraints": constraints, "plan": plan})
    plan = reviewed["plan"]
    plan.destination = state["original_plan"].destination
    reviewed_day_ids = [day.day for day in plan.days]
    valid_reviewed_days = (
        len(reviewed_day_ids) == len(set(reviewed_day_ids))
        and set(reviewed_day_ids) == set(pre_review_days)
    )
    reviewed_days = {day.day: day for day in plan.days} if valid_reviewed_days else pre_review_days
    ordered_days = []
    restored_days = set()
    for original_day in state["original_plan"].days:
        if original_day.day not in affected_days:
            ordered_days.append(original_day.model_copy(deep=True))
            restored_days.add(original_day.day)
        else:
            revised_day = reviewed_days[original_day.day]
            revised_day.day = original_day.day
            revised_day.date = original_day.date
            ordered_days.append(revised_day)
            if not valid_reviewed_days:
                restored_days.add(original_day.day)
    plan.days = ordered_days
    for day, tip in (
        (state["original_plan"].days[0].day, early_window_tip),
        (state["original_plan"].days[-1].day, late_window_tip),
    ):
        if day in restored_days:
            while plan.tips.count(tip) > window_tip_counts[tip]:
                plan.tips.remove(tip)
    plan.intercity_transport = (
        state["original_plan"].intercity_transport.model_copy(deep=True)
        if state["original_plan"].intercity_transport
        else None
    )
    return {**state, "plan": plan, "repair_used": repair_used}


def _validated_plan(value: Any, original: TripPlanResponse) -> TripPlanResponse:
    try:
        normalized = _normalize_plan_shape(value)
    except (AttributeError, TypeError) as exc:
        raise ValueError("调整后的行程 JSON 结构无效。") from exc
    plan = TripPlanResponse.model_validate(normalized)
    candidate_days = [day.day for day in plan.days]
    original_days = [day.day for day in original.days]
    if len(candidate_days) != len(set(candidate_days)) or set(candidate_days) != set(original_days):
        raise ValueError("调整后的行程日期编号与原行程不一致。")
    return plan


_trip_revision_graph = _build_graph()
