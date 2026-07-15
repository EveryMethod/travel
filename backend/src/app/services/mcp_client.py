"""Client for the local travel MCP gateway."""

from typing import Any

import httpx

from src.app.core.config import settings


def call_tool(name: str, arguments: dict[str, Any]) -> dict[str, Any]:
    """Call one map tool through the MCP gateway boundary."""

    response = httpx.post(
        f"{settings.mcp_gateway_url.rstrip('/')}/mcp/tools/{name}",
        json=arguments,
        timeout=settings.mcp_timeout_seconds,
    )
    response.raise_for_status()
    return response.json()
