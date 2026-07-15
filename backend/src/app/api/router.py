"""Application API routes."""

import json
from collections.abc import Iterator
from uuid import uuid4

from fastapi import APIRouter, HTTPException, Request, Response
from fastapi.responses import StreamingResponse

from src.app.api.auth import router as auth_router
from src.app.core.config import settings
from src.app.core.tracing import trace_context
from src.app.graph.trip_planner import plan_trip_with_graph, stream_trip_with_graph
from src.app.models.trip import TripPlanRequest, TripPlanResponse
from src.app.services.llm_service import LLMTimeoutError
from src.app.services.trace_store import list_trace_spans

api_router = APIRouter()
api_router.include_router(auth_router)


@api_router.get("/health")
def health_check() -> dict[str, str]:
    """Return a lightweight API health signal."""

    return {"status": "ok"}


@api_router.post("/trips/plan", response_model=TripPlanResponse)
def plan_trip(request: TripPlanRequest, http_request: Request, response: Response) -> TripPlanResponse:
    """Generate a trip plan through the LangGraph agent."""

    with trace_context(http_request.headers.get("X-Trace-Id")) as trace_id:
        response.headers["X-Trace-Id"] = trace_id
        try:
            return plan_trip_with_graph(request)
        except LLMTimeoutError as exc:
            raise HTTPException(status_code=504, detail="大模型响应超时，请稍后再试。") from exc
        except Exception as exc:
            raise HTTPException(
                status_code=500,
                detail="Unable to create a plan for the supplied request.",
            ) from exc


@api_router.post("/trips/plan/stream")
def stream_plan_trip(request: TripPlanRequest, http_request: Request) -> StreamingResponse:
    """Stream trip planning progress and the final plan as NDJSON."""

    trace_id = http_request.headers.get("X-Trace-Id") or str(uuid4())

    def events() -> Iterator[str]:
        with trace_context(trace_id) as active_trace_id:
            yield json.dumps({"type": "trace", "trace_id": active_trace_id}, ensure_ascii=False) + "\n"
            try:
                for event in stream_trip_with_graph(request):
                    yield json.dumps(event, ensure_ascii=False) + "\n"
            except LLMTimeoutError:
                yield json.dumps({"type": "error", "message": "大模型响应超时，请稍后再试。"}, ensure_ascii=False) + "\n"
            except Exception:
                yield json.dumps({"type": "error", "message": "规划器暂时无法生成行程。"}, ensure_ascii=False) + "\n"

    return StreamingResponse(events(), media_type="application/x-ndjson", headers={"X-Trace-Id": trace_id})


@api_router.get("/traces/{trace_id}")
def get_trace(trace_id: str) -> dict[str, object]:
    """Return spans for one trace in development or when explicitly enabled."""

    if not settings.effective_trace_query_enabled:
        raise HTTPException(status_code=404, detail="Trace query is disabled.")
    return {"trace_id": trace_id, "spans": list_trace_spans(trace_id)}
