# 首页旅行路书视觉优化 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 按顺序完成首页 7 个 UI 优化点，把当前“通用 AI 工作台”进一步收束成“旅行路书 / 出发确认单”的产品体验。

**Architecture:** 保持 lazy scope：只改 `front/src/views/HomeView.vue`，不拆组件、不加依赖、不改 API。继续复用现有 Vue state、`submittedNotes`、`summaryItems`、`optionalSummaryItems` 和 `createPlan()`；所有视觉升级都通过现有 Tailwind class、原生 HTML 控件和少量 computed 数据完成。

**Tech Stack:** Vue 3 `<script setup>`, TypeScript, Tailwind CSS, native `<details>`, native `<input type="date">`, Playwright runtime verification.

## Global Constraints

- 只修改 `front/src/views/HomeView.vue`。
- 不新增依赖。
- 不改 API、types、services、router、后端。
- 不新增 payload 字段名；可选细节继续折入现有 `notes`。
- 日期继续使用原生 `<input type="date">`。
- 旅行风格仍至少保留 1 个选项。
- 页面文案使用中文。
- 保持当前认证门禁；验证 `/home` 时可用 dummy `travel_auth_tokens` 进入页面。
- 每个任务完成后至少运行 `npm --prefix /Users/alh/code/travel/.claude/worktrees/trip-planner-ui-load-reduction/front run build`。

---

## File Structure

- Modify: `front/src/views/HomeView.vue`
  - Script: 只在需要时新增常量 / computed，例如目的地模板点击填充函数、移动端 sticky 判断不需要 JS。
  - Template: 调整 hero、planner form、summary empty state、destination cards、loading state。
  - Styling: 只使用 Tailwind class；不创建新的 CSS 文件。

No new files.

---

### Task 1: Hero mockup becomes a travel manuscript / ticket sheet

**Files:**
- Modify: `front/src/views/HomeView.vue` hero mockup block inside `<section id="top">`.

**Interfaces:**
- Consumes: static hero copy and existing decorative color blocks.
- Produces: static hero visual that reads as `行程手稿 / 车票路书`, no runtime behavior.

- [ ] **Step 1: Replace the current generic workspace mockup content**

In the hero right-side card, keep the outer white card shell and window dots. Replace the inner two-column “出行摘要 + 第 1 天” dashboard with a single manuscript/ticket composition:

```vue
<div class="p-4">
  <div class="rounded-xl border border-dashed border-[#c8c4be] bg-[#f8f5e8] p-5 shadow-[0_18px_40px_rgba(15,15,15,0.16)]">
    <div class="flex items-start justify-between gap-4 border-b border-[#d8c7a4] pb-4">
      <div>
        <p class="text-xs font-semibold tracking-[0.2em] text-[#9a5b13]">ROUTE DRAFT</p>
        <h2 class="mt-2 text-3xl font-semibold leading-tight">北京 1 日路书</h2>
        <p class="mt-2 text-sm text-[#5d5b54]">上海出发 · 本地美食 · 适中节奏</p>
      </div>
      <div class="rounded-lg bg-[#dd5b00] px-3 py-2 text-right text-white">
        <p class="text-xs font-semibold">出发</p>
        <p class="text-xl font-semibold">07.17</p>
      </div>
    </div>

    <ol class="mt-5 space-y-4">
      <li class="grid grid-cols-[56px_1fr] gap-3">
        <p class="text-sm font-semibold text-[#dd5b00]">09:00</p>
        <div class="border-l-2 border-dashed border-[#dd5b00] pl-4">
          <h3 class="font-semibold">故宫</h3>
          <p class="mt-1 text-sm text-[#5d5b54]">预约、门票和入口提醒放在同一处。</p>
        </div>
      </li>
      <li class="grid grid-cols-[56px_1fr] gap-3">
        <p class="text-sm font-semibold text-[#dd5b00]">12:30</p>
        <div class="border-l-2 border-dashed border-[#dd5b00] pl-4">
          <h3 class="font-semibold">胡同午餐</h3>
          <p class="mt-1 text-sm text-[#5d5b54]">把本地小吃排进真实动线。</p>
        </div>
      </li>
      <li class="grid grid-cols-[56px_1fr] gap-3">
        <p class="text-sm font-semibold text-[#dd5b00]">16:40</p>
        <div class="border-l-2 border-dashed border-[#dd5b00] pl-4">
          <h3 class="font-semibold">景山日落</h3>
          <p class="mt-1 text-sm text-[#5d5b54]">保留缓冲时间，不把一天塞满。</p>
        </div>
      </li>
    </ol>

    <div class="mt-5 grid gap-3 sm:grid-cols-2">
      <div class="rounded-lg bg-white/70 p-3 text-sm font-medium text-[#37352f]">预算：¥5000</div>
      <div class="rounded-lg bg-white/70 p-3 text-sm font-medium text-[#37352f]">提醒：核对开放时间</div>
    </div>
  </div>
</div>
```

- [ ] **Step 2: Remove redundant mini-dashboard copy**

Delete old static phrases that make the hero look like a SaaS dashboard, including `路线工作台` inner mock labels only if they duplicate the new ticket concept. Keep the top window label if useful, but prefer `路书草稿`.

- [ ] **Step 3: Verify**

Run:

```bash
npm --prefix /Users/alh/code/travel/.claude/worktrees/trip-planner-ui-load-reduction/front run build
```

Expected: build succeeds.

Runtime check:
- Start frontend on a non-stale port, e.g. `5175`.
- Open `/home` with dummy `travel_auth_tokens`.
- Hero right card visually reads as a route manuscript/ticket, not a generic dashboard.

---

### Task 2: Collapse optional details as one block and move primary CTA earlier

**Files:**
- Modify: `front/src/views/HomeView.vue` planner form block.

**Interfaces:**
- Consumes: existing `createPlan()`, `canSubmit`, `form`, `submittedNotes`.
- Produces: same submit behavior; visible submit button appears before optional details.

- [ ] **Step 1: Keep basic fields above the primary button**

Ensure only these fields appear before the first submit button:

- 目的地
- 出发地
- 旅行天数
- 出行日期
- 旅行风格 chips

- [ ] **Step 2: Move the existing submit button immediately after travel style**

Place this button before optional details:

```vue
<button type="submit" :disabled="!canSubmit" class="inline-flex min-h-10 w-full items-center justify-center gap-2 rounded-md bg-[#5645d4] px-5 py-2.5 text-sm font-medium text-white hover:bg-[#4534b3] disabled:cursor-not-allowed disabled:bg-[#e5e3df] disabled:text-[#bbb8b1]">
  {{ isLoading ? '正在整理路线...' : '生成路线草案' }}
  <ArrowRight class="h-4 w-4" aria-hidden="true" />
</button>
```

- [ ] **Step 3: Wrap all optional fields in one native details block**

Move `总预算`, `展开分项预算`, `节奏`, `同行人`, `必去`, `避开`, and `补充偏好` inside:

```vue
<details class="rounded-xl border border-[#e5e3df] bg-[#fafaf9] p-3">
  <summary class="cursor-pointer text-sm font-semibold text-[#37352f]">可选细节：预算、同行人、必去地点</summary>
  <div class="mt-4 space-y-3">
    <!-- existing optional fields move here -->
  </div>
</details>
```

Do not put a second desktop submit button inside the details block.

- [ ] **Step 4: Verify**

Run build command above.

Runtime check:
- On desktop, submit button is visible before optional details are expanded.
- Optional block is collapsed on first load.
- Expanding optional block exposes all previous optional controls.
- Submit still sends the same payload shape with optional details folded into `notes`.

---

### Task 3: Turn the right-side empty summary into a departure confirmation sheet

**Files:**
- Modify: `front/src/views/HomeView.vue` empty state block `v-else-if="!plan"`.

**Interfaces:**
- Consumes: `summaryItems`, `optionalSummaryItems`.
- Produces: same reactive data, new visual layout.

- [ ] **Step 1: Replace the grid-card summary with confirmation-sheet layout**

Keep the heading and helper text, but replace the `dl` grid with this structure:

```vue
<div class="mt-6 rounded-xl border border-[#d8c7a4] bg-[#f8f5e8] p-5">
  <div class="flex items-center justify-between border-b border-[#d8c7a4] pb-3">
    <p class="text-xs font-semibold tracking-[0.2em] text-[#9a5b13]">DEPARTURE CHECK</p>
    <span class="rounded-md bg-[#dd5b00] px-2 py-1 text-xs font-semibold text-white">草案</span>
  </div>

  <dl class="mt-4 divide-y divide-[#e0d2b6]">
    <div v-for="item in summaryItems" :key="item.label" class="grid grid-cols-[88px_1fr] gap-4 py-2 text-sm">
      <dt class="font-semibold text-[#787671]">{{ item.label }}</dt>
      <dd class="font-medium text-[#1a1a1a]">{{ item.value }}</dd>
    </div>
  </dl>
</div>
```

- [ ] **Step 2: Restyle optional preview as a note sticker**

Replace the current purple optional preview wrapper with:

```vue
<div v-if="optionalSummaryItems.length > 0" class="mt-4 rotate-[-0.5deg] rounded-lg bg-[#f9e79f] p-4 text-sm leading-6 text-[#523410] shadow-sm">
  <p v-for="item in optionalSummaryItems" :key="item.label">
    <span class="font-semibold">{{ item.label }}：</span>{{ item.value }}
  </p>
</div>
```

- [ ] **Step 3: Verify**

Run build command above.

Runtime check:
- Empty state looks like a confirmation sheet.
- Optional preview remains hidden on first load.
- Optional preview appears as yellow note after user fills `必去`, `避开`, budget breakdown, or notes.

---

### Task 4: Make destination inspiration cards act like templates

**Files:**
- Modify: `front/src/views/HomeView.vue` script `destinations` array and destination card template.

**Interfaces:**
- Consumes: existing `destinations`, `form`, `toggleTravelStyle` behavior.
- Produces: clicking a template pre-fills existing fields only; no API changes.

- [ ] **Step 1: Extend destination objects with template values**

Update each object in `destinations` to include:

```ts
styles: ['culture'] as TravelStyle[],
notes: '偏好一句话',
budget: '5000',
```

Use concrete values:

```ts
{
  name: '京都',
  accent: '人文 / 慢游 / 美食',
  description: '庭院、町屋和本地料理排成一条慢路线。',
  tint: 'bg-[#ffe8d4]',
  styles: ['culture', 'food'] as TravelStyle[],
  notes: '想要庭院、町屋和本地料理，节奏不要太赶。',
  budget: '6000',
}
```

Repeat with matching styles for 大理、巴黎、冰岛. Keep all values Chinese.

- [ ] **Step 2: Add an apply function**

Add after `toggleTravelStyle()`:

```ts
function applyDestinationTemplate(destination: { name: string; styles: TravelStyle[]; notes: string; budget: string }) {
  form.destination = destination.name
  form.travel_style = [...destination.styles]
  form.notes = destination.notes
  form.budget = destination.budget
  document.querySelector('#planner')?.scrollIntoView({ behavior: 'smooth' })
}
```

- [ ] **Step 3: Add template CTA to each card**

Inside each destination card, add:

```vue
<button type="button" class="mt-5 rounded-md bg-[#0a1530] px-3 py-2 text-sm font-medium text-white hover:bg-[#1a2a52]" @click="applyDestinationTemplate(destination)">
  用这个开始
</button>
```

- [ ] **Step 4: Verify**

Run build command above.

Runtime check:
- Clicking 京都 card fills destination as 京都, updates style chips, budget, notes, and scrolls to planner.
- Payload still uses existing fields only.

---

### Task 5: Shift color language from Notion-like SaaS to travel materials

**Files:**
- Modify: `front/src/views/HomeView.vue` color classes only.

**Interfaces:**
- Consumes: existing layout and components.
- Produces: same DOM behavior; visual palette emphasizes night route, paper, ticket orange, map blue.

- [ ] **Step 1: Define color use by search-and-replace discipline**

Use these roles without adding CSS variables:

- Night route: keep `#0a1530` for hero/nav dark surfaces.
- Ticket orange: use `#dd5b00` for timeline, stamps, and high-signal accents.
- Paper: use `#f8f5e8` for route sheets / confirmation sheets.
- Map blue: use `#dcecfa` for calm route hints.
- Purple: keep `#5645d4` only for primary CTA and selected style chips.

- [ ] **Step 2: Reduce non-essential purple blocks**

Do not change the primary CTA. For decorative or informational blocks currently using purple backgrounds, switch them to paper/yellow/map-blue if they are not the main action.

Concrete examples:
- Optional preview: already yellow from Task 3.
- Loading step active chip can remain purple because it marks current progress.
- Section eyebrow text can remain purple if changing it would cause broad churn.

- [ ] **Step 3: Verify**

Run build command above.

Runtime check:
- Primary CTA remains clearly purple.
- Hero and summary surfaces feel like route/ticket paper.
- Page no longer has large purple informational blocks outside selected chips/current step.

---

### Task 6: Add mobile sticky generate button

**Files:**
- Modify: `front/src/views/HomeView.vue` planner section.

**Interfaces:**
- Consumes: `canSubmit`, `isLoading`, `createPlan()` through form submission.
- Produces: mobile-only duplicate submit control; desktop unchanged.

- [ ] **Step 1: Add mobile sticky button inside the form**

After the optional details block, add:

```vue
<div class="sticky bottom-3 z-20 mt-4 rounded-xl border border-[#e5e3df] bg-white/95 p-2 shadow-lg backdrop-blur lg:hidden">
  <button type="submit" :disabled="!canSubmit" class="inline-flex min-h-11 w-full items-center justify-center gap-2 rounded-md bg-[#5645d4] px-5 py-2.5 text-sm font-medium text-white hover:bg-[#4534b3] disabled:cursor-not-allowed disabled:bg-[#e5e3df] disabled:text-[#bbb8b1]">
    {{ isLoading ? '正在整理路线...' : '生成路线草案' }}
    <ArrowRight class="h-4 w-4" aria-hidden="true" />
  </button>
</div>
```

- [ ] **Step 2: Hide the earlier primary button on mobile only if duplicate feels too close**

Default lazy choice: keep both. If runtime mobile screenshot shows two buttons within one viewport, change the first submit button class from `w-full` to include `hidden lg:inline-flex`, and keep the sticky button as the mobile action.

- [ ] **Step 3: Verify**

Run build command above.

Runtime check:
- Desktop width: no sticky mobile bar visible.
- Mobile width around `390x844`: sticky generate button visible while scrolling form.
- Button disabled/enabled state matches existing `canSubmit`.

---

### Task 7: Replace loading skeleton with route assembly timeline

**Files:**
- Modify: `front/src/views/HomeView.vue` `v-if="isLoading"` block.

**Interfaces:**
- Consumes: existing `streamMessage`, `streamSteps`, `isLoading`.
- Produces: same loading state behavior, clearer route-assembly visual.

- [ ] **Step 1: Replace generic skeleton card with route assembly copy**

Keep the loading wrapper, but change the main title/copy to:

```vue
<h4 class="text-2xl font-semibold">正在拼出路线</h4>
<p class="mt-2 leading-7 text-[#5d5b54]">{{ streamMessage || '正在把目的地、日期和偏好整理成路书...' }}</p>
```

- [ ] **Step 2: Render stream steps as a route timeline**

Replace the current `ol` styling with route-like rows:

```vue
<ol class="mt-5 space-y-3">
  <li v-for="(step, index) in streamSteps" :key="`${step}-${index}`" class="grid grid-cols-[32px_minmax(0,1fr)] gap-3">
    <span class="relative grid h-8 w-8 place-items-center rounded-full text-xs font-semibold" :class="index === streamSteps.length - 1 ? 'bg-[#dd5b00] text-white' : 'bg-[#f8f5e8] text-[#9a5b13]'">
      {{ index + 1 }}
    </span>
    <span class="rounded-lg border px-3 py-2 text-sm font-medium" :class="index === streamSteps.length - 1 ? 'border-[#dd5b00]/30 bg-[#fff3e6] text-[#793400]' : 'border-[#e5e3df] bg-white text-[#5d5b54]'">
      {{ step }}
    </span>
  </li>
  <li v-if="streamSteps.length === 0" class="grid grid-cols-[32px_minmax(0,1fr)] gap-3">
    <span class="h-8 w-8 animate-pulse rounded-full bg-[#dd5b00]" />
    <span class="rounded-lg border border-[#e5e3df] bg-white px-3 py-2 text-sm font-medium text-[#5d5b54]">
      正在连接规划服务...
    </span>
  </li>
</ol>
```

- [ ] **Step 3: Simplify lower skeleton**

Replace the lower skeleton section with a paper route preview using 2-3 placeholder rows. Keep it lightweight; do not add new animation systems.

- [ ] **Step 4: Verify**

Run build command above.

Runtime check with mocked `/api/trips/plan/stream` or real backend:
- Clicking generate shows “正在拼出路线”.
- Stream status rows render as route timeline.
- Final plan still replaces loading state normally.

---

## Final Verification

- [ ] **Step 1: Start worktree frontend on a non-stale port**

```bash
npm --prefix /Users/alh/code/travel/.claude/worktrees/trip-planner-ui-load-reduction/front run dev -- --host 127.0.0.1 --port 5175
```

- [ ] **Step 2: Enter `/home` with local auth token**

In Playwright or browser console:

```js
localStorage.setItem('travel_auth_tokens', JSON.stringify({ access_token: 'dev', refresh_token: 'dev' }))
location.href = '/home'
```

- [ ] **Step 3: Verify the seven claims in the running app**

Checklist:

- Hero mockup is a route manuscript / ticket sheet.
- Submit button appears before optional details.
- Optional details are collapsed on first load.
- Right summary is a departure confirmation sheet.
- Destination template card fills existing form fields.
- Mobile sticky generate button appears only on mobile widths.
- Loading state uses route assembly timeline and final plan renders.

- [ ] **Step 4: Capture submit payload**

Use Playwright route interception and verify payload shape remains:

```json
{
  "destination": "京都",
  "origin": "上海",
  "days": 1,
  "budget": "6000",
  "travel_style": ["culture", "food"],
  "start_date": "YYYY-MM-DD",
  "end_date": "YYYY-MM-DD",
  "notes": "...可选细节折入这里..."
}
```

No new top-level payload fields are allowed.

- [ ] **Step 5: Final build**

```bash
npm --prefix /Users/alh/code/travel/.claude/worktrees/trip-planner-ui-load-reduction/front run build
```

Expected: build succeeds.

---

## Self-Review Notes

- Spec coverage: all 7 requested points map to Tasks 1-7 in order.
- Scope: one file only; no dependencies; no backend/API/type changes.
- YAGNI: no new component split, no map, no animation library, no design-token refactor.
- Known tradeoff: `HomeView.vue` remains large. This is intentional for now; split only if future edits make reuse necessary.
