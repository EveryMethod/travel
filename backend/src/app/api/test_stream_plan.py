"""Self-checks for streaming trip planning routes."""

import json

from fastapi.testclient import TestClient

from src.app.api import router as api_router
from src.app.core import tracing
from src.app.main import app
from src.app.models.db import User


class FakeSession:
    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, traceback):
        return False


def demo() -> None:
    records: list[tracing.CallTraceRecord] = []

    def traced_events(request):
        yield {"type": "status", "message": "ok"}
        tracing.trace_call("agent.llm", "stream-demo", {"destination": request.destination}, None, lambda: {"ok": True})
        yield {
            "type": "plan",
            "data": {
                "trip_id": "demo",
                "destination": "北京",
                "summary": "demo",
                "days": [{"day": 1, "date": "2026-07-20", "title": "demo", "items": [], "notes": []}],
                "tips": [],
                "disclaimer": "demo",
            },
        }
        yield {"type": "done"}

    old_stream = api_router.stream_trip_with_graph
    old_store = api_router.create_completed_trip
    old_session = api_router.SessionLocal
    old_write_record = tracing._write_record
    app.dependency_overrides[api_router.require_current_user] = lambda: User(id=1, display_name="demo")
    api_router.stream_trip_with_graph = traced_events
    api_router.create_completed_trip = lambda **kwargs: kwargs["plan"]
    api_router.SessionLocal = FakeSession
    tracing._write_record = lambda record: records.append(record)
    try:
        with TestClient(app) as client:
            response = client.post(
                "/api/trips/plan/stream",
                headers={"Authorization": "Bearer demo", "X-Trace-Id": "  trace-stream-demo  "},
                json={"destination": "北京", "days": 1, "travel_style": ["culture"]},
            )
    finally:
        api_router.stream_trip_with_graph = old_stream
        api_router.create_completed_trip = old_store
        api_router.SessionLocal = old_session
        tracing._write_record = old_write_record
        app.dependency_overrides.clear()

    assert response.status_code == 200
    lines = [json.loads(line) for line in response.text.splitlines()]
    assert lines[0] == {"type": "trace", "trace_id": "trace-stream-demo"}
    assert [line["type"] for line in lines] == ["trace", "status", "plan", "done"]
    assert records
    assert {record.trace_id for record in records} == {"trace-stream-demo"}


if __name__ == "__main__":
    demo()
