# Route Leg Estimation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 为生成后的旅游行程增加逐段地图通勤估算，并把明显过长的相邻活动通勤风险写入现有 `tips`。

**Architecture:** 保留现有 FastAPI + LangGraph 流程，只扩展 `backend/src/app/graph/trip_planner.py` 的生成后审查节点。复用现有 `call_tool("amap_geocode", ...)` 和 `call_tool("amap_route_distance", ...)`，不新增响应字段，前端继续展示已有 `tips`。

**Tech Stack:** Python 3.12+、LangGraph、Pydantic v2、现有 MCP gateway 工具、assert-based backend self-check。

## Global Constraints

- 不新增依赖。
- 不做全局路线优化。
- 不重排整天行程。
- 不新增数据库字段。
- 不新增前端复杂 UI。
- 不保证地图数据实时准确；只作为出发前核对提醒。
- 每天最多取前 4 个活动，避免 MCP 调用过多。
- 相邻活动通勤预计超过 45 分钟，视为动线风险。
- 任一地图调用失败时不中断行程生成，只跳过该段。

---

## File Structure

- Modify: `backend/src/app/graph/trip_planner.py`
  - 负责 LangGraph 规划链路和生成后审查。新增逐段通勤估算 helper，并从 `_review_plan` 调用。
- Modify: `backend/src/app/graph/test_trip_planner.py`
  - 负责现有 assert-based self-check。新增长通勤、地图失败、每天最多检查 4 个活动的覆盖。

---

### Task 1: Add route leg risk review

**Files:**
- Modify: `backend/src/app/graph/trip_planner.py:16-430`
- Modify: `backend/src/app/graph/test_trip_planner.py:1-160`

**Interfaces:**
- Consumes existing function: `call_tool(name: str, arguments: dict[str, Any]) -> dict[str, Any]`
- Consumes existing function: `_first_location(data: dict[str, Any]) -> str`
- Produces constant: `_ROUTE_LEG_MAX_ITEMS_PER_DAY: int`
- Produces constant: `_ROUTE_LEG_RISK_SECONDS: int`
- Produces helper: `_review_route_legs(plan: TripPlanResponse) -> list[str]`
- Produces helper: `_route_leg_warning(day: int, origin_place: str, destination_place: str) -> str | None`
- Produces helper: `_route_duration_seconds(data: dict[str, Any]) -> int | None`
- Updates existing function: `_review_plan(state: TripPlannerState) -> TripPlannerState` appends route leg warnings to `plan.tips`

- [ ] **Step 1: Write the failing self-check**

In `backend/src/app/graph/test_trip_planner.py`, inside `demo()`, after the existing assertions:

```python
    assert "明显高于预算" in tips
```

insert this block:

```python
    route_calls = []

    def fake_route_tool(name, arguments):
        route_calls.append((name, arguments))
        if name == "amap_geocode":
            locations = {
                "故宫": "116.397,39.916",
                "环球影城": "116.680,39.850",
                "近处咖啡": "116.681,39.850",
                "博物馆": "116.404,39.915",
                "第五站": "116.500,39.900",
            }
            return {"geocodes": [{"location": locations[arguments["address"]]}]}
        if name == "amap_route_distance":
            if arguments == {"origin": "116.397,39.916", "destination": "116.680,39.850"}:
                return {"route": {"paths": [{"duration": "3600", "distance": "30000"}]}}
            return {"route": {"paths": [{"duration": "600", "distance": "3000"}]}}
        raise AssertionError(name)

    route_plan = TripPlanResponse(
        trip_id="route-risk",
        destination="北京",
        summary="demo",
        days=[
            TripDay(
                day=1,
                date="2026-10-01",
                title="demo",
                items=[
                    TripPlanItem(time="09:00", place="故宫", activity="参观"),
                    TripPlanItem(time="11:00", place="环球影城", activity="游玩"),
                    TripPlanItem(time="15:00", place="近处咖啡", activity="休息"),
                    TripPlanItem(time="17:00", place="博物馆", activity="参观"),
                    TripPlanItem(time="20:00", place="第五站", activity="夜游"),
                ],
                notes=[],
            )
        ],
        tips=[],
        disclaimer="demo",
    )

    old_call_tool = trip_planner.call_tool
    trip_planner.call_tool = fake_route_tool
    try:
        reviewed = trip_planner._review_plan(
            {"request": structured, "context": {}, "constraints": {}, "plan": route_plan}
        )
    finally:
        trip_planner.call_tool = old_call_tool

    tips = "\n".join(reviewed["plan"].tips)
    assert "第 1 天 故宫 → 环球影城 通勤约 60 分钟" in tips
    assert "近处咖啡 → 博物馆 通勤约 10 分钟" not in tips
    assert len([call for call in route_calls if call[0] == "amap_route_distance"]) == 3
    assert not any(call[1].get("address") == "第五站" for call in route_calls if call[0] == "amap_geocode")

    def failing_route_tool(name, arguments):
        raise RuntimeError(name)

    stable_plan = TripPlanResponse(
        trip_id="route-failure",
        destination="北京",
        summary="demo",
        days=[
            TripDay(
                day=1,
                date="2026-10-01",
                title="demo",
                items=[
                    TripPlanItem(time="09:00", place="故宫", activity="参观"),
                    TripPlanItem(time="11:00", place="环球影城", activity="游玩"),
                ],
                notes=[],
            )
        ],
        tips=["原有提醒"],
        disclaimer="demo",
    )

    old_call_tool = trip_planner.call_tool
    trip_planner.call_tool = failing_route_tool
    try:
        reviewed = trip_planner._review_plan(
            {"request": structured, "context": {}, "constraints": {}, "plan": stable_plan}
        )
    finally:
        trip_planner.call_tool = old_call_tool

    assert reviewed["plan"].tips == ["原有提醒"]
```

- [ ] **Step 2: Run the self-check to verify it fails**

Run from `backend/`:

```bash
python3 src/app/graph/test_trip_planner.py
```

Expected: FAIL with an `AssertionError` because no route leg warning is produced yet.

- [ ] **Step 3: Add route leg constants**

In `backend/src/app/graph/trip_planner.py`, after `TripPlannerState`, insert:

```python
_ROUTE_LEG_MAX_ITEMS_PER_DAY = 4
_ROUTE_LEG_RISK_SECONDS = 45 * 60
```

- [ ] **Step 4: Call route leg review from `_review_plan`**

In `backend/src/app/graph/trip_planner.py`, inside `_review_plan`, after this existing block:

```python
    if isinstance(budget_total, int) and estimated_cost is not None and estimated_cost > budget_total * 1.15:
        warnings.append(f"可解析费用约 {estimated_cost} 元，已明显高于预算 {budget_total} 元，请压缩活动或提高预算。")
```

insert:

```python
    warnings.extend(_review_route_legs(plan))
```

- [ ] **Step 5: Add route leg helper functions**

In `backend/src/app/graph/trip_planner.py`, after `_estimate_plan_cost`, insert:

```python
def _review_route_legs(plan: TripPlanResponse) -> list[str]:
    warnings: list[str] = []
    for day in plan.days:
        items = [item for item in day.items[:_ROUTE_LEG_MAX_ITEMS_PER_DAY] if item.place.strip()]
        for origin, destination in zip(items, items[1:]):
            warning = _route_leg_warning(day.day, origin.place.strip(), destination.place.strip())
            if warning:
                warnings.append(warning)
    return warnings


def _route_leg_warning(day: int, origin_place: str, destination_place: str) -> str | None:
    try:
        origin = _first_location(call_tool("amap_geocode", {"address": origin_place}))
        destination = _first_location(call_tool("amap_geocode", {"address": destination_place}))
        if not origin or not destination:
            return None
        route = call_tool("amap_route_distance", {"origin": origin, "destination": destination})
    except Exception:
        return None

    seconds = _route_duration_seconds(route)
    if seconds is None or seconds <= _ROUTE_LEG_RISK_SECONDS:
        return None

    minutes = round(seconds / 60)
    return f"第 {day} 天 {origin_place} → {destination_place} 通勤约 {minutes} 分钟，建议拆到不同日期或删除其中一个。"


def _route_duration_seconds(data: dict[str, Any]) -> int | None:
    paths = (data.get("route") or {}).get("paths") or []
    if not paths:
        return None
    try:
        return int(float(str(paths[0].get("duration"))))
    except (TypeError, ValueError):
        return None
```

- [ ] **Step 6: Run the route leg self-check**

Run from `backend/`:

```bash
python3 src/app/graph/test_trip_planner.py
```

Expected: PASS with no output.

- [ ] **Step 7: Run backend compile check**

Run from repo root:

```bash
python -m compileall backend/src
```

Expected: PASS and output ends without syntax errors.

- [ ] **Step 8: Commit the implementation**

```bash
git add backend/src/app/graph/trip_planner.py backend/src/app/graph/test_trip_planner.py
git commit -m "feat: flag long route legs in trip plans

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

---

## Self-Review

- Spec coverage: route leg checks, first 4 activities cap, 45-minute threshold, existing `tips`, MCP failure tolerance, no frontend/database/schema change are all covered in Task 1.
- Placeholder scan: no placeholder steps remain.
- Type consistency: helper signatures and constants match the interfaces block and implementation snippets.
