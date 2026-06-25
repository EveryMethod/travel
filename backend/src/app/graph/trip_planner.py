"""Minimal LangGraph travel planner skeleton."""

import re
from typing import TypedDict

from langgraph.graph import END, START, StateGraph

from src.app.models.trip import TripDay, TripPlanRequest, TripPlanResponse


class TripPlannerState(TypedDict, total=False):
    """State passed through the trip planner graph."""

    request: TripPlanRequest
    plan: TripPlanResponse


_STYLE_THEMES: dict[str, tuple[str, str]] = {
    "culture": ("寺社街区、城市故事和在地文化", "历史街区"),
    "food": ("本地市场、特色小店和轻松美食体验", "美食街区"),
    "nature": ("自然步道、城市绿地和安静观景点", "公园或观景点"),
    "family": ("节奏舒适、动线简单、适合全家同行", "亲子友好场馆"),
    "romantic": ("慢步调散步、氛围晚餐和有记忆点的夜晚", "河畔或老街"),
    "adventure": ("更主动的探索、短途延伸和有惊喜的路线", "步道或近郊目的地"),
    "relaxed": ("不赶路的安排、留白时间和街区漫游", "生活感街区"),
}


def plan_trip_with_graph(request: TripPlanRequest) -> TripPlanResponse:
    """Run the local LangGraph planner and return its generated trip plan."""

    final_state = _trip_planner_graph.invoke({"request": request})
    return final_state["plan"]


def _build_graph():
    graph = StateGraph(TripPlannerState)
    graph.add_node("draft_itinerary", _draft_itinerary)
    graph.add_edge(START, "draft_itinerary")
    graph.add_edge("draft_itinerary", END)
    return graph.compile()


def _draft_itinerary(state: TripPlannerState) -> TripPlannerState:
    request = state["request"]
    return {"request": request, "plan": _build_demo_plan(request)}


def _build_demo_plan(request: TripPlanRequest) -> TripPlanResponse:
    style_theme, anchor_place = _STYLE_THEMES[request.travel_style]
    slug = _slugify(request.destination)
    month_phrase = f"，出行时间为{request.month}" if request.month else ""
    origin_phrase = f"，从{request.origin}出发" if request.origin else ""
    notes_phrase = "。行程已为你的补充偏好预留弹性时间" if request.notes else ""

    days = [
        _build_day_plan(
            day=day,
            destination=request.destination,
            style_theme=style_theme,
            anchor_place=anchor_place,
        )
        for day in range(1, request.days + 1)
    ]

    return TripPlanResponse(
        trip_id=f"demo-{slug}-{request.days}",
        destination=request.destination,
        summary=(
            f"这是一份为{request.destination}定制的{request.days}天中文行程草案"
            f"{month_phrase}{origin_phrase}。整体节奏围绕“{style_theme}”展开，"
            f"每天安排相对紧凑但保留调整空间{notes_phrase}。"
        ),
        days=days,
        tips=[
            "优先把相邻景点安排在同一天，减少往返交通消耗。",
            "每天保留一段可调整时间，用来应对天气、休息或临时发现的好去处。",
            _budget_tip(request.budget),
        ],
        disclaimer="这是一份由本地演示规划器生成的行程草案，建议出发前再核对开放时间、交通和预约信息。",
    )


def _build_day_plan(
    *,
    day: int,
    destination: str,
    style_theme: str,
    anchor_place: str,
) -> TripDay:
    if day == 1:
        return TripDay(
            day=day,
            title="抵达与初识城市",
            theme="轻松适应",
            morning=f"抵达{destination}后先办理入住或寄存行李，留出时间熟悉周边环境。",
            afternoon=f"选择一处附近的{anchor_place}慢慢逛，建立对城市节奏的第一印象。",
            evening="晚餐安排在住处附近，避免第一天跨城奔波。",
            notes=["第一天不建议排得太满。", style_theme],
        )

    return TripDay(
        day=day,
        title=f"第 {day} 天街区路线",
        theme=style_theme,
        morning=f"从{destination}交通方便的区域开始，安排一个重点参观或体验项目。",
        afternoon=f"顺路前往附近的{anchor_place}，中途预留咖啡、休息或临时调整时间。",
        evening="晚餐尽量选择当天最后一站附近，减少夜间重复换乘。",
        notes=["每天控制在两次以内的大跨度交通移动，体验会更从容。"],
    )


def _budget_tip(budget: str) -> str:
    if budget == "low":
        return "预算偏经济时，可多选择公共交通、简餐和免费观景点，把费用留给真正想体验的项目。"
    if budget == "high":
        return "预算较充足时，建议把高价值消费集中在一顿特色餐或一次私享导览上。"
    return "预算均衡时，可用日常餐饮搭配一两项重点体验，让花费和体验更平衡。"


def _slugify(value: str) -> str:
    normalized = value.strip().lower()
    slug = re.sub(r"[^\w]+", "-", normalized, flags=re.UNICODE).strip("-")
    return slug or "trip"


_trip_planner_graph = _build_graph()
