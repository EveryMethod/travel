"""Self-checks for the MCP-backed trip planner graph."""

from src.app.core import tracing
from src.app.graph import trip_planner
from src.app.models.trip import TripPlanRequest


def demo() -> None:
    def fake_call_tool(name, arguments):
        def run():
            if name == "ticket_price_search":
                return {"query": arguments["query"], "results": [{"title": "西湖门票免费", "url": "https://example.com", "content": "西湖景区免费开放，游船另付费。"}]}
            if name == "amap_geocode":
                return {"geocodes": [{"location": "120.0,30.0"}]}
            return {"pois": [{"name": "西湖", "type": "风景名胜", "address": "杭州", "location": "120.0,30.0"}]}

        return tracing.trace_call("mcp.client", name, arguments, None, run)

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
    kinds = {record.kind for record in records}
    assert "agent.llm" in kinds
    assert "mcp.client" in kinds
    assert {record.trace_id for record in records} == {"trace-trip-demo"}


if __name__ == "__main__":
    demo()
