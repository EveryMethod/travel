"""Application API routes."""

import json
from collections.abc import AsyncIterator, Iterator
from fastapi import APIRouter, Depends, HTTPException, Request, Response
from fastapi.responses import StreamingResponse
from pydantic import ValidationError
from sqlalchemy.orm import Session
from starlette.concurrency import run_in_threadpool

from src.app.api.auth import require_current_user, router as auth_router
from src.app.core.config import settings
from src.app.core.database import SessionLocal, get_db
from src.app.core.tracing import normalize_trace_id, trace_context
from src.app.graph.transport_planner import plan_transport_with_graph
from src.app.graph.trip_planner import plan_trip_with_graph, stream_trip_with_graph
from src.app.graph.trip_revision import stream_trip_revision
from src.app.models.db import User
from src.app.models.trip import SavedTripDetail, SavedTripListItem, TripPlanRequest, TripPlanResponse, TripRevisionRequest
from src.app.services.llm_service import LLMTimeoutError
from src.app.services.trace_store import list_trace_spans
from src.app.services.trip_store import (
    create_completed_trip,
    delete_user_trip,
    get_user_trip_detail,
    list_user_trips,
    replace_user_trip_plan,
)

api_router = APIRouter()
api_router.include_router(auth_router)


def _next_stream_event(iterator: Iterator[dict]) -> tuple[bool, dict | None]:
    try:
        return True, next(iterator)
    except StopIteration:
        return False, None


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

    trace_id = normalize_trace_id(http_request.headers.get("X-Trace-Id"))
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


@api_router.post("/trips/{trip_id}/revise/stream")
def stream_revise_trip(
    trip_id: int,
    request: TripRevisionRequest,
    http_request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_current_user),
) -> StreamingResponse:
    """Stream a revised copy of a saved trip and save it as a new trip."""

    source = get_user_trip_detail(db=db, user_id=current_user.id, trip_id=trip_id)
    original_request = source.request_json.model_copy(deep=True)
    original_plan = source.plan_json.model_copy(deep=True)
    user_id = current_user.id
    db.close()
    revised_request = original_request.model_copy(deep=True)
    revised_request.revision_instructions = [*revised_request.revision_instructions, request.instruction][-10:]
    trace_id = normalize_trace_id(http_request.headers.get("X-Trace-Id"))

    async def events() -> AsyncIterator[str]:
        yield json.dumps({"type": "trace", "trace_id": trace_id}, ensure_ascii=False) + "\n"
        try:
            pending_plan: TripPlanResponse | None = None
            revision = stream_trip_revision(original_request, original_plan, request.instruction)
            while True:
                if await http_request.is_disconnected():
                    return
                with trace_context(trace_id):
                    has_event, event = await run_in_threadpool(_next_stream_event, revision)
                if await http_request.is_disconnected():
                    return
                if not has_event:
                    break
                assert event is not None
                if event.get("type") == "plan":
                    pending_plan = TripPlanResponse.model_validate(event["data"])
                elif event.get("type") == "done":
                    if pending_plan is None:
                        raise RuntimeError("revision stream completed without a plan")
                    if await http_request.is_disconnected():
                        return

                    def save_plan() -> TripPlanResponse:
                        with SessionLocal() as save_db:
                            return create_completed_trip(
                                db=save_db,
                                user_id=user_id,
                                trace_id=trace_id,
                                request=revised_request,
                                plan=pending_plan,
                            )

                    saved_plan = await run_in_threadpool(save_plan)
                    yield json.dumps({"type": "plan", "data": saved_plan.model_dump()}, ensure_ascii=False) + "\n"
                    yield json.dumps(event, ensure_ascii=False) + "\n"
                    return
                elif event.get("type") in {"status", "context"}:
                    yield json.dumps(event, ensure_ascii=False) + "\n"
            raise RuntimeError("revision stream ended before completion")
        except LLMTimeoutError:
            yield json.dumps({"type": "error", "message": "大模型响应超时，请稍后再试。"}, ensure_ascii=False) + "\n"
        except ValidationError:
            yield json.dumps({"type": "error", "message": "调整后的行程格式不完整，请重新尝试。"}, ensure_ascii=False) + "\n"
        except ValueError as exc:
            message = str(exc)
            if not any("\u4e00" <= char <= "\u9fff" for char in message):
                message = "暂时无法生成调整后的行程。"
            yield json.dumps({"type": "error", "message": message}, ensure_ascii=False) + "\n"
        except Exception:
            yield json.dumps({"type": "error", "message": "暂时无法生成调整后的行程。"}, ensure_ascii=False) + "\n"

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


@api_router.post("/trips/{trip_id}/transport/refresh", response_model=TripPlanResponse)
def refresh_trip_transport(
    trip_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_current_user),
) -> TripPlanResponse:
    source = get_user_trip_detail(db=db, user_id=current_user.id, trip_id=trip_id)
    request = source.request_json.model_copy(deep=True)
    original_plan = source.plan_json.model_copy(deep=True)
    detail = "暂时没有可用的交通方案，已保留原行程。"
    try:
        transport = plan_transport_with_graph(request, force_refresh=True)
        if transport is None or not transport.options:
            raise ValueError("no transport options")
        plan = plan_trip_with_graph(request, transport_plan=transport)
        original_days = [(day.day, day.date) for day in original_plan.days]
        regenerated_days = [(day.day, day.date) for day in plan.days]
        if regenerated_days != original_days or len(set(regenerated_days)) != len(regenerated_days):
            raise ValueError("regenerated trip days changed")
    except Exception as exc:
        raise HTTPException(status_code=502, detail=detail) from exc

    if len(plan.days) > 2:
        plan.days[1:-1] = [day.model_copy(deep=True) for day in original_plan.days[1:-1]]
    return replace_user_trip_plan(db=db, user_id=current_user.id, trip_id=trip_id, plan=plan)


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
