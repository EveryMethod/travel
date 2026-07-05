"""Application API routes."""

from fastapi import APIRouter, HTTPException

from src.app.api.auth import router as auth_router
from src.app.graph.trip_planner import plan_trip_with_graph
from src.app.models.trip import TripPlanRequest, TripPlanResponse

api_router = APIRouter()
api_router.include_router(auth_router)


@api_router.get("/health")
def health_check() -> dict[str, str]:
    """Return a lightweight API health signal."""

    return {"status": "ok"}


@api_router.post("/trips/plan", response_model=TripPlanResponse)
def plan_trip(request: TripPlanRequest) -> TripPlanResponse:
    """Generate a demo trip plan through the LangGraph skeleton."""

    try:
        return plan_trip_with_graph(request)
    except Exception as exc:
        raise HTTPException(
            status_code=500,
            detail="Unable to create a plan for the supplied request.",
        ) from exc
