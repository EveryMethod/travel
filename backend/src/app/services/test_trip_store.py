"""Self-checks for saved trip persistence helpers."""

from datetime import datetime
from pathlib import Path
import sys
from types import SimpleNamespace

from fastapi import HTTPException

sys.path.insert(0, str(Path(__file__).resolve().parents[3]))

from src.app.models.trip import TripPlanRequest, TripPlanResponse  # noqa: E402
from src.app.services.trip_store import get_user_trip_or_404  # noqa: E402


def demo() -> None:
    class FakeDb:
        def __init__(self):
            self.trip = SimpleNamespace(id=7, user_id=42, created_at=datetime.utcnow())

        def get(self, model, trip_id):
            if trip_id == 7:
                return self.trip
            return None

    db = FakeDb()
    assert get_user_trip_or_404(db=db, user_id=42, trip_id=7).id == 7

    try:
        get_user_trip_or_404(db=db, user_id=99, trip_id=7)
    except HTTPException as exc:
        assert exc.status_code == 404
    else:
        raise AssertionError("cross-user trip access must return 404")

    try:
        get_user_trip_or_404(db=db, user_id=42, trip_id=8)
    except HTTPException as exc:
        assert exc.status_code == 404
    else:
        raise AssertionError("missing trip must return 404")

    request = TripPlanRequest(destination="北京", origin="上海", days=1, travel_style=["culture"])
    plan = TripPlanResponse(
        trip_id="draft",
        destination="北京",
        summary="一天北京行程。",
        days=[],
        tips=[],
        disclaimer="请以实际信息为准。",
    )
    assert request.destination == plan.destination


if __name__ == "__main__":
    demo()
