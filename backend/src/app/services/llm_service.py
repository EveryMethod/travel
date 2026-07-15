"""OpenAI-compatible LLM helpers."""

import json
from typing import Any

import httpx

from src.app.core.config import settings


class LLMTimeoutError(RuntimeError):
    """Raised when the configured LLM does not answer in time."""


def generate_json(messages: list[dict[str, str]]) -> dict[str, Any]:
    """Call the configured LLM and parse its JSON response."""

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
