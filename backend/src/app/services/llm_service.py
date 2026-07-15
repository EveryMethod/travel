"""OpenAI-compatible LLM helpers."""

import json
from typing import Any

import httpx

from src.app.core.config import settings
from src.app.core.tracing import trace_call


class LLMTimeoutError(RuntimeError):
    """Raised when the configured LLM does not answer in time."""


def generate_json(messages: list[dict[str, str]]) -> dict[str, Any]:
    """Call the configured LLM and parse its JSON response."""

    return trace_call(
        "agent.llm",
        settings.llm_name,
        _summarize_messages(messages),
        {"base_url": settings.openai_base_url, "timeout_seconds": settings.llm_timeout_seconds, "response_format": "json_object"},
        lambda: _generate_json_untraced(messages),
    )


def _generate_json_untraced(messages: list[dict[str, str]]) -> dict[str, Any]:
    if not settings.openai_api_key:
        raise RuntimeError("OPENAI_API_KEY is not configured.")

    try:
        response = httpx.post(
            f"{settings.openai_base_url.rstrip('/')}/chat/completions",
            headers={"Authorization": f"Bearer {settings.openai_api_key}"},
            json={
                "model": settings.llm_name,
                "messages": messages,
                "temperature": settings.llm_temperature,
                "response_format": {"type": "json_object"},
            },
            timeout=settings.llm_timeout_seconds,
        )
    except httpx.TimeoutException as exc:
        raise LLMTimeoutError("LLM request timed out.") from exc
    response.raise_for_status()
    content = response.json()["choices"][0]["message"]["content"]
    return json.loads(content)


def _summarize_messages(messages: list[dict[str, str]]) -> dict[str, Any]:
    return {
        "message_count": len(messages),
        "roles": [message.get("role", "") for message in messages],
        "total_content_chars": sum(len(message.get("content", "")) for message in messages),
    }
