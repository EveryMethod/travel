"""Persistence helpers for call trace records."""

from __future__ import annotations

from typing import Any

from sqlalchemy import select

from src.app.core.database import SessionLocal
from src.app.core.tracing import CallTraceRecord
from src.app.models.db import CallTrace


def write_trace(record: CallTraceRecord) -> None:
    with SessionLocal() as db:
        db.add(
            CallTrace(
                trace_id=record.trace_id,
                span_id=record.span_id,
                parent_span_id=record.parent_span_id,
                kind=record.kind,
                name=record.name,
                status=record.status,
                started_at=record.started_at,
                ended_at=record.ended_at,
                duration_ms=record.duration_ms,
                input_summary=record.input_summary,
                output_summary=record.output_summary,
                error_type=record.error_type,
                error_message=record.error_message,
                metadata_json=record.metadata,
            )
        )
        db.commit()


def list_trace_spans(trace_id: str) -> list[dict[str, Any]]:
    with SessionLocal() as db:
        rows = db.scalars(select(CallTrace).where(CallTrace.trace_id == trace_id).order_by(CallTrace.started_at, CallTrace.id)).all()
        return [_serialize_trace(row) for row in rows]


def _serialize_trace(row: CallTrace) -> dict[str, Any]:
    return {
        "id": row.id,
        "trace_id": row.trace_id,
        "span_id": row.span_id,
        "parent_span_id": row.parent_span_id,
        "kind": row.kind,
        "name": row.name,
        "status": row.status,
        "started_at": row.started_at.isoformat() if row.started_at else None,
        "ended_at": row.ended_at.isoformat() if row.ended_at else None,
        "duration_ms": row.duration_ms,
        "input_summary": row.input_summary,
        "output_summary": row.output_summary,
        "error_type": row.error_type,
        "error_message": row.error_message,
        "metadata": row.metadata_json,
        "created_at": row.created_at.isoformat() if row.created_at else None,
    }


def demo() -> None:
    row = type(
        "Row",
        (),
        {
            "id": 1,
            "trace_id": "trace-demo",
            "span_id": "span-demo",
            "parent_span_id": None,
            "kind": "mcp.client",
            "name": "amap_weather",
            "status": "ok",
            "started_at": None,
            "ended_at": None,
            "duration_ms": 1,
            "input_summary": {"city": "杭州"},
            "output_summary": {"keys": ["lives"]},
            "error_type": None,
            "error_message": None,
            "metadata_json": {"a": 1},
            "created_at": None,
        },
    )()
    assert _serialize_trace(row)["metadata"] == {"a": 1}
    assert _serialize_trace(row)["name"] == "amap_weather"


if __name__ == "__main__":
    demo()
