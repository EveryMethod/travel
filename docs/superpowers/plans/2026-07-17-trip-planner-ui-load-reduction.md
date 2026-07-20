# 旅行规划表单减负 Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** 降低首页生成旅行计划表单的填写负担，让用户先完成核心输入，再按需补充偏好。

**Architecture:** 只修改 `front/src/views/HomeView.vue`。保留现有数据模型、提交 payload、流式生成和结果组件；调整页面顺序、表单分组、旅行风格选择方式、分项预算展示方式和右侧未生成状态。

**Tech Stack:** Vue 3 `<script setup>`, TypeScript, Tailwind CSS, native `<details>`, native `<input type="date">`.

## Global Constraints

- 不新增依赖。
- 不改 API、types、services、router、后端。
- 不改变提交 payload 字段名或生成逻辑。
- 日期继续使用原生 `<input type="date">`。
- 旅行风格仍至少保留 1 个选项。
- 页面文案使用中文。

---

## Required changes

Modify only `front/src/views/HomeView.vue`:

1. Move the complete `<section id="planner" ...>` so it appears immediately after the hero section and before `<section id="destinations" ...>`. Keep IDs and nav links unchanged.
2. Add a computed summary after `selectedStyleLabels`:

```ts
const summaryItems = computed(() => [
  { label: '目的地', value: form.destination.trim() || '未填写' },
  { label: '出发地', value: form.origin.trim() || '未填写' },
  { label: '日期', value: `${form.start_date || '未定'} 至 ${form.end_date || '未定'}` },
  { label: '天数', value: `${form.days} 天` },
  { label: '风格', value: selectedStyleLabels.value || '未选择' },
  { label: '预算', value: form.budget.trim() ? `¥${form.budget.trim()}` : '未填写' },
  { label: '节奏', value: paceOptions.find((option) => option.value === form.pace)?.label ?? '适中' },
  { label: '同行', value: companionOptions.find((option) => option.value === form.companions)?.label ?? '朋友' },
])
```

3. Change planner helper copy from `保留原来的生成能力，只把表单和结果区改成更像工作台的双栏布局。` to `先填必要信息就能生成；预算拆分、同行人和补充偏好都可以之后再加。`
4. Inside the form's `<div class="space-y-3">`, add a basic-info label before destination:

```vue
<div class="rounded-lg bg-[#fafaf9] px-3 py-2">
  <p class="text-sm font-semibold">基础信息</p>
  <p class="mt-1 text-xs leading-5 text-[#5d5b54]">这些足够生成第一版路线。</p>
</div>
```

5. Add an optional-preferences label before the budget field:

```vue
<div class="pt-2">
  <p class="text-sm font-semibold">补充偏好</p>
  <p class="mt-1 text-xs leading-5 text-[#5d5b54]">想控制得更细再填，不填也能生成。</p>
</div>
```

6. Replace the travel style `<details>` dropdown with visible chip buttons:

```vue
<div class="block sm:col-span-2">
  <span class="text-sm font-medium">旅行风格</span>
  <div class="mt-2 flex flex-wrap gap-2">
    <button
      v-for="option in styleOptions"
      :key="option.value"
      type="button"
      class="rounded-md border px-3 py-2 text-sm font-medium transition"
      :class="form.travel_style.includes(option.value) ? 'border-[#5645d4] bg-[#e6e0f5] text-[#391c57]' : 'border-[#c8c4be] bg-white text-[#5d5b54] hover:bg-[#fafaf9]'"
      :aria-pressed="form.travel_style.includes(option.value)"
      @click="toggleTravelStyle(option.value)"
    >
      {{ option.label }}
    </button>
  </div>
</div>
```

7. Keep the total budget input visible, but wrap the four `budget_breakdown` inputs in a native details block, default closed:

```vue
<details class="rounded-lg border border-[#e5e3df] bg-[#fafaf9] p-3">
  <summary class="cursor-pointer text-sm font-semibold text-[#37352f]">展开分项预算</summary>
  <div class="mt-3 grid gap-2 sm:grid-cols-2">
    <input v-model="form.budget_breakdown.transport" inputmode="numeric" class="h-10 w-full rounded-md border border-[#c8c4be] bg-white px-3 text-sm outline-none focus:border-[#5645d4] focus:ring-2 focus:ring-[#d6b6f6]" placeholder="交通 1200" />
    <input v-model="form.budget_breakdown.hotel" inputmode="numeric" class="h-10 w-full rounded-md border border-[#c8c4be] bg-white px-3 text-sm outline-none focus:border-[#5645d4] focus:ring-2 focus:ring-[#d6b6f6]" placeholder="住宿 1800" />
    <input v-model="form.budget_breakdown.food" inputmode="numeric" class="h-10 w-full rounded-md border border-[#c8c4be] bg-white px-3 text-sm outline-none focus:border-[#5645d4] focus:ring-2 focus:ring-[#d6b6f6]" placeholder="餐饮 900" />
    <input v-model="form.budget_breakdown.tickets" inputmode="numeric" class="h-10 w-full rounded-md border border-[#c8c4be] bg-white px-3 text-sm outline-none focus:border-[#5645d4] focus:ring-2 focus:ring-[#d6b6f6]" placeholder="门票 600" />
  </div>
</details>
```

8. Replace the `v-else-if="!plan"` empty state with:

```vue
<div v-else-if="!plan" class="rounded-xl border border-dashed border-[#c8c4be] bg-[#fafaf9] p-6">
  <h4 class="text-2xl font-semibold">先生成第一版，再慢慢改。</h4>
  <p class="mt-3 max-w-2xl leading-7 text-[#5d5b54]">
    左侧这些信息已经足够生成路线草案。补充偏好会让结果更准，但不是必填。
  </p>

  <dl class="mt-6 grid gap-3 sm:grid-cols-2">
    <div v-for="item in summaryItems" :key="item.label" class="rounded-lg bg-white p-3">
      <dt class="text-xs font-semibold text-[#787671]">{{ item.label }}</dt>
      <dd class="mt-1 text-sm font-medium text-[#1a1a1a]">{{ item.value }}</dd>
    </div>
  </dl>

  <div v-if="form.must_see || form.avoid || form.notes" class="mt-4 rounded-lg bg-[#e6e0f5] p-4 text-sm leading-6 text-[#391c57]">
    <p v-if="form.must_see"><span class="font-semibold">必去：</span>{{ form.must_see }}</p>
    <p v-if="form.avoid"><span class="font-semibold">避开：</span>{{ form.avoid }}</p>
    <p v-if="form.notes"><span class="font-semibold">补充：</span>{{ form.notes }}</p>
  </div>
</div>
```

9. Run `npm --prefix /Users/alh/code/travel/.claude/worktrees/trip-planner-ui-load-reduction/front run build`.

No commits unless the user explicitly asks.
