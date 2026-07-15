"""Reusable call tracing helpers."""

from __future__ import annotations

import json
import logging
import time
from collections.abc import Callable, Iterator
from contextlib import contextmanager
from contextvars import ContextVar
from dataclasses import dataclass
from datetime import datetime
from typing import Any, TypeVar
from uuid import uuid4

try:
    from src.app.core.config import settings
except ModuleNotFoundError:
    if __name__ != "__main__":
        raise

    class _DemoSettings:
        trace_enabled = True
        trace_summary_max_chars = 120

    settings = _DemoSettings()

T = TypeVar("T")
logger = logging.getLogger(__name__)

_trace_id: ContextVar[str | None] = ContextVar("trace_id", default=None)
_span_id: ContextVar[str | None] = ContextVar("span_id", default=None)
_SENSITIVE_PARTS = ("key", "token", "secret", "password", "authorization", "api_key", "access_token", "refresh_token")


@dataclass(frozen=True)
class CallTraceRecord:
    trace_id: str
    span_id: str
    parent_span_id: str | None
    kind: str
    name: str
    status: str
    started_at: datetime
    ended_at: datetime
    duration_ms: int
    input_summary: Any
    output_summary: Any
    error_type: str | None
    error_message: str | None
    metadata: dict[str, Any] | None


@contextmanager
def trace_context(trace_id: str | None = None) -> Iterator[str]:
    active_trace_id = trace_id or str(uuid4())
    trace_token = _trace_id.set(active_trace_id)
    span_token = _span_id.set(None)
    try:
        yield active_trace_id
    finally:
        _span_id.reset(span_token)
        _trace_id.reset(trace_token)


def current_trace_id() -> str | None:
    return _trace_id.get()


def trace_call(kind: str, name: str, input_data: Any, metadata: dict[str, Any] | None, func: Callable[[], T]) -> T:
    if not settings.trace_enabled:
        return func()

    trace_id = current_trace_id() or str(uuid4())
    parent_span_id = _span_id.get()
    span_id = str(uuid4())
    span_token = _span_id.set(span_id)
    started_at = datetime.utcnow()
    started_perf = time.perf_counter()
    status = "ok"
    output_summary: Any = None
    error_type: str | None = None
    error_message: str | None = None

    try:
        result = func()
        output_summary = summarize_value(result)
        return result
    except Exception as exc:
        status = "error"
        error_type = exc.__class__.__name__
        error_message = str(exc)[:500]
        raise
    finally:
        ended_at = datetime.utcnow()
        record = CallTraceRecord(
            trace_id=trace_id,
            span_id=span_id,
            parent_span_id=parent_span_id,
            kind=kind,
            name=name,
            status=status,
            started_at=started_at,
            ended_at=ended_at,
            duration_ms=int((time.perf_counter() - started_perf) * 1000),
            input_summary=summarize_value(input_data),
            output_summary=output_summary,
            error_type=error_type,
            error_message=error_message,
            metadata=summarize_value(metadata or {}),
        )
        _write_record(record)
        _span_id.reset(span_token)


def summarize_value(value: Any, max_chars: int | None = None) -> Any:
    limit = max_chars or settings.trace_summary_max_chars
    try:
        return _summarize(value, limit)
    except Exception as exc:
        return {"summary_error": exc.__class__.__name__}


def _summarize(value: Any, limit: int) -> Any:
    if isinstance(value, dict):
        return {str(key): _summarize_field(str(key), item, limit) for key, item in value.items()}
    if isinstance(value, list):
        return {"type": "list", "length": len(value), "items": [_summarize(item, limit) for item in value[:3]]}
    if isinstance(value, tuple):
        return {"type": "tuple", "length": len(value), "items": [_summarize(item, limit) for item in value[:3]]}
    if isinstance(value, str):
        return value if len(value) <= limit else {"type": "str", "length": len(value), "prefix": value[:limit]}
    if isinstance(value, int | float | bool) or value is None:
        return value
    return {"type": value.__class__.__name__, "repr": repr(value)[:limit]}


def _summarize_field(key: str, value: Any, limit: int) -> Any:
    key_lower = key.lower()
    if any(part in key_lower for part in _SENSITIVE_PARTS):
        return "***REDACTED***"
    return _summarize(value, limit)


def _write_record(record: CallTraceRecord) -> None:
    log_payload = {
        "event": "call_trace",
        "trace_id": record.trace_id,
        "span_id": record.span_id,
        "parent_span_id": record.parent_span_id,
        "kind": record.kind,
        "name": record.name,
        "status": record.status,
        "duration_ms": record.duration_ms,
    }
    logger.info(json.dumps(log_payload, ensure_ascii=False))
    try:
        from src.app.services.trace_store import write_trace

        write_trace(record)
    except Exception as exc:
        logger.warning(
            json.dumps(
                {
                    "event": "trace_store_error",
                    "trace_id": record.trace_id,
                    "span_id": record.span_id,
                    "error_type": exc.__class__.__name__,
                    "error_message": str(exc)[:500],
                },
                ensure_ascii=False,
            )
        )


def demo() -> None:
    records: list[CallTraceRecord] = []

    def fake_write(record: CallTraceRecord) -> None:
        records.append(record)

    global _write_record
    old_write_record = _write_record
    _write_record = fake_write
    try:
        assert current_trace_id() is None
        with trace_context("trace-demo") as trace_id:
            assert trace_id == "trace-demo"
            assert current_trace_id() == "trace-demo"
            redacted = summarize_value({"api_key": "secret", "city": "杭州"})
            assert redacted["api_key"] == "***REDACTED***"
            assert redacted["city"] == "杭州"
            assert trace_call("mcp.client", "demo_tool", {"city": "杭州"}, None, lambda: {"ok": True}) == {"ok": True}
            try:
                trace_call("tool.execute", "boom", {}, None, lambda: (_ for _ in ()).throw(ValueError("bad")))
            except ValueError:
                pass
        assert len(records) == 2
        assert records[0].status == "ok"
        assert records[1].status == "error"
        assert records[1].error_type == "ValueError"
    finally:
        _write_record = old_write_record


if __name__ == "__main__":
    demo()
