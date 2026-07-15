<script setup lang="ts">
import { computed, onMounted, reactive, ref, watch } from 'vue'
import { useRouter } from 'vue-router'
import { ArrowRight, CalendarDays, CheckCircle2, Compass, MapPinned, Route, Sparkles } from 'lucide-vue-next'

import TripPlanResult from '@/components/TripPlanResult.vue'
import { getAuthTokens, logout, planTripStream } from '@/services'
import type { TravelStyle, TripPlanResponse } from '@/types'

const styleOptions: Array<{ label: string; value: TravelStyle }> = [
  { label: '人文历史', value: 'culture' },
  { label: '本地美食', value: 'food' },
  { label: '自然风景', value: 'nature' },
  { label: '亲子友好', value: 'family' },
  { label: '浪漫慢游', value: 'romantic' },
  { label: '探索冒险', value: 'adventure' },
  { label: '轻松休闲', value: 'relaxed' },
]

const destinations = [
  { name: '京都', accent: '人文 / 秋季', description: '庭院、町屋和本地料理排成一条慢路线。', tint: 'bg-[#ffe8d4]' },
  { name: '大理', accent: '自然 / 民宿', description: '把洱海、古城和留白时间放在同一张行程里。', tint: 'bg-[#d9f3e1]' },
  { name: '巴黎', accent: '艺术 / 步行', description: '用清楚坐标串起左岸、画廊和晨咖啡。', tint: 'bg-[#fde0ec]' },
  { name: '冰岛', accent: '公路 / 季节', description: '给天气、温泉和远距离交通留出弹性。', tint: 'bg-[#dcecfa]' },
]

const features = [
  { icon: Compass, title: '偏好成形', description: '预算、日期、旅行风格和补充偏好先收束成一条路线。' },
  { icon: CalendarDays, title: '按日展开', description: '每天按具体时间点展开，避免只得到景点清单。' },
  { icon: Route, title: '动线清楚', description: '围绕相邻区域安排重点，减少无意义往返。' },
  { icon: CheckCircle2, title: '提醒完整', description: '保留交通、预约、天气和开放时间的核对意识。' },
]

const form = reactive({
  destination: '北京',
  origin: '上海',
  days: 1,
  budget: '5000',
  travel_style: ['culture'] as TravelStyle[],
  start_date: todayIso(),
  end_date: todayIso(),
  notes: '喜欢慢节奏的早晨和本地美食。',
})

const plan = ref<TripPlanResponse | null>(null)
const error = ref('')
const isLoading = ref(false)
const streamMessage = ref('')
const streamSteps = ref<string[]>([])
const dateWarning = ref('')
const saveMessage = ref('')
const isLoggedIn = ref(false)
const router = useRouter()

const maxEndDate = computed(() => addDays(form.start_date, 9))
const canSubmit = computed(() => form.destination.trim().length > 0 && form.days >= 1 && form.days <= 10 && form.travel_style.length > 0 && !isLoading.value)
const destinationHasError = computed(() => error.value.length > 0 && form.destination.trim().length === 0)
const selectedStyleLabels = computed(() => styleOptions.filter((option) => form.travel_style.includes(option.value)).map((option) => option.label).join('、'))

watch(
  () => [form.start_date, form.end_date],
  () => {
    const selectedDays = getTripDays(form.start_date, form.end_date)
    form.days = selectedDays
    if (selectedDays > 10) {
      dateWarning.value = '最多只能选择 10 天行程。'
      form.end_date = maxEndDate.value
      return
    }
    dateWarning.value = ''
  },
)

watch(
  () => form.days,
  () => {
    if (form.days < 1) form.days = 1
    if (form.days > 10) {
      form.days = 10
      dateWarning.value = '最多只能选择 10 天行程。'
    }
    form.end_date = addDays(form.start_date, form.days - 1)
  },
)

async function createPlan() {
  if (!canSubmit.value) {
    error.value = '请填写目的地，并至少安排 1 天行程。'
    return
  }

  error.value = ''
  saveMessage.value = ''
  isLoading.value = true
  plan.value = null
  streamMessage.value = '正在启动路线规划...'
  streamSteps.value = []

  try {
    const payload = {
      destination: form.destination.trim(),
      origin: form.origin.trim(),
      days: form.days,
      budget: form.budget,
      travel_style: form.travel_style,
      start_date: form.start_date,
      end_date: form.end_date,
      notes: form.notes.trim(),
    }

    plan.value = await planTripStream(payload, (event) => {
      if (event.type === 'status' && event.message) {
        streamMessage.value = event.message
        streamSteps.value = [...streamSteps.value, event.message]
      }
    })
    saveMessage.value = '已保存到工作台。'
  } catch (caughtError) {
    plan.value = null
    error.value = caughtError instanceof Error ? caughtError.message : '规划器暂时无法生成行程。'
  } finally {
    isLoading.value = false
    streamMessage.value = ''
  }
}

async function logoutAndReturn() {
  await logout()
  isLoggedIn.value = false
  await router.push('/login')
}

onMounted(() => {
  isLoggedIn.value = getAuthTokens() !== null
})

function showDateLimitHint() {
  dateWarning.value = '最多只能选择 10 天行程。'
}

function toggleTravelStyle(style: TravelStyle) {
  if (form.travel_style.includes(style)) {
    if (form.travel_style.length > 1) {
      form.travel_style = form.travel_style.filter((item) => item !== style)
    }
    return
  }
  form.travel_style = [...form.travel_style, style]
}

function getTripDays(start: string, end: string): number {
  if (!start || !end) return 0
  const startDate = new Date(`${start}T00:00:00`)
  const endDate = new Date(`${end}T00:00:00`)
  return Math.floor((endDate.getTime() - startDate.getTime()) / 86400000) + 1
}

function todayIso(): string {
  return new Date().toISOString().slice(0, 10)
}

function addDays(value: string, days: number): string {
  if (!value) return ''
  const date = new Date(`${value}T00:00:00`)
  date.setDate(date.getDate() + days)
  return date.toISOString().slice(0, 10)
}
</script>

<template>
  <main class="min-h-screen bg-white text-[#1a1a1a] [font-family:Inter,-apple-system,BlinkMacSystemFont,'Segoe_UI','PingFang_SC','Microsoft_YaHei',sans-serif]">
    <header class="sticky top-0 z-30 border-b border-[#e5e3df] bg-white/90 backdrop-blur">
      <div class="mx-auto flex max-w-7xl items-center justify-between gap-4 px-4 py-3 sm:px-6 lg:px-8">
        <a href="#top" class="flex items-center gap-2 text-sm font-semibold text-[#000000]">
          <span class="grid h-8 w-8 place-items-center rounded-md bg-[#0a1530] text-white">
            <MapPinned class="h-4 w-4" aria-hidden="true" />
          </span>
          远行手稿
        </a>

        <nav class="hidden items-center gap-6 text-sm font-medium text-[#5d5b54] md:flex" aria-label="页面章节">
          <a class="hover:text-[#000000]" href="#destinations">目的地</a>
          <a class="hover:text-[#000000]" href="#planner">规划器</a>
          <a class="hover:text-[#000000]" href="#features">方法</a>
        </nav>

        <div class="flex items-center gap-2">
          <RouterLink
            v-if="isLoggedIn"
            to="/workspace"
            class="rounded-md border border-[#c8c4be] px-3 py-2 text-sm font-medium hover:bg-[#f6f5f4]"
          >
            工作台
          </RouterLink>
          <button
            v-if="isLoggedIn"
            type="button"
            class="rounded-md border border-[#c8c4be] px-3 py-2 text-sm font-medium hover:bg-[#f6f5f4]"
            @click="logoutAndReturn"
          >
            退出登录
          </button>
          <RouterLink v-else to="/login" class="rounded-md border border-[#c8c4be] px-3 py-2 text-sm font-medium hover:bg-[#f6f5f4]">
            登录
          </RouterLink>
          <a href="#planner" class="rounded-md bg-[#5645d4] px-3 py-2 text-sm font-medium text-white hover:bg-[#4534b3]">
            开始规划
          </a>
        </div>
      </div>
    </header>

    <section id="top" class="relative overflow-hidden bg-[#0a1530] text-white">
      <div class="absolute left-[8%] top-16 h-9 w-9 rotate-6 rounded-md bg-[#f5d75e]" aria-hidden="true" />
      <div class="absolute right-[18%] top-24 h-7 w-7 -rotate-12 rounded-md bg-[#ff64c8]" aria-hidden="true" />
      <div class="absolute bottom-16 left-[18%] h-6 w-6 rotate-12 rounded-md bg-[#2a9d99]" aria-hidden="true" />
      <div class="absolute bottom-28 right-[10%] h-8 w-8 -rotate-6 rounded-md bg-[#dd5b00]" aria-hidden="true" />

      <div class="mx-auto grid max-w-7xl gap-10 px-4 py-16 sm:px-6 lg:grid-cols-[0.9fr_1.1fr] lg:px-8 lg:py-24">
        <div class="self-center">
          <p class="mb-5 inline-flex rounded-md bg-white/10 px-3 py-1 text-xs font-semibold text-[#d6b6f6]">
            智能旅行工作台
          </p>
          <h1 class="max-w-3xl text-5xl font-semibold leading-tight sm:text-6xl lg:text-7xl">
            把旅行想法整理成可执行的日程。
          </h1>
          <p class="mt-6 max-w-2xl text-lg leading-8 text-[#d9d7d2]">
            输入目的地、天数、预算和偏好，生成一版中文路线草案。先得到骨架，再和同行者一起删改。
          </p>
          <div class="mt-8 flex flex-col gap-3 sm:flex-row">
            <a href="#planner" class="inline-flex min-h-11 items-center justify-center gap-2 rounded-md bg-[#5645d4] px-5 py-3 text-sm font-medium text-white hover:bg-[#4534b3]">
              生成路线草案
              <ArrowRight class="h-4 w-4" aria-hidden="true" />
            </a>
            <a href="#destinations" class="inline-flex min-h-11 items-center justify-center rounded-md border border-white/40 px-5 py-3 text-sm font-medium text-white hover:bg-white/10">
              查看示例目的地
            </a>
          </div>
        </div>

        <div class="rounded-xl border border-[#e5e3df] bg-white text-[#1a1a1a] shadow-2xl shadow-black/30">
          <div class="flex items-center justify-between border-b border-[#e5e3df] px-4 py-3">
            <div class="flex gap-1.5" aria-hidden="true">
              <span class="h-3 w-3 rounded-full bg-[#ff64c8]" />
              <span class="h-3 w-3 rounded-full bg-[#f5d75e]" />
              <span class="h-3 w-3 rounded-full bg-[#1aae39]" />
            </div>
            <p class="text-xs font-semibold text-[#787671]">路线工作台</p>
          </div>

          <div class="grid gap-4 p-4 sm:grid-cols-[0.8fr_1.2fr]">
            <aside class="rounded-lg bg-[#f6f5f4] p-4">
              <p class="text-xs font-semibold text-[#787671]">出行摘要</p>
              <h2 class="mt-2 text-2xl font-semibold">北京，10月</h2>
              <div class="mt-5 space-y-2 text-sm">
                <p class="rounded-md bg-[#e6e0f5] px-3 py-2 text-[#391c57]">人文历史</p>
                <p class="rounded-md bg-[#ffe8d4] px-3 py-2 text-[#793400]">本地美食</p>
                <p class="rounded-md bg-[#d9f3e1] px-3 py-2 text-[#1a1a1a]">慢节奏早晨</p>
              </div>
            </aside>

            <div class="space-y-3">
              <div class="rounded-lg border border-[#e5e3df] p-4">
                <div class="mb-3 flex items-center justify-between">
                  <p class="font-semibold">第 1 天 · 轻松适应</p>
                  <span class="rounded bg-[#fef7d6] px-2 py-1 text-xs font-semibold">具体时间点</span>
                </div>
                <div class="space-y-2 text-sm text-[#5d5b54]">
                  <p class="rounded-md bg-[#fafaf9] px-3 py-2">办理入住，熟悉周边环境</p>
                  <p class="rounded-md bg-[#fafaf9] px-3 py-2">慢逛历史街区和茶庭</p>
                  <p class="rounded-md bg-[#fafaf9] px-3 py-2">住处附近安排晚餐</p>
                </div>
              </div>
              <div class="grid gap-3 sm:grid-cols-2">
                <div class="rounded-lg bg-[#dcecfa] p-4">
                  <p class="text-sm font-semibold">交通提醒</p>
                  <p class="mt-2 text-sm text-[#37352f]">同一天尽量少跨区。</p>
                </div>
                <div class="rounded-lg bg-[#fde0ec] p-4">
                  <p class="text-sm font-semibold">预约提醒</p>
                  <p class="mt-2 text-sm text-[#37352f]">出发前核对开放时间。</p>
                </div>
              </div>
            </div>
          </div>
        </div>
      </div>
    </section>

    <section id="destinations" class="mx-auto max-w-7xl px-4 py-16 sm:px-6 lg:px-8">
      <div class="mb-8 flex flex-col justify-between gap-4 md:flex-row md:items-end">
        <div>
          <p class="text-xs font-semibold uppercase text-[#5645d4]">目的地灵感</p>
          <h2 class="mt-3 text-4xl font-semibold leading-tight">先选旅程的质地。</h2>
        </div>
        <p class="max-w-xl text-base leading-7 text-[#5d5b54]">
          页面不再堆装饰，把目的地灵感、规划表单和生成结果放在同一条清楚路径上。
        </p>
      </div>

      <div class="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
        <article v-for="destination in destinations" :key="destination.name" class="rounded-xl border border-[#e5e3df] p-5" :class="destination.tint">
          <p class="text-xs font-semibold text-[#5d5b54]">{{ destination.accent }}</p>
          <h3 class="mt-4 text-3xl font-semibold">{{ destination.name }}</h3>
          <p class="mt-4 text-sm leading-6 text-[#37352f]">{{ destination.description }}</p>
        </article>
      </div>
    </section>

    <section id="planner" class="bg-[#f6f5f4] px-4 py-16 sm:px-6 lg:px-8">
      <div class="mx-auto max-w-7xl">
        <div class="mb-8 max-w-3xl">
          <p class="text-xs font-semibold uppercase text-[#5645d4]">行程规划</p>
          <h2 class="mt-3 text-4xl font-semibold leading-tight">把想法交给一张清楚的行程单。</h2>
          <p id="planner-helper" class="mt-4 text-base leading-7 text-[#5d5b54]">
            保留原来的生成能力，只把表单和结果区改成更像工作台的双栏布局。
          </p>
        </div>

        <div class="grid items-stretch gap-6 lg:grid-cols-[360px_minmax(0,1fr)]">
          <form class="rounded-xl border border-[#e5e3df] bg-white p-4 lg:sticky lg:top-24 lg:self-start" :aria-describedby="error ? 'planner-error' : 'planner-helper'" @submit.prevent="createPlan">
            <div class="mb-4 flex items-center justify-between gap-4">
              <div>
                <p class="text-xs font-semibold text-[#787671]">出行摘要</p>
                <h3 class="mt-1 text-xl font-semibold">这次出发</h3>
              </div>
              <Sparkles class="h-6 w-6 text-[#5645d4]" aria-hidden="true" />
            </div>

            <div class="space-y-3">
              <label class="block">
                <span class="text-sm font-medium">目的地</span>
                <input
                  v-model="form.destination"
                  :aria-invalid="destinationHasError ? 'true' : undefined"
                  :aria-describedby="error ? 'planner-error' : undefined"
                  class="mt-1.5 h-10 w-full rounded-md border border-[#c8c4be] bg-white px-3 text-base outline-none focus:border-[#5645d4] focus:ring-2 focus:ring-[#d6b6f6]"
                  placeholder="京都"
                />
              </label>

              <div class="grid gap-3 sm:grid-cols-2">
                <label class="block">
                  <span class="text-sm font-medium">出发地</span>
                  <input v-model="form.origin" class="mt-1.5 h-10 w-full rounded-md border border-[#c8c4be] bg-white px-3 text-base outline-none focus:border-[#5645d4] focus:ring-2 focus:ring-[#d6b6f6]" placeholder="上海" />
                </label>

                <div class="block">
                  <span class="text-sm font-medium">旅行天数</span>
                  <input v-model.number="form.days" type="number" min="1" max="10" class="mt-1.5 h-10 w-full rounded-md border border-[#c8c4be] bg-white px-3 text-base outline-none focus:border-[#5645d4] focus:ring-2 focus:ring-[#d6b6f6]" />
                </div>
              </div>

              <div class="grid gap-3 sm:grid-cols-2">
                <label class="block">
                  <span class="text-sm font-medium">预算</span>
                  <div class="mt-1.5 flex h-10 overflow-hidden rounded-md border border-[#c8c4be] bg-white focus-within:border-[#5645d4] focus-within:ring-2 focus-within:ring-[#d6b6f6]">
                    <span class="grid w-10 place-items-center border-r border-[#e5e3df] text-sm font-semibold text-[#5d5b54]">¥</span>
                    <input v-model="form.budget" inputmode="numeric" class="min-w-0 flex-1 px-3 text-base outline-none" placeholder="5000" />
                  </div>
                </label>

                <div class="block">
                  <span class="text-sm font-medium">旅行风格</span>
                  <details class="group relative mt-1.5">
                    <summary class="flex h-10 cursor-pointer list-none items-center justify-between rounded-md border border-[#c8c4be] bg-white px-3 text-base outline-none group-open:border-[#5645d4] group-open:ring-2 group-open:ring-[#d6b6f6]">
                      <span class="truncate">{{ selectedStyleLabels }}</span>
                      <span class="text-xs text-[#787671]">▾</span>
                    </summary>
                    <div class="absolute z-20 mt-1 grid w-full gap-1 rounded-md border border-[#c8c4be] bg-white p-2 shadow-lg">
                      <label v-for="option in styleOptions" :key="option.value" class="flex cursor-pointer items-center gap-2 rounded px-2 py-1.5 text-sm hover:bg-[#fafaf9]">
                        <input
                          type="checkbox"
                          class="h-4 w-4 accent-[#5645d4]"
                          :checked="form.travel_style.includes(option.value)"
                          @change="toggleTravelStyle(option.value)"
                        />
                        {{ option.label }}
                      </label>
                    </div>
                  </details>
                </div>
              </div>

              <div class="block">
                <span class="text-sm font-medium">出行日期</span>
                <div class="mt-1.5 grid gap-2 sm:grid-cols-2">
                  <input v-model="form.start_date" type="date" class="h-10 w-full rounded-md border border-[#c8c4be] bg-white px-3 text-sm outline-none focus:border-[#5645d4] focus:ring-2 focus:ring-[#d6b6f6]" />
                  <input
                    v-model="form.end_date"
                    type="date"
                    :min="form.start_date"
                    :max="maxEndDate"
                    class="h-10 w-full rounded-md border border-[#c8c4be] bg-white px-3 text-sm outline-none focus:border-[#5645d4] focus:ring-2 focus:ring-[#d6b6f6]"
                    @mouseenter="showDateLimitHint"
                    @focus="showDateLimitHint"
                    @click="showDateLimitHint"
                  />
                </div>
                <p class="mt-1.5 text-xs font-medium" :class="dateWarning ? 'text-[#a02e6d]' : 'text-[#787671]'">
                  {{ dateWarning || `结束日期最多可选到 ${maxEndDate}` }}
                </p>
              </div>

              <label class="block">
                <span class="text-sm font-medium">补充偏好</span>
                <textarea v-model="form.notes" rows="2" class="mt-1.5 w-full rounded-md border border-[#c8c4be] bg-white px-3 py-2 text-base outline-none focus:border-[#5645d4] focus:ring-2 focus:ring-[#d6b6f6]" placeholder="美食、节奏、必去地点、同行人情况等..." />
              </label>

              <p v-if="error" id="planner-error" class="rounded-md border border-[#e03131]/30 bg-[#fde0ec] px-3 py-2 text-sm font-medium text-[#a02e6d]" role="alert">
                {{ error }}
              </p>

              <button type="submit" :disabled="!canSubmit" class="inline-flex min-h-10 w-full items-center justify-center gap-2 rounded-md bg-[#5645d4] px-5 py-2.5 text-sm font-medium text-white hover:bg-[#4534b3] disabled:cursor-not-allowed disabled:bg-[#e5e3df] disabled:text-[#bbb8b1]">
                {{ isLoading ? '正在整理路线...' : '生成路线草案' }}
                <ArrowRight class="h-4 w-4" aria-hidden="true" />
              </button>
            </div>
          </form>

          <aside class="min-h-0 rounded-xl border border-[#e5e3df] bg-white p-5 sm:p-6 lg:h-full lg:overflow-y-auto" aria-live="polite" :aria-busy="isLoading">
            <div class="mb-5 flex items-center justify-between gap-4">
              <div>
                <p class="text-xs font-semibold text-[#787671]">路线草案</p>
                <h3 class="mt-1 text-2xl font-semibold">路线草案</h3>
              </div>
              <Route class="h-6 w-6 text-[#5645d4]" aria-hidden="true" />
            </div>

            <div v-if="isLoading" class="overflow-hidden rounded-xl border border-[#d6b6f6] bg-[#fafaf9]">
              <div class="grid gap-5 p-5 md:grid-cols-[180px_minmax(0,1fr)] sm:p-6">
                <div class="relative min-h-36 rounded-xl bg-[#0a1530] p-4 text-white">
                  <div class="absolute right-4 top-4 h-2 w-2 animate-ping rounded-full bg-[#1aae39]" aria-hidden="true" />
                  <div class="grid h-12 w-12 place-items-center rounded-full bg-white/10">
                    <div class="h-5 w-5 animate-pulse rounded-full bg-[#f5d75e]" aria-hidden="true" />
                  </div>
                  <p class="mt-5 text-xs font-semibold text-[#d6b6f6]">智能规划中</p>
                  <p class="mt-2 text-xl font-semibold leading-tight">路线正在成形</p>
                  <div class="mt-5 flex gap-1.5" aria-hidden="true">
                    <span class="h-1.5 w-8 animate-pulse rounded-full bg-[#ff64c8]" />
                    <span class="h-1.5 w-5 animate-pulse rounded-full bg-[#f5d75e] [animation-delay:120ms]" />
                    <span class="h-1.5 w-7 animate-pulse rounded-full bg-[#1aae39] [animation-delay:240ms]" />
                  </div>
                </div>

                <div class="min-w-0">
                  <h4 class="text-2xl font-semibold">正在生成路线草案</h4>
                  <p class="mt-2 leading-7 text-[#5d5b54]">{{ streamMessage || '正在整理信息...' }}</p>

                  <ol class="mt-5 space-y-3">
                    <li
                      v-for="(step, index) in streamSteps"
                      :key="`${step}-${index}`"
                      class="grid grid-cols-[24px_minmax(0,1fr)] gap-3"
                    >
                      <span
                        class="mt-0.5 grid h-6 w-6 place-items-center rounded-full text-xs font-semibold"
                        :class="index === streamSteps.length - 1 ? 'bg-[#5645d4] text-white' : 'bg-[#d9f3e1] text-[#1a1a1a]'"
                      >
                        {{ index + 1 }}
                      </span>
                      <span
                        class="rounded-lg border px-3 py-2 text-sm font-medium"
                        :class="index === streamSteps.length - 1 ? 'border-[#d6b6f6] bg-[#e6e0f5] text-[#391c57]' : 'border-[#e5e3df] bg-white text-[#5d5b54]'"
                      >
                        {{ step }}
                      </span>
                    </li>
                    <li v-if="streamSteps.length === 0" class="grid grid-cols-[24px_minmax(0,1fr)] gap-3">
                      <span class="mt-0.5 h-6 w-6 animate-pulse rounded-full bg-[#5645d4]" />
                      <span class="rounded-lg border border-[#e5e3df] bg-white px-3 py-2 text-sm font-medium text-[#5d5b54]">
                        正在连接规划服务...
                      </span>
                    </li>
                  </ol>
                </div>
              </div>

              <div class="grid gap-3 border-t border-[#e5e3df] bg-white/70 p-5 sm:p-6 lg:grid-cols-[1.1fr_0.9fr]">
                <div class="rounded-xl bg-[#f9e79f] p-4">
                  <div class="h-3 w-20 animate-pulse rounded-full bg-[#523410]/20" />
                  <div class="mt-4 h-7 w-36 animate-pulse rounded-full bg-[#523410]/25" />
                  <div class="mt-4 space-y-2">
                    <div class="h-3 w-full animate-pulse rounded-full bg-[#523410]/15" />
                    <div class="h-3 w-4/5 animate-pulse rounded-full bg-[#523410]/15" />
                  </div>
                </div>

                <div class="grid gap-3">
                  <div class="rounded-xl border border-[#e5e3df] bg-white p-4">
                    <div class="flex items-center justify-between gap-4">
                      <div class="h-4 w-24 animate-pulse rounded-full bg-[#5645d4]/20" />
                      <div class="h-6 w-16 animate-pulse rounded-md bg-[#e6e0f5]" />
                    </div>
                    <div class="mt-4 grid gap-2">
                      <div class="h-9 animate-pulse rounded-lg bg-[#fafaf9]" />
                      <div class="h-9 animate-pulse rounded-lg bg-[#fafaf9]" />
                      <div class="h-9 animate-pulse rounded-lg bg-[#fafaf9]" />
                    </div>
                  </div>
                  <div class="grid gap-3 sm:grid-cols-2">
                    <div class="h-16 animate-pulse rounded-xl bg-[#dcecfa]" />
                    <div class="h-16 animate-pulse rounded-xl bg-[#d9f3e1]" />
                  </div>
                </div>
              </div>
            </div>

            <div v-else-if="!plan" class="rounded-xl border border-dashed border-[#c8c4be] bg-[#fafaf9] p-6">
              <h4 class="text-2xl font-semibold">还没有路线草案。</h4>
              <p class="mt-3 max-w-2xl leading-7 text-[#5d5b54]">
                填写左侧信息后，这里会按具体日期生成天气、预算、交通和时间点安排。
              </p>
              <div class="mt-6 grid gap-3 sm:grid-cols-2">
                <div class="rounded-lg bg-[#ffe8d4] p-4 text-sm font-medium">日期 · 天气 · 当日预算</div>
                <div class="rounded-lg bg-[#e6e0f5] p-4 text-sm font-medium">时间点 · 地点 · 费用提示</div>
              </div>
            </div>

            <div v-else class="space-y-4">
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

              <TripPlanResult :plan="plan" />
            </div>
          </aside>
        </div>
      </div>
    </section>

    <section id="features" class="mx-auto max-w-7xl px-4 py-16 sm:px-6 lg:px-8">
      <div class="rounded-xl bg-[#f9e79f] p-6 sm:p-8 lg:p-10">
        <div class="grid gap-8 lg:grid-cols-[0.8fr_1.2fr] lg:items-start">
          <div>
            <p class="text-xs font-semibold uppercase text-[#523410]">规划方法</p>
            <h2 class="mt-3 text-4xl font-semibold leading-tight">一份好路线，需要四个层次。</h2>
          </div>
          <div class="grid gap-4 sm:grid-cols-2">
            <article v-for="feature in features" :key="feature.title" class="rounded-xl border border-[#e5e3df] bg-white p-5">
              <component :is="feature.icon" class="h-6 w-6 text-[#5645d4]" aria-hidden="true" />
              <h3 class="mt-4 text-xl font-semibold">{{ feature.title }}</h3>
              <p class="mt-3 text-sm leading-6 text-[#5d5b54]">{{ feature.description }}</p>
            </article>
          </div>
        </div>
      </div>
    </section>
  </main>
</template>
