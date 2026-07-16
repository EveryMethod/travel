"""Self-checks for the MCP-backed trip planner graph."""

from src.app.core import tracing
from src.app.graph import trip_planner
from src.app.models.trip import TripDay, TripPlanItem, TripPlanRequest, TripPlanResponse


def demo() -> None:
    def fake_call_tool(name, arguments):
        return tracing.trace_call("mcp.client", name, arguments, None, lambda: _fake_tool_result(name, arguments))

    def fake_generate_json(messages):
        return tracing.trace_call("agent.llm", "demo-llm", {"message_count": len(messages)}, None, lambda: {
            "trip_id": "test-hangzhou-2",
            "destination": "杭州",
            "summary": "结合真实地点生成的 2 天行程。",
            "days": [
                {
                    "day": 1,
                    "date": "2026-10-01",
                    "title": "西湖初见",
                    "weather": "多云，适合步行",
                    "items": [
                        {
                            "time": "09:30",
                            "place": "西湖",
                            "activity": "环湖步行，观察湖畔景观。",
                            "estimated_cost": "免费",
                            "booking_hint": "无需预约",
                            "source_hint": "Tavily 价格参考",
                        }
                    ],
                    "daily_budget": "约 ¥200",
                    "transport": "市内地铁和步行",
                    "notes": ["使用 MCP 返回的西湖。"],
                },
                {
                    "day": 2,
                    "date": "2026-10-02",
                    "title": "城市文化",
                    "weather": "以实时天气为准",
                    "items": [
                        {
                            "time": "10:00",
                            "place": "博物馆",
                            "activity": "参观城市文化展。",
                            "estimated_cost": "需查询官方渠道",
                            "booking_hint": "提前确认开放时间",
                            "source_hint": "价格未命中",
                        }
                    ],
                    "daily_budget": "约 ¥300",
                    "transport": "公共交通",
                    "notes": ["控制跨区移动。"],
                },
            ],
            "tips": ["出发前核对天气。"],
            "disclaimer": "请以实际开放信息为准。",
        })

    records = []

    def fake_write_record(record):
        records.append(record)

    old_call_tool = trip_planner.call_tool
    old_generate_json = trip_planner.generate_json
    old_write_record = tracing._write_record
    trip_planner.call_tool = fake_call_tool
    trip_planner.generate_json = fake_generate_json
    tracing._write_record = fake_write_record
    try:
        with tracing.trace_context("trace-trip-demo"):
            plan = trip_planner.plan_trip_with_graph(
                TripPlanRequest(destination="杭州", origin="上海", days=2, travel_style=["culture"])
            )
    finally:
        trip_planner.call_tool = old_call_tool
        trip_planner.generate_json = old_generate_json
        tracing._write_record = old_write_record

    assert plan.destination == "杭州"
    assert len(plan.days) == 2
    assert plan.days[0].date == "2026-10-01"
    assert "西湖" in plan.days[0].items[0].place

    structured = TripPlanRequest(
        destination="京都",
        days=3,
        budget_breakdown={"transport": "1200", "hotel": "1800", "food": "900", "tickets": "600"},
        pace="relaxed",
        companions="family",
        must_see="清水寺",
        avoid="环球影城",
    )
    assert structured.budget_breakdown.transport == "1200"
    assert structured.pace == "relaxed"
    assert structured.companions == "family"
    assert structured.must_see == "清水寺"
    assert structured.avoid == "环球影城"

    assert trip_planner._parse_budget_amount("1200") == 1200
    assert trip_planner._parse_budget_amount("约 500-800 元") == 800
    assert trip_planner._parse_budget_amount("需查询官方渠道") is None
    constraint_state = trip_planner._check_constraints({"request": structured, "context": {}})
    constraints = constraint_state["constraints"]
    assert constraints["parsed_budget"] == {"transport": 1200, "hotel": 1800, "food": 900, "tickets": 600}
    assert constraints["budget_total"] == 4500
    assert "2 到 3 个活动" in constraints["pace_rule"]
    assert "降低步行强度" in constraints["companions_rule"]
    assert constraints["must_see"] == "清水寺"
    assert constraints["avoid"] == "环球影城"

    risky_plan = TripPlanResponse(
        trip_id="demo",
        destination="京都",
        summary="demo",
        days=[
            TripDay(
                day=1,
                date="2026-10-01",
                title="demo",
                items=[
                    TripPlanItem(time="09:00", place="环球影城", activity="游玩", estimated_cost="300"),
                    TripPlanItem(time="09:00", place="咖啡店", activity="早餐", estimated_cost="80"),
                    TripPlanItem(time="11:00", place="博物馆", activity="参观", estimated_cost="80"),
                    TripPlanItem(time="14:00", place="商店街", activity="购物", estimated_cost="200"),
                ],
                notes=[],
            )
        ],
        tips=[],
        disclaimer="demo",
    )
    reviewed = trip_planner._review_plan(
        {"request": structured, "context": {}, "constraints": {"budget_total": 500, "must_see": "清水寺", "avoid": "环球影城"}, "plan": risky_plan}
    )
    tips = "\n".join(reviewed["plan"].tips)
    assert "慢游节奏" in tips
    assert "重复时间" in tips
    assert "必去地点" in tips
    assert "避开地点" in tips
    assert "明显高于预算" in tips

    route_calls = []

    def fake_route_tool(name, arguments):
        route_calls.append((name, arguments))
        if name == "amap_geocode":
            locations = {
                "北京故宫": "116.397,39.916",
                "北京环球影城": "116.680,39.850",
                "北京近处咖啡": "116.681,39.850",
                "北京博物馆": "116.404,39.915",
                "北京第五站": "116.500,39.900",
            }
            return {"geocodes": [{"location": locations[arguments["address"]]}]}
        if name == "amap_route_distance":
            if arguments == {"origin": "116.397,39.916", "destination": "116.680,39.850"}:
                return {"route": {"paths": [{"duration": "3600", "distance": "30000"}]}}
            return {"route": {"paths": [{"duration": "600", "distance": "3000"}]}}
        raise AssertionError(name)

    route_plan = TripPlanResponse(
        trip_id="route-risk",
        destination="北京",
        summary="demo",
        days=[
            TripDay(
                day=1,
                date="2026-10-01",
                title="demo",
                items=[
                    TripPlanItem(time="09:00", place="故宫", activity="参观"),
                    TripPlanItem(time="11:00", place="环球影城", activity="游玩"),
                    TripPlanItem(time="15:00", place="近处咖啡", activity="休息"),
                    TripPlanItem(time="17:00", place="博物馆", activity="参观"),
                    TripPlanItem(time="20:00", place="第五站", activity="夜游"),
                ],
                notes=[],
            )
        ],
        tips=[],
        disclaimer="demo",
    )

    old_call_tool = trip_planner.call_tool
    trip_planner.call_tool = fake_route_tool
    try:
        reviewed = trip_planner._review_plan(
            {"request": structured, "context": {}, "constraints": {}, "plan": route_plan}
        )
    finally:
        trip_planner.call_tool = old_call_tool

    tips = "\n".join(reviewed["plan"].tips)
    assert "第 1 天 故宫 → 环球影城 通勤约 60 分钟" in tips
    assert "近处咖啡 → 博物馆 通勤约 10 分钟" not in tips
    geocode_addresses = [call[1].get("address") for call in route_calls if call[0] == "amap_geocode"]
    assert len([call for call in route_calls if call[0] == "amap_route_distance"]) == 3
    assert all(str(address).startswith("北京") for address in geocode_addresses)
    assert geocode_addresses.count("北京环球影城") == 1
    assert not any(address == "北京第五站" for address in geocode_addresses)

    before_blank_routes = len([call for call in route_calls if call[0] == "amap_route_distance"])
    blank_plan = TripPlanResponse(
        trip_id="route-blank",
        destination="北京",
        summary="demo",
        days=[
            TripDay(
                day=1,
                date="2026-10-01",
                title="demo",
                items=[
                    TripPlanItem(time="09:00", place="故宫", activity="参观"),
                    TripPlanItem(time="10:00", place="", activity="休息"),
                    TripPlanItem(time="11:00", place="环球影城", activity="游玩"),
                ],
                notes=[],
            )
        ],
        tips=[],
        disclaimer="demo",
    )
    assert trip_planner._review_route_legs(blank_plan) == []
    after_blank_routes = len([call for call in route_calls if call[0] == "amap_route_distance"])
    assert after_blank_routes == before_blank_routes
    assert trip_planner._route_duration_seconds({"route": []}) is None
    assert trip_planner._route_duration_seconds({"route": {"paths": [None]}}) is None

    def failing_route_tool(name, arguments):
        raise RuntimeError(name)

    stable_plan = TripPlanResponse(
        trip_id="route-failure",
        destination="北京",
        summary="demo",
        days=[
            TripDay(
                day=1,
                date="2026-10-01",
                title="demo",
                items=[
                    TripPlanItem(time="09:00", place="故宫", activity="参观"),
                    TripPlanItem(time="11:00", place="环球影城", activity="游玩"),
                ],
                notes=[],
            )
        ],
        tips=["原有提醒"],
        disclaimer="demo",
    )

    old_call_tool = trip_planner.call_tool
    trip_planner.call_tool = failing_route_tool
    try:
        reviewed = trip_planner._review_plan(
            {"request": structured, "context": {}, "constraints": {}, "plan": stable_plan}
        )
    finally:
        trip_planner.call_tool = old_call_tool

    assert reviewed["plan"].tips == ["原有提醒"]

    kinds = {record.kind for record in records}
    assert "agent.llm" in kinds
    assert "mcp.client" in kinds
    assert {record.trace_id for record in records} == {"trace-trip-demo"}


def _fake_tool_result(name, arguments):
    if name == "ticket_price_search":
        return {"query": arguments["query"], "results": [{"title": "西湖门票免费", "url": "https://example.com", "content": "西湖景区免费开放，游船另付费。"}]}
    if name == "amap_geocode":
        return {"geocodes": [{"location": "120.0,30.0"}]}
    return {"pois": [{"name": "西湖", "type": "风景名胜", "address": "杭州", "location": "120.0,30.0"}]}


if __name__ == "__main__":
    demo()
