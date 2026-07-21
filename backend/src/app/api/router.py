"""Application API routes."""

import json
from collections.abc import Iterator
from uuid import uuid4

from fastapi import APIRouter, Depends, HTTPException, Request, Response
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from src.app.api.auth import require_current_user, router as auth_router
from src.app.core.config import settings
from src.app.core.database import SessionLocal, get_db
from src.app.core.tracing import trace_context
from src.app.graph.trip_planner import plan_trip_with_graph, stream_trip_with_graph
from src.app.models.db import User
from src.app.models.trip import SavedTripDetail, SavedTripListItem, TripPlanRequest, TripPlanResponse
from src.app.services.llm_service import LLMTimeoutError
from src.app.services.trace_store import list_trace_spans
from src.app.services.trip_store import create_completed_trip, delete_user_trip, get_user_trip_detail, list_user_trips

api_router = APIRouter()
api_router.include_router(auth_router)


@api_router.get("/health")
def health_check() -> dict[str, str]:
    """Return a lightweight API health signal."""

    return {"status": "ok"}


@api_router.post("/trips/plan", response_model=TripPlanResponse)
def plan_trip(
    request: TripPlanRequest,
    http_request: Request,
    response: Response,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_current_user),
) -> TripPlanResponse:
    """Generate and save a trip plan through the LangGraph agent."""

    with trace_context(http_request.headers.get("X-Trace-Id")) as trace_id:
        response.headers["X-Trace-Id"] = trace_id
        try:
            plan = plan_trip_with_graph(request)
            return create_completed_trip(db=db, user_id=current_user.id, trace_id=trace_id, request=request, plan=plan)
        except LLMTimeoutError as exc:
            raise HTTPException(status_code=504, detail="大模型响应超时，请稍后再试。") from exc
        except Exception as exc:
            raise HTTPException(
                status_code=500,
                detail="Unable to create a plan for the supplied request.",
            ) from exc


@api_router.post("/trips/plan/stream")
def stream_plan_trip(
    request: TripPlanRequest,
    http_request: Request,
    current_user: User = Depends(require_current_user),
) -> StreamingResponse:
    """Stream trip planning progress and save the final plan as NDJSON."""

    with trace_context(http_request.headers.get("X-Trace-Id") or str(uuid4())) as trace_id:
        pass
    user_id = current_user.id

    def events() -> Iterator[str]:
        # ponytail: StreamingResponse advances sync generators across contexts; don't hold ContextVar tokens across yields.
        yield json.dumps({"type": "trace", "trace_id": trace_id}, ensure_ascii=False) + "\n"
        try:
            planner = stream_trip_with_graph(request)
            while True:
                try:
                    with trace_context(trace_id):
                        event = next(planner)
                except StopIteration:
                    break
                if event.get("type") == "plan":
                    plan = TripPlanResponse.model_validate(event["data"])
                    with SessionLocal() as db:
                        saved_plan = create_completed_trip(
                            db=db,
                            user_id=user_id,
                            trace_id=trace_id,
                            request=request,
                            plan=plan,
                        )
                    yield json.dumps({"type": "plan", "data": saved_plan.model_dump()}, ensure_ascii=False) + "\n"
                    continue
                yield json.dumps(event, ensure_ascii=False) + "\n"
        except LLMTimeoutError:
            yield json.dumps({"type": "error", "message": "大模型响应超时，请稍后再试。"}, ensure_ascii=False) + "\n"
        except Exception:
            yield json.dumps({"type": "error", "message": "规划器暂时无法生成行程。"}, ensure_ascii=False) + "\n"

    return StreamingResponse(events(), media_type="application/x-ndjson", headers={"X-Trace-Id": trace_id})


@api_router.get("/trips", response_model=list[SavedTripListItem])
def list_trips(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_current_user),
) -> list[SavedTripListItem]:
    return list_user_trips(db=db, user_id=current_user.id)


@api_router.get("/trips/{trip_id}", response_model=SavedTripDetail)
def get_trip(
    trip_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_current_user),
) -> SavedTripDetail:
    return get_user_trip_detail(db=db, user_id=current_user.id, trip_id=trip_id)


@api_router.delete("/trips/{trip_id}", status_code=204)
def delete_trip(
    trip_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_current_user),
) -> Response:
    delete_user_trip(db=db, user_id=current_user.id, trip_id=trip_id)
    return Response(status_code=204)


@api_router.get("/traces/{trace_id}")
def get_trace(trace_id: str) -> dict[str, object]:
    """Return spans for one trace in development or when explicitly enabled."""

    if not settings.effective_trace_query_enabled:
        raise HTTPException(status_code=404, detail="Trace query is disabled.")
    return {"trace_id": trace_id, "spans": list_trace_spans(trace_id)}
