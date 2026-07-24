"""Persistence helpers for saved trips."""

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from src.app.models.db import Trip
from src.app.models.trip import SavedTripDetail, SavedTripListItem, TripPlanRequest, TripPlanResponse


def create_completed_trip(
    *,
    db: Session,
    user_id: int,
    trace_id: str | None,
    request: TripPlanRequest,
    plan: TripPlanResponse,
) -> TripPlanResponse:
    trip = Trip(
        user_id=user_id,
        trace_id=trace_id,
        destination=request.destination,
        days=request.days,
        status="completed",
        request_json=request.model_dump(),
        plan_json={},
    )
    db.add(trip)
    db.flush()

    plan.trip_id = str(trip.id)
    plan.destination = plan.destination or request.destination
    trip.plan_json = plan.model_dump()
    db.commit()
    return plan


def list_user_trips(*, db: Session, user_id: int) -> list[SavedTripListItem]:
    trips = db.scalars(select(Trip).where(Trip.user_id == user_id).order_by(Trip.created_at.desc(), Trip.id.desc())).all()
    return [
        SavedTripListItem(
            id=trip.id,
            destination=trip.destination,
            days=trip.days,
            status="completed",
            created_at=trip.created_at,
        )
        for trip in trips
    ]


def get_user_trip_or_404(*, db: Session, user_id: int, trip_id: int) -> Trip:
    trip = db.get(Trip, trip_id)
    if not trip or trip.user_id != user_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="行程不存在。")
    return trip


def get_user_trip_detail(*, db: Session, user_id: int, trip_id: int) -> SavedTripDetail:
    trip = get_user_trip_or_404(db=db, user_id=user_id, trip_id=trip_id)
    return SavedTripDetail(
        id=trip.id,
        destination=trip.destination,
        days=trip.days,
        status="completed",
        created_at=trip.created_at,
        updated_at=trip.updated_at,
        trace_id=trip.trace_id,
        request_json=TripPlanRequest.model_validate(trip.request_json),
        plan_json=TripPlanResponse.model_validate(trip.plan_json),
    )


def replace_user_trip_plan(*, db: Session, user_id: int, trip_id: int, plan: TripPlanResponse) -> TripPlanResponse:
    trip = get_user_trip_or_404(db=db, user_id=user_id, trip_id=trip_id)
    plan.trip_id = str(trip.id)
    trip.plan_json = plan.model_dump(mode="json")
    db.commit()
    return plan


def delete_user_trip(*, db: Session, user_id: int, trip_id: int) -> None:
    trip = get_user_trip_or_404(db=db, user_id=user_id, trip_id=trip_id)
    db.delete(trip)
    db.commit()
