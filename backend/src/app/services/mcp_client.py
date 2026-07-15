"""Client for the local travel MCP gateway."""

from typing import Any

import httpx

from src.app.core.config import settings
from src.app.core.tracing import trace_call


def call_tool(name: str, arguments: dict[str, Any]) -> dict[str, Any]:
    """Call one map tool through the MCP gateway boundary."""

    return trace_call(
        "mcp.client",
        name,
        arguments,
        {"gateway_url": settings.mcp_gateway_url, "timeout_seconds": settings.mcp_timeout_seconds},
        lambda: _call_tool_untraced(name, arguments),
    )


def _call_tool_untraced(name: str, arguments: dict[str, Any]) -> dict[str, Any]:
    response = httpx.post(
        f"{settings.mcp_gateway_url.rstrip('/')}/mcp/tools/{name}",
        json=arguments,
        timeout=settings.mcp_timeout_seconds,
    )
    response.raise_for_status()
    return response.json()
