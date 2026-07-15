"""Small HTTP MCP-style gateway for AMap tools."""

from typing import Any

import httpx
from fastapi import FastAPI, HTTPException

from src.app.core.config import settings

app = FastAPI(title="Travel MCP Gateway")


@app.post("/mcp/tools/{tool_name}")
def call_tool(tool_name: str, arguments: dict[str, Any]) -> dict[str, Any]:
    if not settings.amap_api_key:
        raise HTTPException(status_code=500, detail="AMAP_API_KEY is not configured.")

    tools = {
        "amap_search_poi": _search_poi,
        "amap_geocode": _geocode,
        "amap_route_distance": _route_distance,
        "amap_weather": _weather,
        "amap_place_detail": _place_detail,
        "ticket_price_search": _ticket_price_search,
    }
    tool = tools.get(tool_name)
    if not tool:
        raise HTTPException(status_code=404, detail="Unknown MCP tool.")

    try:
        return tool(arguments)
    except httpx.HTTPError as exc:
        raise HTTPException(status_code=502, detail="AMap request failed.") from exc


def _amap_get(path: str, params: dict[str, Any]) -> dict[str, Any]:
    response = httpx.get(
        f"https://restapi.amap.com/v3/{path}",
        params={**params, "key": settings.amap_api_key, "output": "JSON"},
        timeout=settings.mcp_timeout_seconds,
    )
    response.raise_for_status()
    data = response.json()
    if data.get("status") != "1":
        raise HTTPException(status_code=502, detail=data.get("info", "AMap request failed."))
    return data


def _search_poi(arguments: dict[str, Any]) -> dict[str, Any]:
    return _amap_get(
        "place/text",
        {
            "keywords": arguments.get("keywords", ""),
            "city": arguments.get("city", ""),
            "types": arguments.get("types", ""),
            "offset": arguments.get("offset", 10),
            "page": 1,
        },
    )


def _geocode(arguments: dict[str, Any]) -> dict[str, Any]:
    return _amap_get("geocode/geo", {"address": arguments.get("address", ""), "city": arguments.get("city", "")})


def _route_distance(arguments: dict[str, Any]) -> dict[str, Any]:
    return _amap_get(
        "direction/driving",
        {
            "origin": arguments.get("origin", ""),
            "destination": arguments.get("destination", ""),
        },
    )


def _weather(arguments: dict[str, Any]) -> dict[str, Any]:
    return _amap_get("weather/weatherInfo", {"city": arguments.get("city", ""), "extensions": "base"})


def _place_detail(arguments: dict[str, Any]) -> dict[str, Any]:
    return _amap_get("place/detail", {"id": arguments.get("id", "")})


def _ticket_price_search(arguments: dict[str, Any]) -> dict[str, Any]:
    if not settings.tavily_api_key:
        return {"query": arguments.get("query", ""), "results": []}

    response = httpx.post(
        settings.tavily_search_url,
        json={
            "api_key": settings.tavily_api_key,
            "query": arguments.get("query", ""),
            "search_depth": "basic",
            "max_results": arguments.get("max_results", 5),
        },
        timeout=settings.mcp_timeout_seconds,
    )
    response.raise_for_status()
    return response.json()
