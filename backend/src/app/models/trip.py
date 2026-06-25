"""Trip planning request and response models."""

from typing import Literal

from pydantic import BaseModel, Field

BudgetLevel = Literal["low", "medium", "high"]
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
    days: int = Field(..., ge=1, le=14)
    budget: BudgetLevel = "medium"
    travel_style: TravelStyle = "relaxed"
    month: str = ""
    notes: str = Field(default="", max_length=500)


class TripDay(BaseModel):
    """One day in the generated itinerary."""

    day: int
    title: str
    theme: str
    morning: str
    afternoon: str
    evening: str
    notes: list[str]


class TripPlanResponse(BaseModel):
    """Generated trip plan returned to the frontend."""

    trip_id: str
    destination: str
    summary: str
    days: list[TripDay]
    tips: list[str]
    disclaimer: str
