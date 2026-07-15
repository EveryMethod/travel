# 用户个人工作台 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 登录用户生成行程后自动保存，并能在独立工作台查看、复制、重新生成、删除自己的行程。

**Architecture:** 后端新增一张 `trips` 表，用 JSON 保存原始请求和生成结果；trip API 全部依赖当前登录用户。前端保留 `/home` 作为生成入口，新增 `/workspace` 列表页和 `/trips/:id` 详情页，复制 Markdown 在浏览器端完成。

**Tech Stack:** FastAPI, SQLAlchemy, Alembic, Redis-backed auth sessions, Vue 3, Vue Router, TypeScript, Tailwind CSS.

## Global Constraints

- MVP 只支持登录用户；不做匿名行程。
- 只新增一张 `trips` 表；不拆 `trip_days` / `trip_items`。
- 生成成功后自动保存；生成失败不保存。
- 重新生成创建新行程，不覆盖旧行程。
- 不做分享链接、PDF 导出、标题/备注编辑、局部编辑每天行程、复杂个人设置。
- 不新增依赖。
- 用户要求：本计划阶段不提交 git commit。

---

## File Structure

### Backend

- Modify: `backend/src/app/api/auth.py`
  - Add `require_current_user()` dependency that reads Bearer token from Redis session.
- Modify: `backend/src/app/models/db.py`
  - Add SQLAlchemy `Trip` model and `User.trips` relationship.
- Create: `backend/alembic/versions/20260715_0003_create_trips.py`
  - Create/drop `trips` table and indexes.
- Modify: `backend/src/app/models/trip.py`
  - Add saved-trip response models.
- Create: `backend/src/app/services/trip_store.py`
  - Encapsulate create/list/get/delete trip persistence.
- Modify: `backend/src/app/api/router.py`
  - Protect trip planning endpoints and add list/detail/delete endpoints.
- Create: `backend/src/app/services/test_trip_store.py`
  - Add assert-based self-check for ownership filtering and not-found behavior.

### Frontend

- Modify: `front/src/types/index.ts`
  - Add saved-trip list/detail types and stream event type.
- Modify: `front/src/services/index.ts`
  - Add auth header to streaming request and add trip list/detail/delete functions.
- Create: `front/src/services/tripMarkdown.ts`
  - Convert `TripPlanResponse` to Markdown.
- Create: `front/src/components/TripPlanResult.vue`
  - Reusable plan renderer for `/home` and `/trips/:id`.
- Create: `front/src/components/TripList.vue`
  - Workspace list component.
- Create: `front/src/views/WorkspaceView.vue`
  - Independent personal workspace page.
- Create: `front/src/views/TripDetailView.vue`
  - Saved trip detail page.
- Modify: `front/src/views/HomeView.vue`
  - Show saved-to-workspace actions after generation.
- Modify: `front/src/router/index.ts`
  - Add `/workspace` and `/trips/:id`, protect them with auth guard.

---

### Task 1: Backend auth dependency and trip persistence model

**Files:**
- Modify: `backend/src/app/api/auth.py`
- Modify: `backend/src/app/models/db.py`
- Create: `backend/alembic/versions/20260715_0003_create_trips.py`

**Interfaces:**
- Consumes: existing `auth:access:{token}` Redis keys from `auth_service.py`.
- Produces: `require_current_user(...) -> User`, `Trip` ORM model.

- [ ] **Step 1: Add current-user dependency**

In `backend/src/app/api/auth.py`, extend imports:

```python
from datetime import datetime

from fastapi import APIRouter, Depends, HTTPException, Request, status
from fastapi.security import HTTPAuthorizationCredentials, HTTPBearer
```

Add after `get_redis()`:

```python
auth_scheme = HTTPBearer(auto_error=False)


def require_current_user(
    credentials: HTTPAuthorizationCredentials | None = Depends(auth_scheme),
    db: Session = Depends(get_db),
    redis: Redis = Depends(get_redis),
) -> User:
    if not credentials or credentials.scheme.lower() != "bearer":
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="登录状态已失效，请重新登录。")

    session_id = redis.get(f"auth:access:{credentials.credentials}")
    if not session_id:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="登录状态已失效，请重新登录。")

    session = db.get(AuthSession, int(session_id))
    if not session or session.revoked_at or session.expires_at <= datetime.utcnow():
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="登录状态已失效，请重新登录。")

    if session.user.status != "active":
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="用户已被禁用。")

    return session.user
```

Also extend the existing import from `src.app.models.db`:

```python
from src.app.models.db import AuthSession, User
```

- [ ] **Step 2: Add Trip ORM model**

In `backend/src/app/models/db.py`, add `TripStatus` near existing literal types:

```python
TripStatus = Literal["completed"]
```

Add relationship to `User`:

```python
    trips: Mapped[list["Trip"]] = relationship(back_populates="user")
```

Add this class after `CallTrace`:

```python
class Trip(Base):
    __tablename__ = "trips"

    id: Mapped[int] = mapped_column(BIGINT(unsigned=True), primary_key=True, autoincrement=True, comment="行程ID")
    user_id: Mapped[int] = mapped_column(BIGINT(unsigned=True), ForeignKey("users.id"), nullable=False, comment="关联用户ID")
    trace_id: Mapped[str | None] = mapped_column(String(36), nullable=True, comment="生成链路ID")
    destination: Mapped[str] = mapped_column(String(120), nullable=False, comment="目的地")
    days: Mapped[int] = mapped_column(Integer, nullable=False, comment="行程天数")
    status: Mapped[str] = mapped_column(Enum("completed"), default="completed", server_default="completed", nullable=False, comment="行程状态")
    request_json: Mapped[dict] = mapped_column(JSON, nullable=False, comment="原始规划请求")
    plan_json: Mapped[dict] = mapped_column(JSON, nullable=False, comment="生成行程结果")
    created_at: Mapped[datetime] = mapped_column(DateTime, server_default=func.current_timestamp(), comment="创建时间")
    updated_at: Mapped[datetime] = mapped_column(
        DateTime,
        server_default=func.current_timestamp(),
        server_onupdate=func.current_timestamp(),
        onupdate=func.current_timestamp(),
        comment="更新时间",
    )

    user: Mapped[User] = relationship(back_populates="trips")

    __table_args__ = (
        Index("idx_trips_user_created_at", "user_id", "created_at"),
        Index("idx_trips_trace_id", "trace_id"),
        {"comment": "用户保存的旅行行程表"},
    )
```

- [ ] **Step 3: Add migration**

Create `backend/alembic/versions/20260715_0003_create_trips.py`:

```python
"""create trips table."""

from collections.abc import Sequence

from alembic import op
import sqlalchemy as sa
from sqlalchemy.dialects import mysql

revision: str = "20260715_0003"
down_revision: str | None = "20260715_0002"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    op.create_table(
        "trips",
        sa.Column("id", mysql.BIGINT(unsigned=True), autoincrement=True, nullable=False, comment="行程ID"),
        sa.Column("user_id", mysql.BIGINT(unsigned=True), nullable=False, comment="关联用户ID"),
        sa.Column("trace_id", sa.String(length=36), nullable=True, comment="生成链路ID"),
        sa.Column("destination", sa.String(length=120), nullable=False, comment="目的地"),
        sa.Column("days", sa.Integer(), nullable=False, comment="行程天数"),
        sa.Column("status", sa.Enum("completed"), server_default="completed", nullable=False, comment="行程状态"),
        sa.Column("request_json", mysql.JSON(), nullable=False, comment="原始规划请求"),
        sa.Column("plan_json", mysql.JSON(), nullable=False, comment="生成行程结果"),
        sa.Column("created_at", sa.DateTime(), server_default=sa.text("CURRENT_TIMESTAMP"), nullable=False, comment="创建时间"),
        sa.Column("updated_at", sa.DateTime(), server_default=sa.text("CURRENT_TIMESTAMP ON UPDATE CURRENT_TIMESTAMP"), nullable=False, comment="更新时间"),
        sa.ForeignKeyConstraint(["user_id"], ["users.id"]),
        sa.PrimaryKeyConstraint("id"),
        comment="用户保存的旅行行程表",
    )
    op.create_index("idx_trips_user_created_at", "trips", ["user_id", "created_at"])
    op.create_index("idx_trips_trace_id", "trips", ["trace_id"])


def downgrade() -> None:
    op.drop_index("idx_trips_trace_id", table_name="trips")
    op.drop_index("idx_trips_user_created_at", table_name="trips")
    op.drop_table("trips")
```

- [ ] **Step 4: Run backend syntax check**

Run:

```bash
python -m compileall backend/src
```

Expected: command exits 0 and prints compiled files or no errors.

---

### Task 2: Backend trip service and API endpoints

**Files:**
- Modify: `backend/src/app/models/trip.py`
- Create: `backend/src/app/services/trip_store.py`
- Modify: `backend/src/app/api/router.py`
- Create: `backend/src/app/services/test_trip_store.py`

**Interfaces:**
- Consumes: `Trip` ORM model, `TripPlanRequest`, `TripPlanResponse`, `require_current_user()`.
- Produces: `create_completed_trip()`, `list_user_trips()`, `get_user_trip_or_404()`, `delete_user_trip()`.

- [ ] **Step 1: Add saved-trip response models**

In `backend/src/app/models/trip.py`, extend imports:

```python
from datetime import datetime
```

Add after `TripPlanResponse`:

```python
class SavedTripListItem(BaseModel):
    id: int
    destination: str
    days: int
    status: Literal["completed"]
    created_at: datetime


class SavedTripDetail(SavedTripListItem):
    trace_id: str | None
    request_json: TripPlanRequest
    plan_json: TripPlanResponse
    updated_at: datetime
```

- [ ] **Step 2: Add trip_store service**

Create `backend/src/app/services/trip_store.py`:

```python
"""Persistence helpers for saved trips."""

from fastapi import HTTPException, status
from sqlalchemy import select
from sqlalchemy.orm import Session

from src.app.models.db import Trip
from src.app.models.trip import SavedTripDetail, SavedTripListItem, TripPlanRequest, TripPlanResponse


def create_completed_trip(
    *,
    db: Session,
    user_id: int,
    trace_id: str | None,
    request: TripPlanRequest,
    plan: TripPlanResponse,
) -> TripPlanResponse:
    trip = Trip(
        user_id=user_id,
        trace_id=trace_id,
        destination=request.destination,
        days=request.days,
        status="completed",
        request_json=request.model_dump(),
        plan_json={},
    )
    db.add(trip)
    db.flush()

    plan.trip_id = str(trip.id)
    plan.destination = plan.destination or request.destination
    trip.plan_json = plan.model_dump()
    db.commit()
    return plan


def list_user_trips(*, db: Session, user_id: int) -> list[SavedTripListItem]:
    trips = db.scalars(
        select(Trip)
        .where(Trip.user_id == user_id)
        .order_by(Trip.created_at.desc(), Trip.id.desc())
    ).all()
    return [
        SavedTripListItem(
            id=trip.id,
            destination=trip.destination,
            days=trip.days,
            status="completed",
            created_at=trip.created_at,
        )
        for trip in trips
    ]


def get_user_trip_or_404(*, db: Session, user_id: int, trip_id: int) -> Trip:
    trip = db.get(Trip, trip_id)
    if not trip or trip.user_id != user_id:
        raise HTTPException(status_code=status.HTTP_404_NOT_FOUND, detail="行程不存在。")
    return trip


def get_user_trip_detail(*, db: Session, user_id: int, trip_id: int) -> SavedTripDetail:
    trip = get_user_trip_or_404(db=db, user_id=user_id, trip_id=trip_id)
    return SavedTripDetail(
        id=trip.id,
        destination=trip.destination,
        days=trip.days,
        status="completed",
        created_at=trip.created_at,
        updated_at=trip.updated_at,
        trace_id=trip.trace_id,
        request_json=TripPlanRequest.model_validate(trip.request_json),
        plan_json=TripPlanResponse.model_validate(trip.plan_json),
    )


def delete_user_trip(*, db: Session, user_id: int, trip_id: int) -> None:
    trip = get_user_trip_or_404(db=db, user_id=user_id, trip_id=trip_id)
    db.delete(trip)
    db.commit()
```

- [ ] **Step 3: Protect and save plan endpoints**

In `backend/src/app/api/router.py`, update imports:

```python
from fastapi import APIRouter, Depends, HTTPException, Request, Response
from sqlalchemy.orm import Session

from src.app.api.auth import require_current_user
from src.app.core.database import get_db
from src.app.models.db import User
from src.app.models.trip import SavedTripDetail, SavedTripListItem, TripPlanRequest, TripPlanResponse
from src.app.services.trip_store import create_completed_trip, delete_user_trip, get_user_trip_detail, list_user_trips
```

Change `plan_trip` signature and body:

```python
@api_router.post("/trips/plan", response_model=TripPlanResponse)
def plan_trip(
    request: TripPlanRequest,
    http_request: Request,
    response: Response,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_current_user),
) -> TripPlanResponse:
    """Generate and save a trip plan through the LangGraph agent."""

    with trace_context(http_request.headers.get("X-Trace-Id")) as trace_id:
        response.headers["X-Trace-Id"] = trace_id
        try:
            plan = plan_trip_with_graph(request)
            return create_completed_trip(db=db, user_id=current_user.id, trace_id=trace_id, request=request, plan=plan)
        except LLMTimeoutError as exc:
            raise HTTPException(status_code=504, detail="大模型响应超时，请稍后再试。") from exc
        except Exception as exc:
            raise HTTPException(
                status_code=500,
                detail="Unable to create a plan for the supplied request.",
            ) from exc
```

Change `stream_plan_trip` signature and save the final plan event:

```python
@api_router.post("/trips/plan/stream")
def stream_plan_trip(
    request: TripPlanRequest,
    http_request: Request,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_current_user),
) -> StreamingResponse:
    """Stream trip planning progress and save the final plan as NDJSON."""

    trace_id = http_request.headers.get("X-Trace-Id") or str(uuid4())

    def events() -> Iterator[str]:
        with trace_context(trace_id) as active_trace_id:
            yield json.dumps({"type": "trace", "trace_id": active_trace_id}, ensure_ascii=False) + "\n"
            try:
                for event in stream_trip_with_graph(request):
                    if event.get("type") == "plan":
                        plan = TripPlanResponse.model_validate(event["data"])
                        saved_plan = create_completed_trip(
                            db=db,
                            user_id=current_user.id,
                            trace_id=active_trace_id,
                            request=request,
                            plan=plan,
                        )
                        yield json.dumps({"type": "plan", "data": saved_plan.model_dump()}, ensure_ascii=False) + "\n"
                        continue
                    yield json.dumps(event, ensure_ascii=False) + "\n"
            except LLMTimeoutError:
                yield json.dumps({"type": "error", "message": "大模型响应超时，请稍后再试。"}, ensure_ascii=False) + "\n"
            except Exception:
                yield json.dumps({"type": "error", "message": "规划器暂时无法生成行程。"}, ensure_ascii=False) + "\n"

    return StreamingResponse(events(), media_type="application/x-ndjson", headers={"X-Trace-Id": trace_id})
```

- [ ] **Step 4: Add list/detail/delete routes**

In `backend/src/app/api/router.py`, add after stream route:

```python
@api_router.get("/trips", response_model=list[SavedTripListItem])
def list_trips(
    db: Session = Depends(get_db),
    current_user: User = Depends(require_current_user),
) -> list[SavedTripListItem]:
    return list_user_trips(db=db, user_id=current_user.id)


@api_router.get("/trips/{trip_id}", response_model=SavedTripDetail)
def get_trip(
    trip_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_current_user),
) -> SavedTripDetail:
    return get_user_trip_detail(db=db, user_id=current_user.id, trip_id=trip_id)


@api_router.delete("/trips/{trip_id}", status_code=204)
def delete_trip(
    trip_id: int,
    db: Session = Depends(get_db),
    current_user: User = Depends(require_current_user),
) -> Response:
    delete_user_trip(db=db, user_id=current_user.id, trip_id=trip_id)
    return Response(status_code=204)
```

- [ ] **Step 5: Add self-check for trip_store**

Create `backend/src/app/services/test_trip_store.py`:

```python
"""Self-checks for saved trip persistence helpers."""

from datetime import datetime
from types import SimpleNamespace

from fastapi import HTTPException

from src.app.models.trip import TripPlanRequest, TripPlanResponse
from src.app.services.trip_store import get_user_trip_or_404


def demo() -> None:
    class FakeDb:
        def __init__(self):
            self.trip = SimpleNamespace(id=7, user_id=42, created_at=datetime.utcnow())

        def get(self, model, trip_id):
            if trip_id == 7:
                return self.trip
            return None

    db = FakeDb()
    assert get_user_trip_or_404(db=db, user_id=42, trip_id=7).id == 7

    try:
        get_user_trip_or_404(db=db, user_id=99, trip_id=7)
    except HTTPException as exc:
        assert exc.status_code == 404
    else:
        raise AssertionError("cross-user trip access must return 404")

    try:
        get_user_trip_or_404(db=db, user_id=42, trip_id=8)
    except HTTPException as exc:
        assert exc.status_code == 404
    else:
        raise AssertionError("missing trip must return 404")

    request = TripPlanRequest(destination="北京", origin="上海", days=1, travel_style=["culture"])
    plan = TripPlanResponse(
        trip_id="draft",
        destination="北京",
        summary="一天北京行程。",
        days=[],
        tips=[],
        disclaimer="请以实际信息为准。",
    )
    assert request.destination == plan.destination


if __name__ == "__main__":
    demo()
```

- [ ] **Step 6: Run backend checks**

Run:

```bash
python backend/src/app/services/test_trip_store.py
python -m compileall backend/src
```

Expected: both commands exit 0.

---

### Task 3: Frontend types, API client, and Markdown helper

**Files:**
- Modify: `front/src/types/index.ts`
- Modify: `front/src/services/index.ts`
- Create: `front/src/services/tripMarkdown.ts`

**Interfaces:**
- Consumes: backend endpoints from Task 2.
- Produces: `listTrips()`, `getTrip()`, `deleteTrip()`, `planToMarkdown()`.

- [ ] **Step 1: Add frontend saved-trip types**

In `front/src/types/index.ts`, add after `TripPlanResponse`:

```ts
export interface SavedTripListItem {
  id: number
  destination: string
  days: number
  status: 'completed'
  created_at: string
}

export interface SavedTripDetail extends SavedTripListItem {
  trace_id: string | null
  request_json: TripPlanRequest
  plan_json: TripPlanResponse
  updated_at: string
}

export type TripStreamEvent =
  | { type: 'trace'; trace_id: string }
  | { type: 'status'; message: string }
  | { type: 'context'; data: unknown }
  | { type: 'plan'; data: TripPlanResponse }
  | { type: 'done' }
  | { type: 'error'; message: string }
```

- [ ] **Step 2: Update service imports and stream auth**

In `front/src/services/index.ts`, add imported types:

```ts
  SavedTripDetail,
  SavedTripListItem,
  TripStreamEvent,
```

Change `planTripStream` signature:

```ts
export async function planTripStream(
  payload: TripPlanRequest,
  onEvent: (event: TripStreamEvent) => void,
): Promise<TripPlanResponse> {
```

Inside `planTripStream`, before `fetch`, add:

```ts
  const tokens = getAuthTokens()
```

Change the `headers` object:

```ts
      headers: {
        'Content-Type': 'application/json',
        ...(tokens ? { Authorization: `Bearer ${tokens.access_token}` } : {}),
      },
```

Change event parsing:

```ts
      const event = JSON.parse(line) as TripStreamEvent
```

- [ ] **Step 3: Add trip API functions**

In `front/src/services/index.ts`, after `planTripStream`, add:

```ts
export async function listTrips(): Promise<SavedTripListItem[]> {
  return request<SavedTripListItem[]>('/api/trips')
}

export async function getTrip(id: number | string): Promise<SavedTripDetail> {
  return request<SavedTripDetail>(`/api/trips/${id}`)
}

export async function deleteTrip(id: number | string): Promise<void> {
  await request<void>(`/api/trips/${id}`, { method: 'DELETE' })
}
```

- [ ] **Step 4: Create Markdown helper**

Create `front/src/services/tripMarkdown.ts`:

```ts
import type { TripPlanResponse } from '@/types'

export function planToMarkdown(plan: TripPlanResponse): string {
  const lines = [`# ${plan.destination}行程`, '', plan.summary, '']

  for (const day of plan.days) {
    lines.push(`## 第 ${day.day} 天 · ${day.date} · ${day.title}`, '')
    lines.push(`- 天气：${day.weather}`)
    lines.push(`- 预算：${day.daily_budget}`)
    lines.push(`- 交通：${day.transport}`, '')

    for (const item of day.items) {
      lines.push(`### ${item.time} ${item.place}`)
      lines.push(item.activity)
      lines.push(`- 费用：${item.estimated_cost}`)
      lines.push(`- 预约：${item.booking_hint}`)
      lines.push(`- 来源：${item.source_hint}`, '')
    }

    if (day.notes.length > 0) {
      lines.push('注意事项：')
      for (const note of day.notes) lines.push(`- ${note}`)
      lines.push('')
    }
  }

  if (plan.tips.length > 0) {
    lines.push('## 出发前提醒', '')
    for (const tip of plan.tips) lines.push(`- ${tip}`)
    lines.push('')
  }

  lines.push('## 免责声明', '', plan.disclaimer)
  return lines.join('\n')
}

export function demo() {
  const markdown = planToMarkdown({
    trip_id: '1',
    destination: '北京',
    summary: '一天北京行程。',
    days: [
      {
        day: 1,
        date: '2026-10-01',
        title: '故宫周边',
        weather: '以实时天气为准',
        daily_budget: '约 ¥300',
        transport: '地铁和步行',
        notes: ['提前预约。'],
        items: [
          {
            time: '09:00',
            place: '故宫',
            activity: '参观中轴线。',
            estimated_cost: '需查询官方渠道',
            booking_hint: '提前预约',
            source_hint: '官方信息为准',
          },
        ],
      },
    ],
    tips: ['带身份证。'],
    disclaimer: '请以实际开放信息为准。',
  })

  console.assert(markdown.includes('# 北京行程'))
  console.assert(markdown.includes('09:00 故宫'))
}
```

- [ ] **Step 5: Run frontend build**

Run:

```bash
corepack pnpm --dir front build
```

Expected: build exits 0.

---

### Task 4: Reusable plan result and workspace list components

**Files:**
- Create: `front/src/components/TripPlanResult.vue`
- Create: `front/src/components/TripList.vue`

**Interfaces:**
- Consumes: `TripPlanResponse`, `SavedTripListItem`.
- Produces: reusable display components for Home, Workspace, Detail.

- [ ] **Step 1: Create TripPlanResult component**

Create `front/src/components/TripPlanResult.vue`:

```vue
<script setup lang="ts">
import type { TripPlanResponse } from '@/types'

defineProps<{ plan: TripPlanResponse }>()
</script>

<template>
  <div class="space-y-4">
    <div class="grid gap-4 rounded-xl bg-[#f9e79f] p-4 md:grid-cols-[220px_minmax(0,1fr)] md:items-center">
      <div>
        <p class="text-xs font-semibold text-[#523410]">{{ plan.trip_id }}</p>
        <h2 class="mt-2 text-3xl font-semibold">{{ plan.destination }}</h2>
      </div>
      <p class="text-sm leading-6 text-[#37352f]">{{ plan.summary }}</p>
    </div>

    <article v-for="day in plan.days" :key="`${day.day}-${day.date}`" class="rounded-xl border border-[#e5e3df] p-4">
      <div class="grid gap-3 lg:grid-cols-[180px_minmax(0,1fr)]">
        <div>
          <p class="text-xs font-semibold text-[#5645d4]">第 {{ day.day }} 天 · {{ day.date }}</p>
          <h3 class="mt-1 text-lg font-semibold leading-snug">{{ day.title }}</h3>
          <div class="mt-3 grid gap-2 text-xs font-medium text-[#5d5b54]">
            <p class="rounded-md bg-[#dcecfa] px-3 py-2">{{ day.weather }}</p>
            <p class="rounded-md bg-[#f9e79f] px-3 py-2">{{ day.daily_budget }}</p>
            <p class="rounded-md bg-[#d9f3e1] px-3 py-2">{{ day.transport }}</p>
          </div>
        </div>

        <ol class="grid gap-3">
          <li v-for="item in day.items" :key="`${day.date}-${item.time}-${item.place}`" class="grid gap-3 rounded-lg bg-[#fafaf9] p-3 sm:grid-cols-[72px_minmax(0,1fr)]">
            <p class="text-sm font-semibold text-[#5645d4]">{{ item.time }}</p>
            <div>
              <div class="flex flex-wrap items-center gap-2">
                <h4 class="font-semibold">{{ item.place }}</h4>
                <span class="rounded bg-white px-2 py-1 text-xs font-semibold text-[#793400]">{{ item.estimated_cost }}</span>
              </div>
              <p class="mt-2 text-sm leading-6 text-[#37352f]">{{ item.activity }}</p>
              <div class="mt-2 grid gap-2 text-xs font-medium text-[#5d5b54] md:grid-cols-2">
                <p class="rounded-md bg-white px-2 py-1.5">{{ item.booking_hint }}</p>
                <p class="rounded-md bg-white px-2 py-1.5">{{ item.source_hint }}</p>
              </div>
            </div>
          </li>
        </ol>
      </div>

      <ul class="mt-3 list-disc space-y-1 pl-5 text-sm leading-6 text-[#5d5b54]">
        <li v-for="note in day.notes" :key="note">{{ note }}</li>
      </ul>
    </article>

    <div class="rounded-xl bg-[#d9f3e1] p-4">
      <h3 class="font-semibold">出发前提醒</h3>
      <ul class="mt-3 grid gap-2 text-sm leading-6 text-[#37352f] md:grid-cols-2">
        <li v-for="tip in plan.tips" :key="tip">{{ tip }}</li>
      </ul>
      <p class="mt-4 border-t border-[#1aae39]/20 pt-4 text-xs font-semibold text-[#5d5b54]">{{ plan.disclaimer }}</p>
    </div>
  </div>
</template>
```

- [ ] **Step 2: Create TripList component**

Create `front/src/components/TripList.vue`:

```vue
<script setup lang="ts">
import { RouterLink } from 'vue-router'
import type { SavedTripListItem } from '@/types'

defineProps<{
  trips: SavedTripListItem[]
  isLoading: boolean
  error: string
}>()

const emit = defineEmits<{
  retry: []
  delete: [trip: SavedTripListItem]
}>()

function formatDate(value: string): string {
  return new Intl.DateTimeFormat('zh-CN', { dateStyle: 'medium', timeStyle: 'short' }).format(new Date(value))
}
</script>

<template>
  <div class="rounded-xl border border-[#e5e3df] bg-white p-5">
    <div class="mb-5 flex flex-col justify-between gap-3 sm:flex-row sm:items-center">
      <div>
        <p class="text-xs font-semibold uppercase text-[#5645d4]">Workspace</p>
        <h2 class="mt-2 text-2xl font-semibold">我的行程</h2>
      </div>
      <RouterLink to="/home" class="inline-flex min-h-10 items-center justify-center rounded-md bg-[#5645d4] px-4 py-2 text-sm font-medium text-white hover:bg-[#4534b3]">
        新建规划
      </RouterLink>
    </div>

    <p v-if="error" class="rounded-md border border-[#e03131]/30 bg-[#fde0ec] px-3 py-2 text-sm font-medium text-[#a02e6d]" role="alert">
      {{ error }}
      <button type="button" class="ml-2 underline" @click="emit('retry')">重试</button>
    </p>

    <p v-else-if="isLoading" class="rounded-md bg-[#fafaf9] px-3 py-8 text-center text-sm text-[#5d5b54]">
      正在加载行程...
    </p>

    <p v-else-if="trips.length === 0" class="rounded-md bg-[#fafaf9] px-3 py-8 text-center text-sm text-[#5d5b54]">
      还没有保存的行程。先新建一次规划。
    </p>

    <div v-else class="grid gap-3">
      <article v-for="trip in trips" :key="trip.id" class="grid gap-3 rounded-xl border border-[#e5e3df] p-4 sm:grid-cols-[minmax(0,1fr)_auto] sm:items-center">
        <div>
          <div class="flex flex-wrap items-center gap-2">
            <h3 class="text-lg font-semibold">{{ trip.destination }}</h3>
            <span class="rounded bg-[#d9f3e1] px-2 py-1 text-xs font-semibold text-[#1a1a1a]">{{ trip.status === 'completed' ? '已完成' : trip.status }}</span>
          </div>
          <p class="mt-2 text-sm text-[#5d5b54]">{{ trip.days }} 天 · {{ formatDate(trip.created_at) }}</p>
        </div>
        <div class="flex flex-wrap gap-2">
          <RouterLink :to="`/trips/${trip.id}`" class="rounded-md bg-[#0a1530] px-3 py-2 text-sm font-medium text-white hover:bg-[#1a2a52]">
            查看详情
          </RouterLink>
          <button type="button" class="rounded-md border border-[#c8c4be] px-3 py-2 text-sm font-medium hover:bg-[#f6f5f4]" @click="emit('delete', trip)">
            删除
          </button>
        </div>
      </article>
    </div>
  </div>
</template>
```

- [ ] **Step 3: Run frontend build**

Run:

```bash
corepack pnpm --dir front build
```

Expected: build exits 0.

---

### Task 5: Workspace page, detail page, and routes

**Files:**
- Create: `front/src/views/WorkspaceView.vue`
- Create: `front/src/views/TripDetailView.vue`
- Modify: `front/src/router/index.ts`

**Interfaces:**
- Consumes: `TripList`, `TripPlanResult`, `listTrips()`, `getTrip()`, `deleteTrip()`, `planTrip()`, `planToMarkdown()`.
- Produces: `/workspace` and `/trips/:id` user flows.

- [ ] **Step 1: Add WorkspaceView**

Create `front/src/views/WorkspaceView.vue`:

```vue
<script setup lang="ts">
import { onMounted, ref } from 'vue'
import TripList from '@/components/TripList.vue'
import { deleteTrip, listTrips, logout } from '@/services'
import type { SavedTripListItem } from '@/types'
import { useRouter } from 'vue-router'

const router = useRouter()
const trips = ref<SavedTripListItem[]>([])
const isLoading = ref(false)
const error = ref('')

async function loadTrips() {
  error.value = ''
  isLoading.value = true
  try {
    trips.value = await listTrips()
  } catch (caughtError) {
    error.value = caughtError instanceof Error ? caughtError.message : '工作台加载失败，请稍后重试。'
  } finally {
    isLoading.value = false
  }
}

async function removeTrip(trip: SavedTripListItem) {
  if (!window.confirm(`删除 ${trip.destination} 的 ${trip.days} 天游程？`)) return
  try {
    await deleteTrip(trip.id)
    trips.value = trips.value.filter((item) => item.id !== trip.id)
  } catch (caughtError) {
    error.value = caughtError instanceof Error ? caughtError.message : '删除失败，请稍后重试。'
  }
}

async function logoutAndReturn() {
  await logout()
  await router.push('/login')
}

onMounted(loadTrips)
</script>

<template>
  <main class="min-h-screen bg-[#f6f5f4] text-[#1a1a1a] [font-family:Inter,-apple-system,BlinkMacSystemFont,'Segoe_UI','PingFang_SC','Microsoft_YaHei',sans-serif]">
    <header class="border-b border-[#e5e3df] bg-white">
      <div class="mx-auto flex max-w-6xl items-center justify-between gap-4 px-4 py-4 sm:px-6 lg:px-8">
        <RouterLink to="/home" class="text-sm font-semibold text-[#0a1530]">远行手稿</RouterLink>
        <button type="button" class="rounded-md border border-[#c8c4be] px-3 py-2 text-sm font-medium hover:bg-[#f6f5f4]" @click="logoutAndReturn">
          退出登录
        </button>
      </div>
    </header>

    <section class="mx-auto max-w-6xl px-4 py-8 sm:px-6 lg:px-8">
      <TripList :trips="trips" :is-loading="isLoading" :error="error" @retry="loadTrips" @delete="removeTrip" />
    </section>
  </main>
</template>
```

- [ ] **Step 2: Add TripDetailView**

Create `front/src/views/TripDetailView.vue`:

```vue
<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { useRoute, useRouter } from 'vue-router'
import TripPlanResult from '@/components/TripPlanResult.vue'
import { deleteTrip, getTrip, planTrip } from '@/services'
import { planToMarkdown } from '@/services/tripMarkdown'
import type { SavedTripDetail } from '@/types'

const route = useRoute()
const router = useRouter()
const trip = ref<SavedTripDetail | null>(null)
const isLoading = ref(false)
const isRegenerating = ref(false)
const error = ref('')
const copyMessage = ref('')
const tripId = computed(() => String(route.params.id))

async function loadTrip() {
  error.value = ''
  isLoading.value = true
  try {
    trip.value = await getTrip(tripId.value)
  } catch (caughtError) {
    error.value = caughtError instanceof Error ? caughtError.message : '行程加载失败。'
  } finally {
    isLoading.value = false
  }
}

async function copyMarkdown() {
  if (!trip.value) return
  const markdown = planToMarkdown(trip.value.plan_json)
  try {
    await navigator.clipboard.writeText(markdown)
    copyMessage.value = '已复制 Markdown。'
  } catch {
    copyMessage.value = '复制失败，请手动复制页面内容。'
  }
}

async function regenerateTrip() {
  if (!trip.value) return
  isRegenerating.value = true
  error.value = ''
  try {
    const plan = await planTrip(trip.value.request_json)
    await router.push(`/trips/${plan.trip_id}`)
  } catch (caughtError) {
    error.value = caughtError instanceof Error ? caughtError.message : '重新生成失败，请稍后重试。'
  } finally {
    isRegenerating.value = false
  }
}

async function removeTrip() {
  if (!trip.value) return
  if (!window.confirm(`删除 ${trip.value.destination} 的 ${trip.value.days} 天游程？`)) return
  try {
    await deleteTrip(trip.value.id)
    await router.push('/workspace')
  } catch (caughtError) {
    error.value = caughtError instanceof Error ? caughtError.message : '删除失败，请稍后重试。'
  }
}

function formatDate(value: string): string {
  return new Intl.DateTimeFormat('zh-CN', { dateStyle: 'medium', timeStyle: 'short' }).format(new Date(value))
}

onMounted(loadTrip)
</script>

<template>
  <main class="min-h-screen bg-[#f6f5f4] text-[#1a1a1a] [font-family:Inter,-apple-system,BlinkMacSystemFont,'Segoe_UI','PingFang_SC','Microsoft_YaHei',sans-serif]">
    <header class="border-b border-[#e5e3df] bg-white">
      <div class="mx-auto flex max-w-6xl items-center justify-between gap-4 px-4 py-4 sm:px-6 lg:px-8">
        <RouterLink to="/workspace" class="text-sm font-semibold text-[#0a1530]">← 返回工作台</RouterLink>
        <RouterLink to="/home" class="rounded-md bg-[#5645d4] px-3 py-2 text-sm font-medium text-white hover:bg-[#4534b3]">新建规划</RouterLink>
      </div>
    </header>

    <section class="mx-auto max-w-6xl px-4 py-8 sm:px-6 lg:px-8">
      <p v-if="isLoading" class="rounded-xl bg-white p-8 text-center text-sm text-[#5d5b54]">正在加载行程...</p>

      <div v-else-if="error && !trip" class="rounded-xl border border-[#e03131]/30 bg-white p-6">
        <p class="text-sm font-medium text-[#a02e6d]">{{ error }}</p>
        <RouterLink to="/workspace" class="mt-4 inline-flex rounded-md bg-[#0a1530] px-3 py-2 text-sm font-medium text-white">返回工作台</RouterLink>
      </div>

      <div v-else-if="trip" class="space-y-5">
        <div class="rounded-xl border border-[#e5e3df] bg-white p-5">
          <p class="text-xs font-semibold uppercase text-[#5645d4]">Trip Detail</p>
          <div class="mt-3 flex flex-col justify-between gap-4 lg:flex-row lg:items-end">
            <div>
              <h1 class="text-3xl font-semibold">{{ trip.destination }}</h1>
              <p class="mt-2 text-sm text-[#5d5b54]">{{ trip.days }} 天 · {{ formatDate(trip.created_at) }}</p>
            </div>
            <div class="flex flex-wrap gap-2">
              <button type="button" class="rounded-md border border-[#c8c4be] px-3 py-2 text-sm font-medium hover:bg-[#f6f5f4]" @click="copyMarkdown">复制 Markdown</button>
              <button type="button" :disabled="isRegenerating" class="rounded-md bg-[#5645d4] px-3 py-2 text-sm font-medium text-white hover:bg-[#4534b3] disabled:bg-[#e5e3df] disabled:text-[#bbb8b1]" @click="regenerateTrip">
                {{ isRegenerating ? '重新生成中...' : '重新生成' }}
              </button>
              <button type="button" class="rounded-md border border-[#e03131]/40 px-3 py-2 text-sm font-medium text-[#a02e6d] hover:bg-[#fde0ec]" @click="removeTrip">删除</button>
            </div>
          </div>
          <p v-if="copyMessage" class="mt-3 text-sm font-medium text-[#1aae39]">{{ copyMessage }}</p>
          <p v-if="error" class="mt-3 rounded-md border border-[#e03131]/30 bg-[#fde0ec] px-3 py-2 text-sm font-medium text-[#a02e6d]">{{ error }}</p>
        </div>

        <TripPlanResult :plan="trip.plan_json" />
      </div>
    </section>
  </main>
</template>
```

- [ ] **Step 3: Add routes and guard**

In `front/src/router/index.ts`, add routes before catch-all:

```ts
  {
    path: '/workspace',
    name: 'workspace',
    component: () => import('@/views/WorkspaceView.vue'),
  },
  {
    path: '/trips/:id',
    name: 'trip-detail',
    component: () => import('@/views/TripDetailView.vue'),
  },
```

Replace guard body with:

```ts
router.beforeEach((to) => {
  const isLoggedIn = getAuthTokens() !== null
  const protectedRoutes = new Set(['home', 'workspace', 'trip-detail'])

  if (typeof to.name === 'string' && protectedRoutes.has(to.name) && !isLoggedIn) {
    return { name: 'login' }
  }

  if ((to.name === 'login' || to.path === '/') && isLoggedIn) {
    return { name: 'home' }
  }

  return true
})
```

- [ ] **Step 4: Run frontend build**

Run:

```bash
corepack pnpm --dir front build
```

Expected: build exits 0.

---

### Task 6: Home page saved-state integration

**Files:**
- Modify: `front/src/views/HomeView.vue`

**Interfaces:**
- Consumes: `TripPlanResponse.trip_id`, `/workspace`, `/trips/:id` routes, `TripPlanResult`.
- Produces: visible saved-to-workspace success action after generation.

- [ ] **Step 1: Import TripPlanResult**

In `front/src/views/HomeView.vue`, add import:

```ts
import TripPlanResult from '@/components/TripPlanResult.vue'
```

- [ ] **Step 2: Track save message**

In script state, add:

```ts
const saveMessage = ref('')
```

At the start of `createPlan()`, after `error.value = ''`, add:

```ts
  saveMessage.value = ''
```

After `plan.value = await planTripStream(...)`, add:

```ts
    saveMessage.value = '已保存到工作台。'
```

- [ ] **Step 3: Add workspace nav link in header**

In the logged-in header actions near the logout button, add:

```vue
<RouterLink
  v-if="isLoggedIn"
  to="/workspace"
  class="rounded-md border border-[#c8c4be] px-3 py-2 text-sm font-medium hover:bg-[#f6f5f4]"
>
  工作台
</RouterLink>
```

- [ ] **Step 4: Show saved actions above generated plan**

In the `v-else` block that currently renders the generated plan, add before the plan content:

```vue
<div v-if="saveMessage && plan" class="rounded-xl border border-[#1aae39]/30 bg-[#d9f3e1] p-4">
  <p class="font-semibold text-[#1a1a1a]">{{ saveMessage }}</p>
  <div class="mt-3 flex flex-wrap gap-2">
    <RouterLink :to="`/trips/${plan.trip_id}`" class="rounded-md bg-[#0a1530] px-3 py-2 text-sm font-medium text-white hover:bg-[#1a2a52]">
      查看本次行程详情
    </RouterLink>
    <RouterLink to="/workspace" class="rounded-md border border-[#c8c4be] bg-white px-3 py-2 text-sm font-medium hover:bg-[#f6f5f4]">
      查看工作台
    </RouterLink>
  </div>
</div>
```

- [ ] **Step 5: Replace inline plan renderer with TripPlanResult**

Inside `HomeView.vue`, replace the generated-plan day/tips markup under `v-else` with:

```vue
<TripPlanResult :plan="plan" />
```

Keep the surrounding `v-else` container and saved actions from Step 4.

- [ ] **Step 6: Run frontend build**

Run:

```bash
corepack pnpm --dir front build
```

Expected: build exits 0.

---

### Task 7: End-to-end verification

**Files:**
- No planned source edits unless a previous task produced a failing check.

**Interfaces:**
- Consumes: all prior task outputs.
- Produces: verified MVP behavior.

- [ ] **Step 1: Run backend syntax check**

Run:

```bash
python -m compileall backend/src
```

Expected: command exits 0.

- [ ] **Step 2: Run frontend production build**

Run:

```bash
corepack pnpm --dir front build
```

Expected: command exits 0.

- [ ] **Step 3: Apply migration in local dev database**

From `backend/`, run:

```bash
python -m uv run alembic upgrade head
```

Expected: command exits 0 and `trips` table exists.

- [ ] **Step 4: Start backend**

From `backend/`, run:

```bash
python -m uv run uvicorn src.app.main:app --reload
```

Expected: API starts on port 8000.

- [ ] **Step 5: Start frontend**

In another terminal, run:

```bash
corepack pnpm --dir front dev
```

Expected: Vite starts and prints a local URL.

- [ ] **Step 6: Manual browser acceptance**

Use the app and confirm:

```text
1. 登录后访问 /home。
2. 生成一次行程。
3. /home 显示“已保存到工作台”。
4. 点击“查看工作台”，/workspace 出现刚生成的行程。
5. 点击“查看详情”，/trips/:id 展示完整行程。
6. 点击“复制 Markdown”，看到成功提示。
7. 点击“重新生成”，生成新行程并跳到新 /trips/:id。
8. 点击“删除”，确认后回到 /workspace，旧行程不再出现。
9. 退出登录后直接访问 /workspace 或 /trips/:id，会跳回 /login。
```

- [ ] **Step 7: Report verification**

In the implementation summary, include exact results:

```text
Backend: python -m compileall backend/src — pass/fail
Frontend: corepack pnpm --dir front build — pass/fail
Migration: python -m uv run alembic upgrade head — pass/fail or skipped with reason
Manual browser acceptance — pass/fail or skipped with reason
```

---

## Self-Review

- Spec coverage: generation auto-save is in Task 2 and Task 6; `/workspace` is Task 5; `/trips/:id` is Task 5; list/detail/delete APIs are Task 2; copy Markdown is Task 3 and Task 5; regenerate is Task 5; auth isolation is Task 1 and Task 2.
- Scope check: no sharing, PDF, title/notes editing, anonymous trips, structured trip tables, or new dependencies are included.
- Type consistency: backend saved-trip fields are `id`, `destination`, `days`, `status`, `created_at`, `trace_id`, `request_json`, `plan_json`, `updated_at`; frontend types and views use the same names.
- Commit behavior: omitted by user request; implementation should not commit unless the user explicitly asks.
