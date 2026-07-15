"""Trip planning request and response models."""

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field

TravelStyle = Literal[
    "culture",
    "food",
    "nature",
    "family",
    "romantic",
    "adventure",
    "relaxed",
]


class TripPlanRequest(BaseModel):
    """User preferences for a generated trip plan."""

    destination: str = Field(..., min_length=1)
    origin: str = ""
    days: int = Field(..., ge=1, le=10)
    budget: str = ""
    travel_style: list[TravelStyle] = Field(default_factory=lambda: ["relaxed"])
    start_date: str = ""
    end_date: str = ""
    notes: str = Field(default="", max_length=500)


class TripPlanItem(BaseModel):
    """One scheduled stop or activity in the generated itinerary."""

    time: str
    place: str
    activity: str
    estimated_cost: str = "需查询官方渠道"
    booking_hint: str = "出发前核实官方信息"
    source_hint: str = "价格为搜索参考，需核实"


class TripDay(BaseModel):
    """One day in the generated itinerary."""

    day: int
    date: str
    title: str
    weather: str = "以实时天气为准"
    items: list[TripPlanItem]
    daily_budget: str = "按实际消费调整"
    transport: str = "以当日交通为准"
    notes: list[str]


class TripPlanResponse(BaseModel):
    """Generated trip plan returned to the frontend."""

    trip_id: str
    destination: str
    summary: str
    days: list[TripDay]
    tips: list[str]
    disclaimer: str


class SavedTripListItem(BaseModel):
    id: int
    destination: str
    days: int
    status: Literal["completed"]
    created_at: datetime


class SavedTripDetail(SavedTripListItem):
    trace_id: str | None
    request_json: TripPlanRequest
    plan_json: TripPlanResponse
    updated_at: datetime
