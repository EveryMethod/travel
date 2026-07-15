"""Reusable call tracing helpers."""

from __future__ import annotations

import json
import logging
import math
import re
import time
from collections.abc import Callable, Iterator
from itertools import islice
from contextlib import contextmanager
from contextvars import ContextVar, Token
from dataclasses import dataclass
from datetime import UTC, datetime
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
_REDACTED = "***REDACTED***"


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
    active_trace_id = _trace_id_for_storage(trace_id)
    trace_token = _trace_id.set(active_trace_id)
    span_token = _span_id.set(None)
    try:
        yield active_trace_id
    finally:
        _span_id.reset(span_token)
        _trace_id.reset(trace_token)


def current_trace_id() -> str | None:
    return _trace_id.get()


def _trace_id_for_storage(trace_id: str | None = None) -> str:
    value = (trace_id or str(uuid4())).strip()
    return value[:36] or str(uuid4())


def trace_call(kind: str, name: str, input_data: Any, metadata: dict[str, Any] | None, func: Callable[[], T]) -> T:
    if not settings.trace_enabled:
        return func()

    if kind not in {"agent.llm", "mcp.client", "tool.execute"}:
        return func()

    trace_token: Token[str | None] | None = None
    trace_id = current_trace_id()
    if trace_id is None:
        trace_id = str(uuid4())
        trace_token = _trace_id.set(trace_id)

    name = name[:128]
    input_summary = summarize_value(input_data)
    metadata_summary = summarize_value(metadata or {})
    parent_span_id = _span_id.get()
    span_id = str(uuid4())
    span_token = _span_id.set(span_id)
    started_at = datetime.now(UTC).replace(tzinfo=None)
    started_perf = time.perf_counter()
    status = "ok"
    output_summary: Any = None
    error_type: str | None = None
    error_message: str | None = None

    try:
        result = func()
        output_summary = summarize_value(result)
        return result
    except BaseException as exc:
        status = "error"
        error_type = exc.__class__.__name__
        error_message = _redact_text(str(exc), 500)
        raise
    finally:
        try:
            ended_at = datetime.now(UTC).replace(tzinfo=None)
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
                input_summary=input_summary,
                output_summary=output_summary,
                error_type=error_type,
                error_message=error_message,
                metadata=metadata_summary,
            )
            _safe_write_record(record)
        finally:
            _span_id.reset(span_token)
            if trace_token is not None:
                _trace_id.reset(trace_token)


def summarize_value(value: Any, max_chars: int | None = None) -> Any:
    limit = settings.trace_summary_max_chars if max_chars is None else max_chars
    try:
        return _summarize(value, max(0, limit))
    except Exception as exc:
        if isinstance(value, dict):
            return {"type": "dict", "items": {}}
        return {"summary_error": exc.__class__.__name__}


def _summarize(value: Any, limit: int) -> Any:
    if isinstance(value, dict):
        return _summarize_dict(value, limit)
    if isinstance(value, list):
        return {"type": "list", "length": len(value), "items": [_summarize(item, limit) for item in value[:3]]}
    if isinstance(value, tuple):
        return {"type": "tuple", "length": len(value), "items": [_summarize(item, limit) for item in value[:3]]}
    if isinstance(value, str):
        prefix = value[:limit]
        redacted = _redact_text(prefix, limit)
        return redacted if len(value) <= limit else {"type": "str", "length": len(value), "prefix": redacted}
    if isinstance(value, float):
        return value if math.isfinite(value) else {"type": "float", "value": str(value)}
    if isinstance(value, (int, bool)) or value is None:
        return value
    return {"type": value.__class__.__name__}


def _summarize_dict(value: dict[Any, Any], limit: int) -> dict[str, Any]:
    items: dict[str, Any] = {}
    max_items = 20
    for key, item in islice(value.items(), max_items):
        key_text = str(key)
        redacted_key = _redact_text(key_text, limit)
        safe_key = redacted_key if redacted_key != key_text else key_text
        if safe_key in items:
            safe_key = f"{safe_key}#{len(items)}"
        items[safe_key] = _REDACTED if _is_sensitive_key(key_text) else _summarize(item, limit)
    if len(value) > max_items:
        items["__truncated__"] = {"type": "dict", "length": len(value), "remaining": len(value) - max_items}
    return items


def _is_sensitive_key(key: str) -> bool:
    key_lower = key.lower().replace("-", "_")
    return key_lower in _SENSITIVE_PARTS or key_lower.endswith(("_key", "_token", "_secret", "_password"))


def _redact_text(text: str, limit: int) -> str:
    redacted = re.sub(
        r"(?i)([\"']?authorization[\"']?\s*[:=]\s*)(\"[^\"]*\"|'[^']*'|[^,;}]+)",
        lambda match: f"{match.group(1)}{_REDACTED}",
        text,
    )
    redacted = re.sub(
        r"(?i)([\"']?(?:api[_-]?key|access[_-]?token|refresh[_-]?token|token|secret|password|key)[\"']?\s*[:=]\s*)(\"[^\"]*\"|'[^']*'|[^\s,;}]+)",
        lambda match: f"{match.group(1)}{_REDACTED}",
        redacted,
    )
    redacted = re.sub(
        r"(?i)\b(password|secret|token|api[_-]?key)\b\s+(?:is\s+)?[^\s,;]+",
        lambda match: f"{match.group(1)} {_REDACTED}",
        redacted,
    )
    return redacted[:limit]


def _safe_write_record(record: CallTraceRecord) -> None:
    try:
        _write_record(record)
    except Exception as exc:
        try:
            logger.warning(
                json.dumps(
                    {
                        "event": "trace_write_error",
                        "trace_id": record.trace_id,
                        "span_id": record.span_id,
                        "error_type": exc.__class__.__name__,
                        "error_message": _redact_text(str(exc), 500),
                    },
                    ensure_ascii=False,
                )
            )
        except Exception:
            pass


def _write_record(record: CallTraceRecord) -> None:
    if logger.isEnabledFor(logging.INFO):
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
                    "error_message": _redact_text(str(exc), 500),
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
    old_logger_disabled = logger.disabled
    _write_record = fake_write
    try:
        assert current_trace_id() is None
        with trace_context("trace-demo") as trace_id:
            assert trace_id == "trace-demo"
            assert current_trace_id() == "trace-demo"
            redacted = summarize_value({"api_key": "secret", "city": "杭州"})
            assert redacted == {"api_key": _REDACTED, "city": "杭州"}
            assert trace_call("mcp.client", "demo_tool", {"city": "杭州"}, None, lambda: {"ok": True}) == {"ok": True}
            try:
                trace_call(
                    "tool.execute",
                    "boom",
                    {},
                    None,
                    lambda: (_ for _ in ()).throw(ValueError("password=hunter2 token abc")),
                )
            except ValueError:
                pass
        assert len(records) == 2
        assert records[0].status == "ok"
        assert records[1].status == "error"
        assert records[1].error_type == "ValueError"
        assert "hunter2" not in records[1].error_message
        assert "abc" not in records[1].error_message

        records.clear()
        trace_call(
            "mcp.client",
            "implicit",
            {},
            None,
            lambda: trace_call("tool.execute", "implicit", {}, None, lambda: current_trace_id()),
        )
        assert records[0].trace_id == records[1].trace_id
        assert records[0].parent_span_id == records[1].span_id
        assert current_trace_id() is None

        logger.disabled = True
        _write_record = lambda record: (_ for _ in ()).throw(RuntimeError("secret=leak"))
        assert trace_call("tool.execute", "write", {}, None, lambda: "ok") == "ok"
        try:
            trace_call("tool.execute", "error", {}, None, lambda: (_ for _ in ()).throw(ValueError("original")))
        except ValueError as exc:
            assert str(exc) == "original"
        assert current_trace_id() is None

        class SecretRepr:
            def __repr__(self) -> str:
                return "password=hunter2"

        object_summary = summarize_value(SecretRepr())
        assert "repr" not in object_summary
        assert "hunter2" not in json.dumps(object_summary)
        capped = summarize_value({str(index): index for index in range(21)})
        assert capped["19"] == 19
        assert capped["__truncated__"] == {"type": "dict", "length": 21, "remaining": 1}
        assert summarize_value("abcd", max_chars=0)["prefix"] == ""
        assert "hunter2" not in _redact_text('{"api_key":"hunter2", "password": "hunter2", "Authorization":"Bearer hunter2"}', 500)
        assert "dXNlcjpwYXNz" not in _redact_text("Authorization: Basic dXNlcjpwYXNz", 500)
        assert "hunter2" not in _redact_text("password is hunter2", 500)
        assert summarize_value({"keywords": "西湖", "api_key": "secret"}) == {"keywords": "西湖", "api_key": _REDACTED}
        assert summarize_value({"abcdef": 1, "abcxyz": 2}, max_chars=3) == {"abc": 1, "abc#1": 2}
        assert summarize_value(float("nan")) == {"type": "float", "value": "nan"}
        assert len(_trace_id_for_storage("x" * 100)) == 36

        _write_record = fake_write
        mutable_input = {"city": "杭州"}
        trace_call("mcp.client", "x" * 200, mutable_input, None, lambda: mutable_input.update({"city": "上海"}))
        assert records[-1].name == "x" * 128
        assert records[-1].input_summary == {"city": "杭州"}

        _write_record = fake_write
        try:
            trace_call("tool.execute", "base-exc", {}, None, lambda: (_ for _ in ()).throw(KeyboardInterrupt("stop")))
        except KeyboardInterrupt:
            pass
        assert records[-1].status == "error"
        assert records[-1].error_type == "KeyboardInterrupt"
    finally:
        logger.disabled = old_logger_disabled
        _write_record = old_write_record


if __name__ == "__main__":
    demo()
