"""Trip planning request and response models."""

from datetime import datetime
from typing import Annotated, Literal

from pydantic import BaseModel, Field, StringConstraints, model_validator

TravelStyle = Literal[
    "culture",
    "food",
    "nature",
    "family",
    "romantic",
    "adventure",
    "relaxed",
]
TravelPace = Literal["relaxed", "balanced", "packed"]
TravelCompanions = Literal["solo", "couple", "friends", "family", "seniors"]
TransportMode = Literal["flight", "rail", "drive"]
TransportDataQuality = Literal["live", "provider_live", "estimate"]
RevisionInstruction = Annotated[
    str,
    StringConstraints(strip_whitespace=True, min_length=1, max_length=500),
]


class TravelerParty(BaseModel):
    adults: int = Field(default=1, ge=1, le=9)
    children: int = Field(default=0, ge=0, le=8)
    infants: int = Field(default=0, ge=0, le=9)

    @model_validator(mode="after")
    def validate_infants(self) -> "TravelerParty":
        if self.infants > self.adults:
            raise ValueError("infants cannot exceed accompanying adults")
        return self


class TransportSegment(BaseModel):
    service_number: str = ""
    carrier: str = ""
    departure_at: datetime | None = None
    arrival_at: datetime | None = None
    from_terminal: str = ""
    to_terminal: str = ""


class TransportLeg(BaseModel):
    direction: Literal["outbound", "return"]
    departure_at: datetime | None = None
    arrival_at: datetime | None = None
    duration_minutes: int | None = None
    transfer_count: int = 0
    segments: list[TransportSegment] = Field(default_factory=list)


class TransportOption(BaseModel):
    id: str
    mode: TransportMode
    provider: str
    data_quality: TransportDataQuality
    total_price: str = ""
    currency: str = "CNY"
    estimated_price_range: str = ""
    fare_details: list[str] = Field(default_factory=list)
    outbound: TransportLeg
    return_leg: TransportLeg
    booking_hint: str
    source_url: str = ""


class IntercityTransportPlan(BaseModel):
    origin: str
    destination: str
    recommended_option_id: str | None = None
    recommendation_reason: str = ""
    options: list[TransportOption] = Field(default_factory=list, max_length=3)
    destination_ready_at: datetime | None = None
    destination_depart_by: datetime | None = None
    searched_at: datetime
    warnings: list[str] = Field(default_factory=list)


class BudgetBreakdown(BaseModel):
    """Structured trip budget inputs."""

    transport: str = ""
    hotel: str = ""
    food: str = ""
    tickets: str = ""


class TripPlanRequest(BaseModel):
    """User preferences for a generated trip plan."""

    destination: str = Field(..., min_length=1)
    origin: str = ""
    days: int = Field(..., ge=1, le=10)
    budget: str = ""
    budget_breakdown: BudgetBreakdown = Field(default_factory=BudgetBreakdown)
    travel_style: list[TravelStyle] = Field(default_factory=lambda: ["relaxed"])
    pace: TravelPace = "balanced"
    companions: TravelCompanions = "friends"
    start_date: str = ""
    end_date: str = ""
    must_see: str = Field(default="", max_length=300)
    avoid: str = Field(default="", max_length=300)
    notes: str = Field(default="", max_length=500)
    revision_instructions: list[RevisionInstruction] = Field(default_factory=list, max_length=10)
    travelers: TravelerParty = Field(default_factory=TravelerParty)


class TripRevisionRequest(BaseModel):
    """Natural-language instruction for revising a trip plan."""

    instruction: RevisionInstruction


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
    intercity_transport: IntercityTransportPlan | None = None


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
