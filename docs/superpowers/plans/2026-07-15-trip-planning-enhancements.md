# Trip Planning Enhancements Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 增强旅游计划生成：支持分项预算、结构化偏好，并在 LangGraph 内完成约束整理和行程审查。

**Architecture:** 保留现有 FastAPI + LangGraph + Vue 首页规划器结构。后端只扩展 `TripPlanRequest` 和 `trip_planner.py` 图节点；前端只扩展类型、表单字段和提交 payload。所有预算/偏好处理必须在 LangGraph 节点中执行，不走 API 层旁路。

**Tech Stack:** Python 3.12+、FastAPI、LangGraph、Pydantic v2、Vue 3、TypeScript、Vite、Tailwind CSS。

## Global Constraints

- 不新增依赖。
- 不接酒店、票务、交通排班等新的实时供应商 API。
- 不做精确路线优化或地图级时间矩阵。
- 不重构主页布局。
- 不新增通用 service 抽象。
- 后端所有新增工作必须嵌入现有 LangGraph 图节点中。
- 响应 schema `TripPlanResponse` 暂不新增字段；风险提醒追加到现有 `tips`。

---

## File Structure

- Modify: `backend/src/app/models/trip.py`
  - 负责请求/响应 Pydantic 模型。新增预算分项、旅行节奏、同行人枚举。
- Modify: `backend/src/app/graph/trip_planner.py`
  - 负责 LangGraph 规划链路。新增 `check_constraints` 和 `review_plan` 节点，补预算解析和轻量审查 helper。
- Modify: `front/src/types/index.ts`
  - 负责前端 API 类型。同步新增请求字段。
- Modify: `front/src/views/HomeView.vue`
  - 负责主页规划器表单和提交 payload。保留现有布局，只在表单内增加字段。

---

### Task 1: Extend trip request models

**Files:**
- Modify: `backend/src/app/models/trip.py:1-29`
- Modify: `front/src/types/index.ts:1-19`

**Interfaces:**
- Produces backend types:
  - `BudgetBreakdown(BaseModel)` with `transport`, `hotel`, `food`, `tickets`: `str`
  - `TravelPace = Literal["relaxed", "balanced", "packed"]`
  - `TravelCompanions = Literal["solo", "couple", "friends", "family", "seniors"]`
  - `TripPlanRequest.budget_breakdown: BudgetBreakdown`
  - `TripPlanRequest.pace: TravelPace`
  - `TripPlanRequest.companions: TravelCompanions`
  - `TripPlanRequest.must_see: str`
  - `TripPlanRequest.avoid: str`
- Produces frontend types:
  - `BudgetBreakdown`
  - `TravelPace`
  - `TravelCompanions`
  - matching fields on `TripPlanRequest`

- [ ] **Step 1: Run the current backend model import check**

Run:

```bash
python3 - <<'PY'
from src.app.models.trip import TripPlanRequest
request = TripPlanRequest(destination='北京', days=1)
print(request.model_dump())
PY
```

from `backend/`.

Expected: PASS and output includes existing fields only (`destination`, `origin`, `days`, `budget`, `travel_style`, `start_date`, `end_date`, `notes`).

- [ ] **Step 2: Add backend model fields**

In `backend/src/app/models/trip.py`, replace the top model/type section with:

```python
"""Trip planning request and response models."""

from datetime import datetime
from typing import Literal

from pydantic import BaseModel, Field

TravelStyle = Literal[
    "culture",
    "food",
    "nature",
    "family",
    "romantic",
    "adventure",
    "relaxed",
]

TravelPace = Literal["relaxed", "balanced", "packed"]
TravelCompanions = Literal["solo", "couple", "friends", "family", "seniors"]


class BudgetBreakdown(BaseModel):
    """Structured trip budget inputs."""

    transport: str = ""
    hotel: str = ""
    food: str = ""
    tickets: str = ""


class TripPlanRequest(BaseModel):
    """User preferences for a generated trip plan."""

    destination: str = Field(..., min_length=1)
    origin: str = ""
    days: int = Field(..., ge=1, le=10)
    budget: str = ""
    budget_breakdown: BudgetBreakdown = Field(default_factory=BudgetBreakdown)
    travel_style: list[TravelStyle] = Field(default_factory=lambda: ["relaxed"])
    pace: TravelPace = "balanced"
    companions: TravelCompanions = "friends"
    start_date: str = ""
    end_date: str = ""
    must_see: str = Field(default="", max_length=300)
    avoid: str = Field(default="", max_length=300)
    notes: str = Field(default="", max_length=500)
```

Leave `TripPlanItem`, `TripDay`, `TripPlanResponse`, `SavedTripListItem`, and `SavedTripDetail` unchanged.

- [ ] **Step 3: Verify backend defaults and validation**

Run from `backend/`:

```bash
python3 - <<'PY'
from pydantic import ValidationError
from src.app.models.trip import TripPlanRequest

request = TripPlanRequest(destination='北京', days=2)
assert request.budget_breakdown.transport == ''
assert request.budget_breakdown.hotel == ''
assert request.pace == 'balanced'
assert request.companions == 'friends'
assert request.must_see == ''
assert request.avoid == ''

request = TripPlanRequest(
    destination='京都',
    days=3,
    budget_breakdown={'transport': '1200', 'hotel': '1800', 'food': '900', 'tickets': '600'},
    pace='relaxed',
    companions='family',
    must_see='清水寺',
    avoid='环球影城',
)
assert request.budget_breakdown.model_dump() == {
    'transport': '1200',
    'hotel': '1800',
    'food': '900',
    'tickets': '600',
}
assert request.pace == 'relaxed'
assert request.companions == 'family'

try:
    TripPlanRequest(destination='北京', days=1, pace='fast')
except ValidationError:
    pass
else:
    raise AssertionError('invalid pace should fail')

print('ok')
PY
```

Expected: `ok`.

- [ ] **Step 4: Add frontend request types**

In `front/src/types/index.ts`, replace lines 1-19 with:

```ts
export type TravelStyle =
  | 'culture'
  | 'food'
  | 'nature'
  | 'family'
  | 'romantic'
  | 'adventure'
  | 'relaxed'

export type TravelPace = 'relaxed' | 'balanced' | 'packed'

export type TravelCompanions = 'solo' | 'couple' | 'friends' | 'family' | 'seniors'

export interface BudgetBreakdown {
  transport: string
  hotel: string
  food: string
  tickets: string
}

export interface TripPlanRequest {
  destination: string
  origin: string
  days: number
  budget: string
  budget_breakdown: BudgetBreakdown
  travel_style: TravelStyle[]
  pace: TravelPace
  companions: TravelCompanions
  start_date: string
  end_date: string
  must_see: string
  avoid: string
  notes: string
}
```

Leave the rest of the file unchanged.

- [ ] **Step 5: Run type build to verify existing callers now fail where payload is missing new fields**

Run from `front/`:

```bash
npm run build
```

Expected: FAIL in `HomeView.vue` or another caller because `TripPlanRequest` now requires `budget_breakdown`, `pace`, `companions`, `must_see`, and `avoid`. This failure is expected and will be fixed in Task 4.

- [ ] **Step 6: Commit model/type expansion**

```bash
git add backend/src/app/models/trip.py front/src/types/index.ts
git commit -m "feat: add structured trip request fields

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

---

### Task 2: Add LangGraph constraint node

**Files:**
- Modify: `backend/src/app/graph/trip_planner.py:16-161`

**Interfaces:**
- Consumes: `TripPlanRequest.budget_breakdown`, `pace`, `companions`, `must_see`, `avoid` from Task 1.
- Produces:
  - `TripPlannerState.constraints: dict[str, Any]`
  - `_check_constraints(state: TripPlannerState) -> TripPlannerState`
  - `_parse_budget_amount(value: str) -> int | None`
  - `_parsed_budget_breakdown(request: TripPlanRequest) -> dict[str, int]`

- [ ] **Step 1: Add a failing helper check for budget parsing**

Run from `backend/` before editing:

```bash
python3 - <<'PY'
from src.app.graph.trip_planner import _parse_budget_amount

assert _parse_budget_amount('1200') == 1200
assert _parse_budget_amount('约 500-800 元') == 800
assert _parse_budget_amount('需查询官方渠道') is None
print('ok')
PY
```

Expected: FAIL with `ImportError` because `_parse_budget_amount` does not exist.

- [ ] **Step 2: Extend graph state**

In `backend/src/app/graph/trip_planner.py`, change `TripPlannerState` to:

```python
class TripPlannerState(TypedDict, total=False):
    request: TripPlanRequest
    context: dict[str, Any]
    constraints: dict[str, Any]
    draft: dict[str, Any]
    plan: TripPlanResponse
```

- [ ] **Step 3: Wire the new node into the compiled graph**

In `_build_graph()`, replace the node and edge block with:

```python
def _build_graph():
    graph = StateGraph(TripPlannerState)
    graph.add_node("normalize_request", _normalize_request)
    graph.add_node("collect_map_context", _collect_map_context)
    graph.add_node("collect_price_context", _collect_price_context)
    graph.add_node("check_constraints", _check_constraints)
    graph.add_node("draft_plan", _draft_plan)
    graph.add_node("validate_plan", _validate_plan)
    graph.add_node("review_plan", _review_plan)
    graph.add_edge(START, "normalize_request")
    graph.add_edge("normalize_request", "collect_map_context")
    graph.add_edge("collect_map_context", "collect_price_context")
    graph.add_edge("collect_price_context", "check_constraints")
    graph.add_edge("check_constraints", "draft_plan")
    graph.add_edge("draft_plan", "validate_plan")
    graph.add_edge("validate_plan", "review_plan")
    graph.add_edge("review_plan", END)
    return graph.compile()
```

`_review_plan` is added in Task 3. To keep Task 2 importable before Task 3, add this temporary pass-through directly below `_validate_plan()`:

```python
def _review_plan(state: TripPlannerState) -> TripPlannerState:
    return state
```

Task 3 replaces this pass-through with real logic.

- [ ] **Step 4: Normalize new request fields**

In `_normalize_request()`, replace the body with:

```python
def _normalize_request(state: TripPlannerState) -> TripPlannerState:
    request = state["request"]
    request.destination = request.destination.strip()
    request.origin = request.origin.strip()
    request.budget = request.budget.strip()
    request.budget_breakdown.transport = request.budget_breakdown.transport.strip()
    request.budget_breakdown.hotel = request.budget_breakdown.hotel.strip()
    request.budget_breakdown.food = request.budget_breakdown.food.strip()
    request.budget_breakdown.tickets = request.budget_breakdown.tickets.strip()
    request.start_date = request.start_date.strip()
    request.end_date = request.end_date.strip()
    request.must_see = request.must_see.strip()
    request.avoid = request.avoid.strip()
    request.notes = request.notes.strip()
    return {"request": request}
```

- [ ] **Step 5: Add constraint helper functions and node**

Add this block after `_collect_price_context()` and before `_draft_plan()`:

```python
def _check_constraints(state: TripPlannerState) -> TripPlannerState:
    request = state["request"]
    parsed_budget = _parsed_budget_breakdown(request)
    fallback_budget = _parse_budget_amount(request.budget)
    budget_total = sum(parsed_budget.values()) if parsed_budget else fallback_budget
    constraints = {
        "budget_breakdown": request.budget_breakdown.model_dump(),
        "parsed_budget": parsed_budget,
        "budget_total": budget_total,
        "pace": request.pace,
        "pace_rule": _pace_rule(request.pace),
        "companions": request.companions,
        "companions_rule": _companions_rule(request.companions),
        "must_see": request.must_see,
        "avoid": request.avoid,
    }
    return {"request": request, "context": state["context"], "constraints": constraints}


def _parse_budget_amount(value: str) -> int | None:
    numbers = re.findall(r"\d+(?:\.\d+)?", value.replace(",", ""))
    if not numbers:
        return None
    return int(max(float(number) for number in numbers))


def _parsed_budget_breakdown(request: TripPlanRequest) -> dict[str, int]:
    values = request.budget_breakdown.model_dump()
    parsed: dict[str, int] = {}
    for key, value in values.items():
        amount = _parse_budget_amount(str(value))
        if amount is not None:
            parsed[key] = amount
    return parsed


def _pace_rule(pace: str) -> str:
    return {
        "relaxed": "每天安排 2 到 3 个活动，减少跨区移动，保留休息时间。",
        "balanced": "每天安排 3 个左右活动，兼顾效率和休息。",
        "packed": "每天安排 3 到 4 个活动，但仍避免明显时间冲突和过度跨区。",
    }.get(pace, "每天安排 3 个左右活动，兼顾效率和休息。")


def _companions_rule(companions: str) -> str:
    return {
        "solo": "增加安全、夜间交通和独自出行提醒。",
        "couple": "保留慢节奏体验和适合两人停留的安排。",
        "friends": "安排可以灵活调整、适合集体行动的路线。",
        "family": "降低步行强度，增加休息和亲子友好提醒。",
        "seniors": "降低步行强度，减少赶路，增加休息和无障碍提醒。",
    }.get(companions, "安排可以灵活调整、适合集体行动的路线。")
```

- [ ] **Step 6: Pass constraints into the LLM prompt**

In `_draft_plan()`, add:

```python
    constraints = state["constraints"]
```

immediately after `context = state["context"]`.

Then replace the system prompt content with:

```python
                    "你是中文旅行规划 Agent。必须只输出 JSON object，字段严格匹配："
                    "trip_id,destination,summary,days,tips,disclaimer。"
                    "days 每项包含 day,date,title,weather,items,daily_budget,transport,notes。"
                    "items 每项包含 time,place,activity,estimated_cost,booking_hint,source_hint。"
                    "必须按具体日期和时间点安排行程，不要使用上午/下午/晚上作为固定字段。"
                    "价格只能使用搜索上下文中的参考信息或写约/区间/需查询官方渠道，不要编造精确实时票价。"
                    "必须优先满足 must_see，不安排 avoid。"
                    "必须按 pace_rule 控制每天活动数量，并按 companions_rule 调整强度和提醒。"
                    "预算建议必须参考 budget_breakdown；不确定价格写区间或需查询官方渠道。"
```

Then replace the inline `"constraints": {...}` object in the user payload with:

```python
                        "constraints": {
                            "language": "zh-CN",
                            "days_count": request.days,
                            "date_range": [request.start_date, request.end_date],
                            "legacy_budget": request.budget,
                            **constraints,
                        },
```

- [ ] **Step 7: Update streaming status to include the new node**

In `stream_trip_with_graph()`, replace the block after `_collect_price_context(state)` with:

```python
    state.update(_collect_price_context(state))
    yield {"type": "status", "message": "正在整理预算和偏好约束..."}
    state.update(_check_constraints(state))
    yield {"type": "status", "message": "正在让大模型生成路线草案..."}
    state.update(_draft_plan(state))
    yield {"type": "status", "message": "正在校验并整理行程格式..."}
    state.update(_validate_plan(state))
    yield {"type": "status", "message": "正在检查预算和行程可执行性..."}
    state.update(_review_plan(state))
    yield {"type": "plan", "data": state["plan"].model_dump()}
    yield {"type": "done"}
```

- [ ] **Step 8: Verify budget parsing and constraint output**

Run from `backend/`:

```bash
python3 - <<'PY'
from src.app.graph.trip_planner import _check_constraints, _parse_budget_amount
from src.app.models.trip import TripPlanRequest

assert _parse_budget_amount('1200') == 1200
assert _parse_budget_amount('约 500-800 元') == 800
assert _parse_budget_amount('需查询官方渠道') is None

request = TripPlanRequest(
    destination='京都',
    days=3,
    budget='5000',
    budget_breakdown={'transport': '1200', 'hotel': '1800', 'food': '900', 'tickets': '600'},
    pace='relaxed',
    companions='family',
    must_see='清水寺',
    avoid='环球影城',
)
state = _check_constraints({'request': request, 'context': {}})
constraints = state['constraints']
assert constraints['parsed_budget'] == {'transport': 1200, 'hotel': 1800, 'food': 900, 'tickets': 600}
assert constraints['budget_total'] == 4500
assert '2 到 3 个活动' in constraints['pace_rule']
assert '降低步行强度' in constraints['companions_rule']
assert constraints['must_see'] == '清水寺'
assert constraints['avoid'] == '环球影城'
print('ok')
PY
```

Expected: `ok`.

- [ ] **Step 9: Compile backend**

Run from repo root:

```bash
python3 -m compileall backend/src
```

Expected: no compile errors.

- [ ] **Step 10: Commit constraint node**

```bash
git add backend/src/app/graph/trip_planner.py
git commit -m "feat: add trip planning constraint node

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

---

### Task 3: Add LangGraph plan review node

**Files:**
- Modify: `backend/src/app/graph/trip_planner.py:164-295`

**Interfaces:**
- Consumes:
  - `TripPlannerState.plan: TripPlanResponse`
  - `TripPlannerState.constraints: dict[str, Any]`
  - `_parse_budget_amount(value: str) -> int | None` from Task 2
- Produces:
  - `_review_plan(state: TripPlannerState) -> TripPlannerState`
  - `_split_terms(value: str) -> list[str]`
  - `_plan_text(plan: TripPlanResponse) -> str`
  - `_estimate_plan_cost(plan: TripPlanResponse) -> int | None`

- [ ] **Step 1: Add a failing review check**

Run from `backend/` before implementing the real review node:

```bash
python3 - <<'PY'
from src.app.graph.trip_planner import _review_plan
from src.app.models.trip import TripDay, TripPlanItem, TripPlanRequest, TripPlanResponse

request = TripPlanRequest(destination='京都', days=1, pace='relaxed', must_see='清水寺', avoid='环球影城')
plan = TripPlanResponse(
    trip_id='demo',
    destination='京都',
    summary='demo',
    days=[TripDay(
        day=1,
        date='2026-10-01',
        title='demo',
        items=[
            TripPlanItem(time='09:00', place='环球影城', activity='游玩', estimated_cost='300'),
            TripPlanItem(time='09:00', place='咖啡店', activity='早餐', estimated_cost='80'),
            TripPlanItem(time='11:00', place='博物馆', activity='参观', estimated_cost='80'),
            TripPlanItem(time='14:00', place='商店街', activity='购物', estimated_cost='200'),
        ],
        notes=[],
    )],
    tips=[],
    disclaimer='demo',
)
state = _review_plan({'request': request, 'context': {}, 'constraints': {'budget_total': 500, 'must_see': '清水寺', 'avoid': '环球影城'}, 'plan': plan})
tips = '\n'.join(state['plan'].tips)
assert '慢游节奏' in tips
assert '重复时间' in tips
assert '必去地点' in tips
assert '避开地点' in tips
print('ok')
PY
```

Expected: FAIL because Task 2 temporary `_review_plan()` is a pass-through.

- [ ] **Step 2: Replace pass-through `_review_plan` with real logic**

In `backend/src/app/graph/trip_planner.py`, replace the temporary `_review_plan()` with:

```python
def _review_plan(state: TripPlannerState) -> TripPlannerState:
    request = state["request"]
    plan = state["plan"]
    constraints = state.get("constraints", {})
    warnings: list[str] = []

    max_items = {"relaxed": 3, "balanced": 3, "packed": 4}.get(request.pace, 3)
    pace_label = {"relaxed": "慢游", "balanced": "适中", "packed": "紧凑"}.get(request.pace, "适中")
    for day in plan.days:
        if len(day.items) > max_items:
            warnings.append(f"第 {day.day} 天活动数量较多，可能不符合{pace_label}节奏。")
        times = [item.time.strip() for item in day.items if item.time.strip()]
        duplicate_times = sorted({time for time in times if times.count(time) > 1})
        if duplicate_times:
            warnings.append(f"第 {day.day} 天存在重复时间：{'、'.join(duplicate_times)}，出发前请调整顺序。")

    text = _plan_text(plan)
    missing_must_see = [term for term in _split_terms(str(constraints.get("must_see") or "")) if term not in text]
    if missing_must_see:
        warnings.append(f"必去地点未出现在路线中：{'、'.join(missing_must_see)}。")

    avoided = [term for term in _split_terms(str(constraints.get("avoid") or "")) if term in text]
    if avoided:
        warnings.append(f"路线中包含避开地点：{'、'.join(avoided)}，请确认是否替换。")

    budget_total = constraints.get("budget_total")
    estimated_cost = _estimate_plan_cost(plan)
    if isinstance(budget_total, int) and estimated_cost is not None and estimated_cost > budget_total * 1.15:
        warnings.append(f"可解析费用约 {estimated_cost} 元，已明显高于预算 {budget_total} 元，请压缩活动或提高预算。")

    for warning in warnings:
        if warning not in plan.tips:
            plan.tips.append(warning)

    return {"request": request, "context": state.get("context", {}), "constraints": constraints, "plan": plan}
```

- [ ] **Step 3: Add review helper functions**

Add these helper functions before `_slugify()`:

```python
def _split_terms(value: str) -> list[str]:
    return [term.strip() for term in re.split(r"[,，、;；\n]+", value) if term.strip()]


def _plan_text(plan: TripPlanResponse) -> str:
    parts = [plan.destination, plan.summary, " ".join(plan.tips), plan.disclaimer]
    for day in plan.days:
        parts.extend([day.title, day.weather, day.daily_budget, day.transport, " ".join(day.notes)])
        for item in day.items:
            parts.extend([item.time, item.place, item.activity, item.estimated_cost, item.booking_hint, item.source_hint])
    return "\n".join(parts)


def _estimate_plan_cost(plan: TripPlanResponse) -> int | None:
    total = 0
    found = False
    for day in plan.days:
        for item in day.items:
            amount = _parse_budget_amount(item.estimated_cost)
            if amount is None:
                continue
            found = True
            total += amount
    return total if found else None
```

- [ ] **Step 4: Verify review warnings**

Run from `backend/`:

```bash
python3 - <<'PY'
from src.app.graph.trip_planner import _review_plan
from src.app.models.trip import TripDay, TripPlanItem, TripPlanRequest, TripPlanResponse

request = TripPlanRequest(destination='京都', days=1, pace='relaxed', must_see='清水寺', avoid='环球影城')
plan = TripPlanResponse(
    trip_id='demo',
    destination='京都',
    summary='demo',
    days=[TripDay(
        day=1,
        date='2026-10-01',
        title='demo',
        items=[
            TripPlanItem(time='09:00', place='环球影城', activity='游玩', estimated_cost='300'),
            TripPlanItem(time='09:00', place='咖啡店', activity='早餐', estimated_cost='80'),
            TripPlanItem(time='11:00', place='博物馆', activity='参观', estimated_cost='80'),
            TripPlanItem(time='14:00', place='商店街', activity='购物', estimated_cost='200'),
        ],
        notes=[],
    )],
    tips=[],
    disclaimer='demo',
)
state = _review_plan({'request': request, 'context': {}, 'constraints': {'budget_total': 500, 'must_see': '清水寺', 'avoid': '环球影城'}, 'plan': plan})
tips = '\n'.join(state['plan'].tips)
assert '慢游节奏' in tips
assert '重复时间' in tips
assert '必去地点' in tips
assert '避开地点' in tips
assert '明显高于预算' in tips
print('ok')
PY
```

Expected: `ok`.

- [ ] **Step 5: Verify review does not block clean plans**

Run from `backend/`:

```bash
python3 - <<'PY'
from src.app.graph.trip_planner import _review_plan
from src.app.models.trip import TripDay, TripPlanItem, TripPlanRequest, TripPlanResponse

request = TripPlanRequest(destination='京都', days=1, pace='balanced', must_see='清水寺', avoid='环球影城')
plan = TripPlanResponse(
    trip_id='demo',
    destination='京都',
    summary='包含清水寺',
    days=[TripDay(
        day=1,
        date='2026-10-01',
        title='清水寺慢游',
        items=[
            TripPlanItem(time='09:00', place='清水寺', activity='参观', estimated_cost='80'),
            TripPlanItem(time='12:00', place='附近餐厅', activity='午餐', estimated_cost='120'),
            TripPlanItem(time='15:00', place='二年坂', activity='散步', estimated_cost='0'),
        ],
        notes=[],
    )],
    tips=['出发前核实开放时间。'],
    disclaimer='demo',
)
state = _review_plan({'request': request, 'context': {}, 'constraints': {'budget_total': 1000, 'must_see': '清水寺', 'avoid': '环球影城'}, 'plan': plan})
assert state['plan'].tips == ['出发前核实开放时间。']
print('ok')
PY
```

Expected: `ok`.

- [ ] **Step 6: Compile backend**

Run from repo root:

```bash
python3 -m compileall backend/src
```

Expected: no compile errors.

- [ ] **Step 7: Commit review node**

```bash
git add backend/src/app/graph/trip_planner.py
git commit -m "feat: review trip plan constraints in graph

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

---

### Task 4: Add frontend budget and preference inputs

**Files:**
- Modify: `front/src/views/HomeView.vue:1-418`

**Interfaces:**
- Consumes frontend types from Task 1:
  - `TravelPace`
  - `TravelCompanions`
- Produces submit payload with:
  - `budget_breakdown`
  - `pace`
  - `companions`
  - `must_see`
  - `avoid`

- [ ] **Step 1: Confirm current build failure from Task 1**

Run from `front/`:

```bash
npm run build
```

Expected: FAIL because `HomeView.vue` payload lacks new required `TripPlanRequest` fields.

- [ ] **Step 2: Import new types**

In `front/src/views/HomeView.vue`, change the type import to:

```ts
import type { TravelCompanions, TravelPace, TravelStyle, TripPlanResponse } from '@/types'
```

- [ ] **Step 3: Add pace and companions options**

After `styleOptions`, add:

```ts
const paceOptions: Array<{ label: string; value: TravelPace }> = [
  { label: '慢游', value: 'relaxed' },
  { label: '适中', value: 'balanced' },
  { label: '紧凑', value: 'packed' },
]

const companionOptions: Array<{ label: string; value: TravelCompanions }> = [
  { label: '独自', value: 'solo' },
  { label: '情侣', value: 'couple' },
  { label: '朋友', value: 'friends' },
  { label: '家庭', value: 'family' },
  { label: '老人', value: 'seniors' },
]
```

- [ ] **Step 4: Extend reactive form state**

Replace the `form = reactive({ ... })` block with:

```ts
const form = reactive({
  destination: '北京',
  origin: '上海',
  days: 1,
  budget_breakdown: {
    transport: '1200',
    hotel: '1800',
    food: '1000',
    tickets: '700',
  },
  travel_style: ['culture'] as TravelStyle[],
  pace: 'balanced' as TravelPace,
  companions: 'friends' as TravelCompanions,
  start_date: todayIso(),
  end_date: todayIso(),
  must_see: '',
  avoid: '',
  notes: '喜欢慢节奏的早晨和本地美食。',
})
```

- [ ] **Step 5: Add legacy budget helper**

Add this function before `createPlan()`:

```ts
function totalBudgetText(): string {
  const total = Object.values(form.budget_breakdown).reduce((sum, value) => sum + (Number(value) || 0), 0)
  return total > 0 ? String(total) : ''
}
```

- [ ] **Step 6: Include new fields in submit payload**

In `createPlan()`, replace the `payload` object with:

```ts
    const payload = {
      destination: form.destination.trim(),
      origin: form.origin.trim(),
      days: form.days,
      budget: totalBudgetText(),
      budget_breakdown: {
        transport: form.budget_breakdown.transport.trim(),
        hotel: form.budget_breakdown.hotel.trim(),
        food: form.budget_breakdown.food.trim(),
        tickets: form.budget_breakdown.tickets.trim(),
      },
      travel_style: form.travel_style,
      pace: form.pace,
      companions: form.companions,
      start_date: form.start_date,
      end_date: form.end_date,
      must_see: form.must_see.trim(),
      avoid: form.avoid.trim(),
      notes: form.notes.trim(),
    }
```

- [ ] **Step 7: Replace single budget input with four budget inputs**

In the template, replace the current budget `<label>` block at the start of the two-column budget/style grid with:

```vue
                <div class="block">
                  <span class="text-sm font-medium">分项预算</span>
                  <div class="mt-1.5 grid gap-2 sm:grid-cols-2">
                    <label class="block">
                      <span class="sr-only">交通预算</span>
                      <input v-model="form.budget_breakdown.transport" inputmode="numeric" class="h-10 w-full rounded-md border border-[#c8c4be] bg-white px-3 text-base outline-none focus:border-[#5645d4] focus:ring-2 focus:ring-[#d6b6f6]" placeholder="交通" />
                    </label>
                    <label class="block">
                      <span class="sr-only">住宿预算</span>
                      <input v-model="form.budget_breakdown.hotel" inputmode="numeric" class="h-10 w-full rounded-md border border-[#c8c4be] bg-white px-3 text-base outline-none focus:border-[#5645d4] focus:ring-2 focus:ring-[#d6b6f6]" placeholder="住宿" />
                    </label>
                    <label class="block">
                      <span class="sr-only">餐饮预算</span>
                      <input v-model="form.budget_breakdown.food" inputmode="numeric" class="h-10 w-full rounded-md border border-[#c8c4be] bg-white px-3 text-base outline-none focus:border-[#5645d4] focus:ring-2 focus:ring-[#d6b6f6]" placeholder="餐饮" />
                    </label>
                    <label class="block">
                      <span class="sr-only">门票预算</span>
                      <input v-model="form.budget_breakdown.tickets" inputmode="numeric" class="h-10 w-full rounded-md border border-[#c8c4be] bg-white px-3 text-base outline-none focus:border-[#5645d4] focus:ring-2 focus:ring-[#d6b6f6]" placeholder="门票" />
                    </label>
                  </div>
                </div>
```

Keep the adjacent travel style `<div class="block">` unchanged.

- [ ] **Step 8: Add pace and companions controls after travel style/date block**

Insert this block after the travel style grid and before the travel date block:

```vue
              <div class="grid gap-3 sm:grid-cols-2">
                <label class="block">
                  <span class="text-sm font-medium">旅行节奏</span>
                  <select v-model="form.pace" class="mt-1.5 h-10 w-full rounded-md border border-[#c8c4be] bg-white px-3 text-base outline-none focus:border-[#5645d4] focus:ring-2 focus:ring-[#d6b6f6]">
                    <option v-for="option in paceOptions" :key="option.value" :value="option.value">
                      {{ option.label }}
                    </option>
                  </select>
                </label>

                <label class="block">
                  <span class="text-sm font-medium">同行人</span>
                  <select v-model="form.companions" class="mt-1.5 h-10 w-full rounded-md border border-[#c8c4be] bg-white px-3 text-base outline-none focus:border-[#5645d4] focus:ring-2 focus:ring-[#d6b6f6]">
                    <option v-for="option in companionOptions" :key="option.value" :value="option.value">
                      {{ option.label }}
                    </option>
                  </select>
                </label>
              </div>
```

- [ ] **Step 9: Add must-see and avoid inputs before notes**

Insert this block before the existing `补充偏好` textarea:

```vue
              <div class="grid gap-3 sm:grid-cols-2">
                <label class="block">
                  <span class="text-sm font-medium">必去地点</span>
                  <input v-model="form.must_see" class="mt-1.5 h-10 w-full rounded-md border border-[#c8c4be] bg-white px-3 text-base outline-none focus:border-[#5645d4] focus:ring-2 focus:ring-[#d6b6f6]" placeholder="故宫、清水寺" />
                </label>

                <label class="block">
                  <span class="text-sm font-medium">避开地点</span>
                  <input v-model="form.avoid" class="mt-1.5 h-10 w-full rounded-md border border-[#c8c4be] bg-white px-3 text-base outline-none focus:border-[#5645d4] focus:ring-2 focus:ring-[#d6b6f6]" placeholder="排队过久、商业街" />
                </label>
              </div>
```

- [ ] **Step 10: Build frontend**

Run from `front/`:

```bash
npm run build
```

Expected: PASS.

- [ ] **Step 11: Commit frontend fields**

```bash
git add front/src/types/index.ts front/src/views/HomeView.vue
git commit -m "feat: add structured trip preferences form

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```

---

### Task 5: End-to-end verification

**Files:**
- No new source files.
- Verify changed files from Tasks 1-4.

**Interfaces:**
- Consumes final frontend payload and backend `/api/trips/plan/stream` behavior.
- Produces confidence that:
  - backend compiles,
  - frontend builds,
  - homepage form renders,
  - stream includes constraint/review statuses,
  - payload includes new fields.

- [ ] **Step 1: Compile backend**

Run from repo root:

```bash
python3 -m compileall backend/src
```

Expected: no compile errors.

- [ ] **Step 2: Build frontend**

Run from `front/`:

```bash
npm run build
```

Expected: PASS.

- [ ] **Step 3: Restart backend and frontend**

Stop existing ports and start services:

```bash
for port in 8000 5173; do pids=$(lsof -ti tcp:$port 2>/dev/null); if [ -n "$pids" ]; then kill $pids; fi; done
```

Start backend from repo root:

```bash
cd backend && /Users/alh/.local/bin/uv run uvicorn src.app.main:app --reload
```

Start frontend in a second shell from repo root:

```bash
cd front && npm run dev -- --host 127.0.0.1
```

Expected:

- backend logs include `Uvicorn running on http://127.0.0.1:8000`
- frontend logs include `Local: http://127.0.0.1:5173/`

- [ ] **Step 4: Health-check services**

Run:

```bash
curl -s http://127.0.0.1:8000/api/health
curl -s -o /dev/null -w '%{http_code}\n' http://127.0.0.1:5173/
```

Expected:

```json
{"status":"ok"}
```

and:

```text
200
```

- [ ] **Step 5: Browser-check homepage form fields**

Open `http://127.0.0.1:5173/home` in the browser with a logged-in session or temporarily navigate after login.

Expected visible fields in the planner form:

- 分项预算 with inputs for 交通、住宿、餐饮、门票
- 旅行节奏 select
- 同行人 select
- 必去地点 input
- 避开地点 input
- existing 补充偏好 textarea

- [ ] **Step 6: Browser-check request payload**

In the browser devtools network panel, click `生成路线草案`.

Expected request body for `/api/trips/plan/stream` contains:

```json
{
  "budget_breakdown": {
    "transport": "1200",
    "hotel": "1800",
    "food": "1000",
    "tickets": "700"
  },
  "pace": "balanced",
  "companions": "friends",
  "must_see": "",
  "avoid": ""
}
```

Authentication or LLM errors are acceptable for this step if the request payload is correct.

- [ ] **Step 7: Backend stream status smoke with monkeypatched internals**

Run from `backend/` to exercise the streaming order without real MCP/LLM calls:

```bash
python3 - <<'PY'
from src.app.graph import trip_planner
from src.app.models.trip import TripDay, TripPlanItem, TripPlanRequest, TripPlanResponse

trip_planner._collect_map_context = lambda state: {**state, 'context': {'pois': [], 'weather': None, 'routes': []}}
trip_planner._collect_price_context = lambda state: {**state, 'context': {**state['context'], 'prices': []}}
trip_planner._draft_plan = lambda state: {**state, 'draft': TripPlanResponse(
    trip_id='demo',
    destination=state['request'].destination,
    summary='demo',
    days=[TripDay(day=1, date='2026-10-01', title='demo', items=[TripPlanItem(time='09:00', place='清水寺', activity='参观', estimated_cost='80')], notes=[])],
    tips=[],
    disclaimer='demo',
).model_dump()}

request = TripPlanRequest(
    destination='京都',
    days=1,
    budget_breakdown={'transport': '1200', 'hotel': '1800', 'food': '1000', 'tickets': '700'},
    pace='balanced',
    companions='friends',
    must_see='清水寺',
)
events = list(trip_planner.stream_trip_with_graph(request))
messages = [event.get('message') for event in events if event.get('type') == 'status']
assert '正在整理预算和偏好约束...' in messages
assert '正在检查预算和行程可执行性...' in messages
assert events[-2]['type'] == 'plan'
assert events[-1]['type'] == 'done'
print('ok')
PY
```

Expected: `ok`.

- [ ] **Step 8: Final diff review**

Run:

```bash
git diff --stat
git status --short
```

Expected:

- diff only includes the planned files and commits from Tasks 1-4,
- working tree has no unintended source changes.

- [ ] **Step 9: Commit any verification-only documentation if added**

If no files were changed during verification, do not commit.

If a small verification note was added intentionally, commit it with:

```bash
git add <changed-doc-file>
git commit -m "docs: record trip planning verification

Co-Authored-By: Claude Opus 4.8 (1M context) <noreply@anthropic.com>"
```
