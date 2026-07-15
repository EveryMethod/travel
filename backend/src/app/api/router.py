"""Application API routes."""

import json
from collections.abc import Iterator

from fastapi import APIRouter, HTTPException
from fastapi.responses import StreamingResponse

from src.app.api.auth import router as auth_router
from src.app.graph.trip_planner import plan_trip_with_graph, stream_trip_with_graph
from src.app.models.trip import TripPlanRequest, TripPlanResponse
from src.app.services.llm_service import LLMTimeoutError

api_router = APIRouter()
api_router.include_router(auth_router)


@api_router.get("/health")
def health_check() -> dict[str, str]:
    """Return a lightweight API health signal."""

    return {"status": "ok"}


@api_router.post("/trips/plan", response_model=TripPlanResponse)
def plan_trip(request: TripPlanRequest) -> TripPlanResponse:
    """Generate a trip plan through the LangGraph agent."""

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
def stream_plan_trip(request: TripPlanRequest) -> StreamingResponse:
    """Stream trip planning progress and the final plan as NDJSON."""

    def events() -> Iterator[str]:
        try:
            for event in stream_trip_with_graph(request):
                yield json.dumps(event, ensure_ascii=False) + "\n"
        except LLMTimeoutError:
            yield json.dumps({"type": "error", "message": "大模型响应超时，请稍后再试。"}, ensure_ascii=False) + "\n"
        except Exception:
            yield json.dumps({"type": "error", "message": "规划器暂时无法生成行程。"}, ensure_ascii=False) + "\n"

    return StreamingResponse(events(), media_type="application/x-ndjson")
