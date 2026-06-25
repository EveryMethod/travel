<script setup lang="ts">
import { computed, reactive, ref } from 'vue'
import { ArrowRight, Compass, Gem, MapPinned, Route, ShieldCheck } from 'lucide-vue-next'

import { planTrip } from '@/services'
import type { BudgetLevel, TravelStyle, TripPlanResponse } from '@/types'

const budgetOptions: Array<{ label: string; value: BudgetLevel }> = [
  { label: '经济', value: 'low' },
  { label: '均衡', value: 'medium' },
  { label: '舒适', value: 'high' },
]

const styleOptions: Array<{ label: string; value: TravelStyle }> = [
  { label: '人文历史', value: 'culture' },
  { label: '本地美食', value: 'food' },
  { label: '自然风景', value: 'nature' },
  { label: '亲子友好', value: 'family' },
  { label: '浪漫慢游', value: 'romantic' },
  { label: '探索冒险', value: 'adventure' },
  { label: '轻松休闲', value: 'relaxed' },
]

const routeFacts = [
  { label: '出发', value: '从一个目的地开始' },
  { label: '节奏', value: '按日拆分行程' },
  { label: '交付', value: '中文路线草案' },
]

const destinations = [
  {
    name: '京都',
    accent: '枫、茶庭、町屋',
    description: '适合把早晨留给庭院，把傍晚交给小巷与料理。',
    tags: ['人文', '秋季', '慢节奏'],
  },
  {
    name: '大理',
    accent: '风、洱海、院落',
    description: '在山海之间安排留白，让路线上有停顿，也有抵达。',
    tags: ['自然', '民宿', '松弛感'],
  },
  {
    name: '巴黎',
    accent: '左岸、画廊、晨咖啡',
    description: '用少量明确的坐标，串起一条不赶路的城市路线。',
    tags: ['艺术', '餐桌', '步行'],
  },
  {
    name: '冰岛',
    accent: '黑沙滩、温泉、极光',
    description: '把辽阔风景拆成可执行的动线，保留天气变化的余地。',
    tags: ['公路', '自然', '季节性'],
  },
]

const features = [
  {
    icon: Compass,
    title: '偏好成形',
    description: '把预算、月份、旅行风格和补充偏好收束成一条清晰路线。',
  },
  {
    icon: Route,
    title: '日程有呼吸',
    description: '每天按上午、下午、晚上展开，避免把旅程压成景点清单。',
  },
  {
    icon: MapPinned,
    title: '可继续讨论',
    description: '生成结果是一份中文草案，适合和同行者继续删改、补充、确认。',
  },
  {
    icon: ShieldCheck,
    title: '提醒不缺席',
    description: '保留交通、开放时间、天气等核对意识，让计划更接近真实出行。',
  },
]

const useCases = [
  {
    title: '还没定路线',
    description: '先得到一版骨架，再决定哪些城市、街区和体验值得留下。',
  },
  {
    title: '同行者很多',
    description: '用同一份草案讨论节奏、预算和偏好，减少反复沟通。',
  },
  {
    title: '出发前复盘',
    description: '按天检查路线密度和注意事项，把临行前的信息整理干净。',
  },
]

const manuscriptStops = [
  '一座城市的气质',
  '一天里的节奏',
  '值得绕路的餐桌',
  '出发前需要核对的事',
]

const form = reactive({
  destination: '京都',
  origin: '上海',
  days: 3,
  budget: 'medium' as BudgetLevel,
  travel_style: 'culture' as TravelStyle,
  month: '10月',
  notes: '喜欢慢节奏的早晨和本地美食。',
})

const plan = ref<TripPlanResponse | null>(null)
const error = ref('')
const isLoading = ref(false)

const canSubmit = computed(() => form.destination.trim().length > 0 && form.days >= 1 && !isLoading.value)
const destinationHasError = computed(() => error.value.length > 0 && form.destination.trim().length === 0)

async function createPlan() {
  if (!canSubmit.value) {
    error.value = '请填写目的地，并至少安排 1 天行程。'
    return
  }

  error.value = ''
  isLoading.value = true

  try {
    plan.value = await planTrip({
      destination: form.destination.trim(),
      origin: form.origin.trim(),
      days: Number(form.days),
      budget: form.budget,
      travel_style: form.travel_style,
      month: form.month.trim(),
      notes: form.notes.trim(),
    })
  } catch (caughtError) {
    plan.value = null
    error.value = caughtError instanceof Error ? caughtError.message : '规划器暂时无法生成行程。'
  } finally {
    isLoading.value = false
  }
}
</script>

<template>
  <main class="min-h-screen overflow-hidden bg-[#0b1012] text-[#f3ebdd] [font-family:Inter,'PingFang_SC','Microsoft_YaHei',sans-serif]">
    <div class="relative isolate">
      <div class="absolute inset-0 -z-20 bg-[radial-gradient(circle_at_16%_8%,rgba(123,156,141,0.24),transparent_28%),radial-gradient(circle_at_80%_2%,rgba(198,161,91,0.18),transparent_24%),linear-gradient(140deg,#0b1012_0%,#111917_48%,#07090a_100%)]" />
      <div class="absolute left-0 top-0 -z-10 h-full w-full bg-[linear-gradient(rgba(243,235,221,0.035)_1px,transparent_1px),linear-gradient(90deg,rgba(243,235,221,0.035)_1px,transparent_1px)] bg-[size:72px_72px] [mask-image:linear-gradient(to_bottom,black,transparent_88%)]" />
      <div class="absolute right-[-10rem] top-[30rem] -z-10 h-[30rem] w-[30rem] rounded-full bg-[#6e2c2c]/25 blur-3xl" />
      <div class="absolute left-[-12rem] top-[86rem] -z-10 h-[34rem] w-[34rem] rounded-full bg-[#7b9c8d]/20 blur-3xl" />

      <header class="mx-auto flex max-w-7xl items-center justify-between px-4 py-6 sm:px-6 lg:px-8" aria-label="主导航">
        <a href="#top" class="group inline-flex items-center gap-3 rounded-full border border-[#f3ebdd]/12 bg-[#f3ebdd]/8 px-4 py-2 text-sm font-semibold text-[#f3ebdd] shadow-2xl shadow-black/10 backdrop-blur-xl transition hover:border-[#c6a15b]/50 focus:outline-none focus:ring-2 focus:ring-[#c6a15b] focus:ring-offset-2 focus:ring-offset-[#0b1012]">
          <span class="flex h-8 w-8 items-center justify-center rounded-full bg-[#c6a15b] text-[#0b1012]">
            <Gem class="h-4 w-4" aria-hidden="true" />
          </span>
          <span>远行手稿</span>
        </a>

        <nav class="hidden items-center gap-7 text-sm text-[#cfc3ad] md:flex" aria-label="页面章节">
          <a class="transition hover:text-[#c6a15b] focus:outline-none focus:ring-2 focus:ring-[#c6a15b] focus:ring-offset-2 focus:ring-offset-[#0b1012]" href="#inspiration">目的地</a>
          <a class="transition hover:text-[#c6a15b] focus:outline-none focus:ring-2 focus:ring-[#c6a15b] focus:ring-offset-2 focus:ring-offset-[#0b1012]" href="#planner">写路线</a>
          <a class="transition hover:text-[#c6a15b] focus:outline-none focus:ring-2 focus:ring-[#c6a15b] focus:ring-offset-2 focus:ring-offset-[#0b1012]" href="#features">方法</a>
        </nav>

        <a href="#planner" class="inline-flex min-h-11 items-center gap-2 rounded-full bg-[#f3ebdd] px-5 py-2 text-sm font-bold text-[#0b1012] shadow-lg shadow-black/15 transition hover:-translate-y-0.5 hover:bg-[#d8bf86] focus:outline-none focus:ring-2 focus:ring-[#c6a15b] focus:ring-offset-2 focus:ring-offset-[#0b1012]">
          开始写路线
          <ArrowRight class="h-4 w-4" aria-hidden="true" />
        </a>
      </header>

      <section id="top" class="mx-auto grid max-w-7xl items-center gap-12 px-4 pb-20 pt-12 sm:px-6 sm:pt-16 lg:grid-cols-[0.92fr_1.08fr] lg:px-8 lg:pb-28">
        <div>
          <p class="inline-flex items-center rounded-full border border-[#c6a15b]/30 bg-[#c6a15b]/10 px-4 py-2 text-xs font-bold uppercase tracking-[0.34em] text-[#d8bf86] backdrop-blur-xl">
            私人行程工作室
          </p>
          <h1 class="mt-7 max-w-4xl text-5xl font-semibold leading-[0.96] tracking-[-0.08em] text-[#fff8ea] [font-family:'Noto_Serif_SC','Songti_SC',serif] sm:text-6xl lg:text-7xl">
            旅行不该像表格，应该像一份慢慢展开的手稿。
          </h1>
          <p class="mt-7 max-w-2xl text-base leading-8 text-[#cfc3ad] sm:text-lg">
            输入目的地、出发地、天数与偏好，先得到一版可讨论的中文路线。它不替你决定旅行，只把散落的想法整理成清楚的日程、节奏与提醒。
          </p>

          <div class="mt-10 flex flex-col gap-3 sm:flex-row">
            <a href="#planner" class="inline-flex min-h-12 items-center justify-center gap-2 rounded-full bg-[#c6a15b] px-7 py-3 font-bold text-[#0b1012] shadow-xl shadow-black/20 transition hover:-translate-y-0.5 hover:bg-[#e2c98e] focus:outline-none focus:ring-2 focus:ring-[#c6a15b] focus:ring-offset-2 focus:ring-offset-[#0b1012]">
              生成路线草案
              <ArrowRight class="h-4 w-4" aria-hidden="true" />
            </a>
            <a href="#inspiration" class="inline-flex min-h-12 items-center justify-center rounded-full border border-[#f3ebdd]/15 bg-[#f3ebdd]/8 px-7 py-3 font-bold text-[#f3ebdd] backdrop-blur-xl transition hover:-translate-y-0.5 hover:border-[#7b9c8d]/60 hover:bg-[#f3ebdd]/12 focus:outline-none focus:ring-2 focus:ring-[#7b9c8d] focus:ring-offset-2 focus:ring-offset-[#0b1012]">
              先看目的地气质
            </a>
          </div>

          <dl class="mt-10 grid gap-3 sm:grid-cols-3">
            <div v-for="fact in routeFacts" :key="fact.label" class="border-l border-[#c6a15b]/40 pl-4">
              <dt class="text-xs font-bold uppercase tracking-[0.28em] text-[#c6a15b]">{{ fact.label }}</dt>
              <dd class="mt-2 text-sm leading-6 text-[#d8d0bf]">{{ fact.value }}</dd>
            </div>
          </dl>
        </div>

        <div class="relative mx-auto w-full max-w-xl lg:max-w-none" aria-label="路线手稿示意">
          <div class="absolute -inset-6 rounded-[3rem] bg-[#c6a15b]/8 blur-3xl" />
          <div class="relative overflow-hidden rounded-[2.4rem] border border-[#f3ebdd]/14 bg-[#f3ebdd]/[0.075] p-4 shadow-[0_34px_120px_rgba(0,0,0,0.34)] backdrop-blur-2xl sm:p-6">
            <div class="absolute right-8 top-8 h-32 w-32 rounded-full border border-[#c6a15b]/20" />
            <div class="absolute right-14 top-14 h-20 w-20 rounded-full border border-[#c6a15b]/15" />
            <div class="rounded-[2rem] border border-[#f3ebdd]/12 bg-[#111917]/78 p-6 sm:p-8">
              <div class="flex items-start justify-between gap-5">
                <div>
                  <p class="text-xs font-bold uppercase tracking-[0.3em] text-[#7b9c8d]">Route Manuscript</p>
                  <h2 class="mt-3 text-3xl font-semibold tracking-[-0.05em] text-[#fff8ea] [font-family:'Noto_Serif_SC','Songti_SC',serif]">京都，十月。</h2>
                </div>
                <div class="flex h-12 w-12 items-center justify-center rounded-full border border-[#c6a15b]/40 bg-[#c6a15b]/12 text-[#d8bf86]">
                  <MapPinned class="h-5 w-5" aria-hidden="true" />
                </div>
              </div>

              <div class="mt-10 grid gap-7 sm:grid-cols-[0.72fr_1fr]">
                <div class="rounded-[1.6rem] border border-[#f3ebdd]/10 bg-[#f3ebdd]/7 p-5">
                  <p class="text-xs font-bold uppercase tracking-[0.26em] text-[#c6a15b]">偏好</p>
                  <p class="mt-4 text-sm leading-7 text-[#d8d0bf]">慢节奏早晨、本地餐桌、少一点奔波，多一点停留。</p>
                </div>
                <ol class="relative space-y-5 border-l border-[#c6a15b]/35 pl-6">
                  <li v-for="stop in manuscriptStops" :key="stop" class="relative text-sm leading-6 text-[#e7deca]">
                    <span class="absolute -left-[1.9rem] top-1.5 h-3 w-3 rounded-full border border-[#c6a15b] bg-[#111917]" />
                    {{ stop }}
                  </li>
                </ol>
              </div>

              <div class="mt-8 rounded-[1.7rem] border border-[#7b9c8d]/25 bg-[#7b9c8d]/10 p-5">
                <p class="text-xs font-bold uppercase tracking-[0.26em] text-[#91b5a5]">输出形式</p>
                <p class="mt-3 text-sm leading-7 text-[#d8d0bf]">每日主题、三段日程、补充备注和出发前提醒。</p>
              </div>
            </div>
          </div>
        </div>
      </section>

      <section id="inspiration" class="mx-auto max-w-7xl px-4 py-16 sm:px-6 lg:px-8">
        <div class="grid gap-6 md:grid-cols-[0.9fr_1.1fr] md:items-end">
          <div>
            <p class="text-xs font-bold uppercase tracking-[0.32em] text-[#c6a15b]">目的地气质</p>
            <h2 class="mt-4 max-w-2xl text-3xl font-semibold tracking-[-0.05em] text-[#fff8ea] [font-family:'Noto_Serif_SC','Songti_SC',serif] sm:text-5xl">先确定旅程的质地，再安排每一天。</h2>
          </div>
          <p class="max-w-xl text-sm leading-7 text-[#cfc3ad] sm:text-base">
            高级感不是堆满景点，而是知道哪里该停、哪里该绕路、哪里只需要一杯咖啡的时间。
          </p>
        </div>

        <div class="mt-10 grid gap-4 md:grid-cols-2 xl:grid-cols-4">
          <article v-for="destination in destinations" :key="destination.name" class="group rounded-[2rem] border border-[#f3ebdd]/12 bg-[#f3ebdd]/[0.07] p-5 shadow-2xl shadow-black/10 backdrop-blur-xl transition duration-300 hover:-translate-y-1 hover:border-[#c6a15b]/45 hover:bg-[#f3ebdd]/[0.095]">
            <p class="text-xs font-bold uppercase tracking-[0.22em] text-[#91b5a5]">{{ destination.accent }}</p>
            <h3 class="mt-5 text-3xl font-semibold tracking-[-0.05em] text-[#fff8ea] [font-family:'Noto_Serif_SC','Songti_SC',serif]">{{ destination.name }}</h3>
            <p class="mt-4 min-h-20 text-sm leading-7 text-[#d8d0bf]">{{ destination.description }}</p>
            <div class="mt-6 flex flex-wrap gap-2">
              <span v-for="tag in destination.tags" :key="tag" class="rounded-full border border-[#c6a15b]/22 bg-[#c6a15b]/10 px-3 py-1 text-xs font-semibold text-[#dcc793]">
                {{ tag }}
              </span>
            </div>
          </article>
        </div>
      </section>

      <section id="planner" class="mx-auto max-w-7xl px-4 py-16 sm:px-6 lg:px-8">
        <div class="mb-10 max-w-3xl">
          <p class="text-xs font-bold uppercase tracking-[0.32em] text-[#91b5a5]">写路线</p>
          <h2 class="mt-4 text-3xl font-semibold tracking-[-0.05em] text-[#fff8ea] [font-family:'Noto_Serif_SC','Songti_SC',serif] sm:text-5xl">把想法交给一张清楚的行程单。</h2>
          <p id="planner-helper" class="mt-5 text-base leading-8 text-[#cfc3ad]">
            这不是最终答案，而是一份可继续修改的初稿。先让路线有形，再决定删掉什么、保留什么。
          </p>
        </div>

        <div class="grid gap-6 lg:grid-cols-[0.9fr_1.1fr]">
          <form class="rounded-[2.25rem] border border-[#f3ebdd]/14 bg-[#f3ebdd]/[0.075] p-5 shadow-[0_28px_90px_rgba(0,0,0,0.25)] backdrop-blur-2xl sm:p-7" :aria-describedby="error ? 'planner-error' : 'planner-helper'" @submit.prevent="createPlan">
            <div class="mb-7 flex items-start justify-between gap-4">
              <div>
                <p class="text-xs font-bold uppercase tracking-[0.28em] text-[#c6a15b]">Route Brief</p>
                <h3 class="mt-2 text-2xl font-semibold tracking-[-0.04em] text-[#fff8ea] [font-family:'Noto_Serif_SC','Songti_SC',serif]">写下这次出发</h3>
              </div>
              <div class="hidden h-12 w-12 items-center justify-center rounded-full border border-[#c6a15b]/30 bg-[#c6a15b]/10 text-[#d8bf86] sm:flex">
                <Compass class="h-5 w-5" aria-hidden="true" />
              </div>
            </div>

            <div class="space-y-5">
              <label class="block">
                <span class="text-sm font-semibold text-[#f3ebdd]">目的地</span>
                <input
                  v-model="form.destination"
                  :aria-invalid="destinationHasError ? 'true' : undefined"
                  :aria-describedby="error ? 'planner-error' : undefined"
                  class="mt-2 min-h-12 w-full rounded-2xl border border-[#f3ebdd]/14 bg-[#080d0e]/65 px-4 py-3 text-[#fff8ea] outline-none ring-[#c6a15b]/35 transition placeholder:text-[#7f7769] focus:border-[#c6a15b]/60 focus:ring-4"
                  placeholder="京都"
                />
              </label>

              <div class="grid gap-4 sm:grid-cols-2">
                <label class="block">
                  <span class="text-sm font-semibold text-[#f3ebdd]">出发地</span>
                  <input
                    v-model="form.origin"
                    class="mt-2 min-h-12 w-full rounded-2xl border border-[#f3ebdd]/14 bg-[#080d0e]/65 px-4 py-3 text-[#fff8ea] outline-none ring-[#c6a15b]/35 transition placeholder:text-[#7f7769] focus:border-[#c6a15b]/60 focus:ring-4"
                    placeholder="上海"
                  />
                </label>

                <label class="block">
                  <span class="text-sm font-semibold text-[#f3ebdd]">旅行天数</span>
                  <input
                    v-model.number="form.days"
                    min="1"
                    max="14"
                    type="number"
                    class="mt-2 min-h-12 w-full rounded-2xl border border-[#f3ebdd]/14 bg-[#080d0e]/65 px-4 py-3 text-[#fff8ea] outline-none ring-[#c6a15b]/35 transition focus:border-[#c6a15b]/60 focus:ring-4"
                  />
                </label>
              </div>

              <div class="grid gap-4 sm:grid-cols-2">
                <label class="block">
                  <span class="text-sm font-semibold text-[#f3ebdd]">预算</span>
                  <select
                    v-model="form.budget"
                    class="mt-2 min-h-12 w-full rounded-2xl border border-[#f3ebdd]/14 bg-[#080d0e]/65 px-4 py-3 text-[#fff8ea] outline-none ring-[#c6a15b]/35 transition focus:border-[#c6a15b]/60 focus:ring-4"
                  >
                    <option v-for="option in budgetOptions" :key="option.value" :value="option.value" class="bg-[#0b1012] text-[#fff8ea]">
                      {{ option.label }}
                    </option>
                  </select>
                </label>

                <label class="block">
                  <span class="text-sm font-semibold text-[#f3ebdd]">旅行风格</span>
                  <select
                    v-model="form.travel_style"
                    class="mt-2 min-h-12 w-full rounded-2xl border border-[#f3ebdd]/14 bg-[#080d0e]/65 px-4 py-3 text-[#fff8ea] outline-none ring-[#c6a15b]/35 transition focus:border-[#c6a15b]/60 focus:ring-4"
                  >
                    <option v-for="option in styleOptions" :key="option.value" :value="option.value" class="bg-[#0b1012] text-[#fff8ea]">
                      {{ option.label }}
                    </option>
                  </select>
                </label>
              </div>

              <label class="block">
                <span class="text-sm font-semibold text-[#f3ebdd]">出行月份</span>
                <input
                  v-model="form.month"
                  class="mt-2 min-h-12 w-full rounded-2xl border border-[#f3ebdd]/14 bg-[#080d0e]/65 px-4 py-3 text-[#fff8ea] outline-none ring-[#c6a15b]/35 transition placeholder:text-[#7f7769] focus:border-[#c6a15b]/60 focus:ring-4"
                  placeholder="10月"
                />
              </label>

              <label class="block">
                <span class="text-sm font-semibold text-[#f3ebdd]">补充偏好</span>
                <textarea
                  v-model="form.notes"
                  rows="4"
                  class="mt-2 w-full rounded-2xl border border-[#f3ebdd]/14 bg-[#080d0e]/65 px-4 py-3 text-[#fff8ea] outline-none ring-[#c6a15b]/35 transition placeholder:text-[#7f7769] focus:border-[#c6a15b]/60 focus:ring-4"
                  placeholder="美食、节奏、必去地点、同行人情况等..."
                />
              </label>

              <p v-if="error" id="planner-error" class="rounded-2xl border border-[#d69a88]/40 bg-[#6e2c2c]/45 px-4 py-3 text-sm font-semibold leading-6 text-[#ffd9cf]" role="alert">
                {{ error }}
              </p>

              <button
                type="submit"
                :disabled="!canSubmit"
                class="inline-flex min-h-12 w-full items-center justify-center gap-2 rounded-2xl bg-[#c6a15b] px-5 py-3 font-black text-[#0b1012] shadow-lg shadow-black/20 transition hover:-translate-y-0.5 hover:bg-[#e2c98e] focus:outline-none focus:ring-2 focus:ring-[#c6a15b] focus:ring-offset-2 focus:ring-offset-[#0b1012] disabled:cursor-not-allowed disabled:opacity-50 disabled:hover:translate-y-0"
              >
                {{ isLoading ? '正在整理路线…' : '生成路线草案' }}
                <ArrowRight class="h-4 w-4" aria-hidden="true" />
              </button>
            </div>
          </form>

          <aside class="rounded-[2.25rem] border border-[#f3ebdd]/14 bg-[#080d0e]/58 p-4 shadow-[0_28px_90px_rgba(0,0,0,0.28)] backdrop-blur-2xl sm:p-6" aria-live="polite" :aria-busy="isLoading">
            <div class="rounded-[1.8rem] border border-[#f3ebdd]/10 bg-[#f3ebdd]/[0.055] p-5 sm:p-6">
              <div class="flex items-start justify-between gap-4">
                <div>
                  <p class="text-xs font-bold uppercase tracking-[0.28em] text-[#91b5a5]">Route Draft</p>
                  <h3 class="mt-2 text-2xl font-semibold tracking-[-0.04em] text-[#fff8ea] [font-family:'Noto_Serif_SC','Songti_SC',serif]">路线草案</h3>
                </div>
                <div class="flex h-12 w-12 items-center justify-center rounded-full border border-[#7b9c8d]/30 bg-[#7b9c8d]/12 text-[#91b5a5]">
                  <Route class="h-5 w-5" aria-hidden="true" />
                </div>
              </div>

              <div v-if="!plan" class="mt-8 rounded-[2rem] border border-dashed border-[#7b9c8d]/35 bg-[linear-gradient(135deg,rgba(123,156,141,0.12),rgba(243,235,221,0.045))] p-6">
                <p class="text-2xl font-semibold tracking-[-0.04em] text-[#fff8ea] [font-family:'Noto_Serif_SC','Songti_SC',serif]">还没有路线草案。</p>
                <p class="mt-3 leading-7 text-[#d8d0bf]">
                  填写左侧信息后，这里会出现按天整理的上午、下午、晚上安排，以及需要出发前核对的提醒。
                </p>
                <div class="mt-6 grid gap-3 sm:grid-cols-3">
                  <div class="rounded-2xl bg-[#f3ebdd]/8 p-4">
                    <p class="text-xs font-bold text-[#c6a15b]">上午</p>
                    <p class="mt-2 text-sm text-[#d8d0bf]">轻一点开始</p>
                  </div>
                  <div class="rounded-2xl bg-[#f3ebdd]/8 p-4">
                    <p class="text-xs font-bold text-[#c6a15b]">下午</p>
                    <p class="mt-2 text-sm text-[#d8d0bf]">安排重点</p>
                  </div>
                  <div class="rounded-2xl bg-[#f3ebdd]/8 p-4">
                    <p class="text-xs font-bold text-[#c6a15b]">晚上</p>
                    <p class="mt-2 text-sm text-[#d8d0bf]">留给回味</p>
                  </div>
                </div>
              </div>

              <div v-else class="mt-8 space-y-5">
                <div class="rounded-[2rem] border border-[#c6a15b]/25 bg-[#c6a15b]/10 p-5">
                  <p class="text-sm font-bold uppercase tracking-[0.22em] text-[#d8bf86]">{{ plan.trip_id }}</p>
                  <h2 class="mt-2 text-3xl font-semibold tracking-[-0.05em] text-[#fff8ea] [font-family:'Noto_Serif_SC','Songti_SC',serif]">{{ plan.destination }}</h2>
                  <p class="mt-3 leading-7 text-[#f0e4cf]">{{ plan.summary }}</p>
                </div>

                <article v-for="day in plan.days" :key="day.day" class="rounded-[1.7rem] border border-[#f3ebdd]/10 bg-[#f3ebdd]/[0.065] p-5">
                  <div class="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
                    <div>
                      <p class="text-xs font-bold uppercase tracking-[0.25em] text-[#91b5a5]">第 {{ day.day }} 天</p>
                      <h3 class="mt-1 text-xl font-semibold text-[#fff8ea] [font-family:'Noto_Serif_SC','Songti_SC',serif]">{{ day.title }}</h3>
                    </div>
                    <span class="w-fit rounded-full border border-[#c6a15b]/30 bg-[#c6a15b]/12 px-3 py-1 text-xs font-bold text-[#dcc793]">
                      {{ day.theme }}
                    </span>
                  </div>

                  <dl class="mt-5 space-y-4 text-sm leading-6 text-[#d8d0bf]">
                    <div class="rounded-2xl bg-[#080d0e]/42 p-4">
                      <dt class="font-bold text-[#fff8ea]">上午</dt>
                      <dd class="mt-1">{{ day.morning }}</dd>
                    </div>
                    <div class="rounded-2xl bg-[#080d0e]/42 p-4">
                      <dt class="font-bold text-[#fff8ea]">下午</dt>
                      <dd class="mt-1">{{ day.afternoon }}</dd>
                    </div>
                    <div class="rounded-2xl bg-[#080d0e]/42 p-4">
                      <dt class="font-bold text-[#fff8ea]">晚上</dt>
                      <dd class="mt-1">{{ day.evening }}</dd>
                    </div>
                  </dl>

                  <ul class="mt-4 list-disc space-y-1 pl-5 text-sm leading-6 text-[#cfc3ad]">
                    <li v-for="note in day.notes" :key="note">{{ note }}</li>
                  </ul>
                </article>

                <div class="rounded-[1.7rem] border border-[#7b9c8d]/24 bg-[#7b9c8d]/10 p-5">
                  <h3 class="font-bold text-[#fff8ea]">出发前提醒</h3>
                  <ul class="mt-3 list-disc space-y-2 pl-5 text-sm leading-6 text-[#d8d0bf]">
                    <li v-for="tip in plan.tips" :key="tip">{{ tip }}</li>
                  </ul>
                  <p class="mt-4 border-t border-[#f3ebdd]/10 pt-4 text-xs font-semibold uppercase tracking-[0.18em] text-[#afa58f]">
                    {{ plan.disclaimer }}
                  </p>
                </div>
              </div>
            </div>
          </aside>
        </div>
      </section>

      <section id="features" class="mx-auto max-w-7xl px-4 py-16 sm:px-6 lg:px-8">
        <div class="max-w-3xl">
          <p class="text-xs font-bold uppercase tracking-[0.32em] text-[#c6a15b]">方法</p>
          <h2 class="mt-4 text-3xl font-semibold tracking-[-0.05em] text-[#fff8ea] [font-family:'Noto_Serif_SC','Songti_SC',serif] sm:text-5xl">一份好路线，需要四个层次。</h2>
        </div>

        <div class="mt-10 grid gap-4 md:grid-cols-2 lg:grid-cols-4">
          <article v-for="feature in features" :key="feature.title" class="rounded-[2rem] border border-[#f3ebdd]/12 bg-[#f3ebdd]/[0.07] p-6 backdrop-blur-xl transition duration-300 hover:-translate-y-1 hover:border-[#7b9c8d]/45 hover:bg-[#f3ebdd]/[0.095]">
            <div class="flex h-12 w-12 items-center justify-center rounded-full border border-[#c6a15b]/25 bg-[#c6a15b]/10 text-[#d8bf86]">
              <component :is="feature.icon" class="h-5 w-5" aria-hidden="true" />
            </div>
            <h3 class="mt-6 text-xl font-semibold text-[#fff8ea] [font-family:'Noto_Serif_SC','Songti_SC',serif]">{{ feature.title }}</h3>
            <p class="mt-3 text-sm leading-7 text-[#d8d0bf]">{{ feature.description }}</p>
          </article>
        </div>
      </section>

      <section class="mx-auto max-w-7xl px-4 py-16 sm:px-6 lg:px-8">
        <div class="rounded-[2.5rem] border border-[#f3ebdd]/14 bg-[#f3ebdd]/[0.07] p-6 shadow-[0_28px_90px_rgba(0,0,0,0.24)] backdrop-blur-2xl sm:p-8 lg:p-10">
          <div class="grid gap-8 lg:grid-cols-[0.82fr_1.18fr] lg:items-center">
            <div>
              <p class="text-xs font-bold uppercase tracking-[0.32em] text-[#91b5a5]">适用场景</p>
              <h2 class="mt-4 text-3xl font-semibold tracking-[-0.05em] text-[#fff8ea] [font-family:'Noto_Serif_SC','Songti_SC',serif] sm:text-5xl">它适合在决定之前使用。</h2>
            </div>
            <div class="grid gap-4 md:grid-cols-3">
              <article v-for="useCase in useCases" :key="useCase.title" class="rounded-[1.6rem] border border-[#f3ebdd]/10 bg-[#080d0e]/42 p-5">
                <h3 class="font-semibold text-[#fff8ea] [font-family:'Noto_Serif_SC','Songti_SC',serif]">{{ useCase.title }}</h3>
                <p class="mt-3 text-sm leading-7 text-[#d8d0bf]">{{ useCase.description }}</p>
              </article>
            </div>
          </div>
        </div>
      </section>

      <section class="mx-auto max-w-5xl px-4 py-20 text-center sm:px-6 lg:px-8">
        <p class="text-xs font-bold uppercase tracking-[0.32em] text-[#c6a15b]">从一座城市开始</p>
        <h2 class="mt-4 text-4xl font-semibold tracking-[-0.06em] text-[#fff8ea] [font-family:'Noto_Serif_SC','Songti_SC',serif] sm:text-6xl">先写一版路线，再慢慢删改。</h2>
        <p class="mx-auto mt-5 max-w-2xl text-base leading-8 text-[#cfc3ad]">
          旅行计划最难的是开始。把目的地写下来，让第一版日程先出现。
        </p>
        <a href="#planner" class="mt-9 inline-flex min-h-12 items-center justify-center gap-2 rounded-full bg-[#c6a15b] px-8 py-3 font-black text-[#0b1012] shadow-xl shadow-black/20 transition hover:-translate-y-0.5 hover:bg-[#e2c98e] focus:outline-none focus:ring-2 focus:ring-[#c6a15b] focus:ring-offset-2 focus:ring-offset-[#0b1012]">
          开始写路线
          <ArrowRight class="h-4 w-4" aria-hidden="true" />
        </a>
      </section>
    </div>
  </main>
</template>
