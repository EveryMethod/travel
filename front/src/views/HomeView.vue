<script setup lang="ts">
import { computed, onMounted, reactive, ref, watch } from 'vue'
import { useRouter } from 'vue-router'
import { ArrowRight, CalendarDays, CheckCircle2, Compass, MapPinned, Route, Sparkles } from 'lucide-vue-next'

import TripPlanResult from '@/components/TripPlanResult.vue'
import { useTripGeneration } from '@/composables'
import { getAuthTokens, logout } from '@/services'
import { planToMarkdown } from '@/services/tripMarkdown'
import type { TravelCompanions, TravelPace, TravelStyle, TripPlanRequest } from '@/types'

const styleOptions: Array<{ label: string; value: TravelStyle }> = [
  { label: '人文历史', value: 'culture' },
  { label: '本地美食', value: 'food' },
  { label: '自然风景', value: 'nature' },
  { label: '亲子友好', value: 'family' },
  { label: '浪漫慢游', value: 'romantic' },
  { label: '探索冒险', value: 'adventure' },
  { label: '轻松休闲', value: 'relaxed' },
]

const paceOptions: Array<{ label: string; value: TravelPace }> = [
  { label: '适中', value: 'balanced' },
  { label: '轻松', value: 'relaxed' },
  { label: '紧凑', value: 'packed' },
]

const companionOptions: Array<{ label: string; value: TravelCompanions }> = [
  { label: '朋友', value: 'friends' },
  { label: '独自出行', value: 'solo' },
  { label: '情侣', value: 'couple' },
  { label: '家庭', value: 'family' },
  { label: '老人', value: 'seniors' },
]

const budgetBreakdownFields = [
  { key: 'transport', label: '交通', placeholder: '1200' },
  { key: 'hotel', label: '住宿', placeholder: '1800' },
  { key: 'food', label: '餐饮', placeholder: '900' },
  { key: 'tickets', label: '门票', placeholder: '600' },
] as const

const destinations = [
  {
    name: '京都',
    accent: '人文 / 慢游 / 美食',
    description: '庭院、町屋和本地料理排成一条慢路线。',
    tint: 'bg-[#ffe8d4]',
    styles: ['culture', 'food'] as TravelStyle[],
    notes: '想要庭院、町屋和本地料理，节奏不要太赶。',
    budget: '6000',
  },
  {
    name: '大理',
    accent: '自然 / 民宿 / 留白',
    description: '把洱海、古城和留白时间放在同一张行程里。',
    tint: 'bg-[#d9f3e1]',
    styles: ['nature', 'relaxed'] as TravelStyle[],
    notes: '想住民宿，看洱海和古城，保留发呆时间。',
    budget: '4500',
  },
  {
    name: '巴黎',
    accent: '艺术 / 步行 / 咖啡',
    description: '用清楚坐标串起左岸、画廊和晨咖啡。',
    tint: 'bg-[#fde0ec]',
    styles: ['culture', 'romantic'] as TravelStyle[],
    notes: '想要博物馆、画廊、咖啡馆和适合步行的路线。',
    budget: '12000',
  },
  {
    name: '冰岛',
    accent: '公路 / 季节 / 温泉',
    description: '给天气、温泉和远距离交通留出弹性。',
    tint: 'bg-[#dcecfa]',
    styles: ['nature', 'adventure'] as TravelStyle[],
    notes: '想看自然风景和温泉，行程要给天气变化留缓冲。',
    budget: '18000',
  },
]

const features = [
  { icon: Compass, title: '偏好成形', description: '预算、日期、旅行风格和补充偏好先收束成一条路线。' },
  { icon: CalendarDays, title: '按日展开', description: '每天按具体时间点展开，避免只得到景点清单。' },
  { icon: Route, title: '动线清楚', description: '围绕相邻区域安排重点，减少无意义往返。' },
  { icon: CheckCircle2, title: '提醒完整', description: '保留交通、预约、天气和开放时间的核对意识。' },
]

const generationStages = [
  {
    key: 'requirements',
    title: '整理旅行需求',
    description: '读取目的地、日期、预算、节奏和同行人偏好。',
    matchers: ['整理旅行需求'],
  },
  {
    key: 'map',
    title: '查询目的地信息',
    description: '检索景点、天气、起终点和基础动线。',
    matchers: ['查询目的地', '天气', '路线数据'],
  },
  {
    key: 'price',
    title: '搜索价格参考',
    description: '查找门票、车票和预算相关信息。',
    matchers: ['搜索门票', '车票', '预算参考'],
  },
  {
    key: 'constraints',
    title: '整理偏好约束',
    description: '合并预算拆分、必去、避开和旅行节奏。',
    matchers: ['整理预算', '偏好约束'],
  },
  {
    key: 'draft',
    title: '生成路线草案',
    description: '按具体日期和时间点生成每日安排。',
    matchers: ['大模型生成', '路线草案'],
  },
  {
    key: 'validate',
    title: '校验行程格式',
    description: '检查返回结构、天数和字段完整性。',
    matchers: ['校验', '行程格式'],
  },
  {
    key: 'review',
    title: '检查可执行性',
    description: '检查预算、重复时间和跨区通勤风险。',
    matchers: ['检查预算', '可执行性'],
  },
] as const

type GenerationStageKey = (typeof generationStages)[number]['key']

const form = reactive({
  destination: '北京',
  origin: '上海',
  days: 1,
  budget: '',
  travel_style: ['culture'] as TravelStyle[],
  start_date: todayIso(),
  end_date: todayIso(),
  pace: '' as TravelPace | '',
  companions: '' as TravelCompanions | '',
  must_see: '',
  avoid: '',
  budget_breakdown: {
    transport: '',
    hotel: '',
    food: '',
    tickets: '',
  },
  notes: '',
})

const currentStageKey = ref<GenerationStageKey>('requirements')
const {
  plan,
  error,
  isGenerating: isLoading,
  isComplete: isPlanComplete,
  isCancelled,
  traceId,
  lastStatus: streamMessage,
  streamSteps,
  generate,
  cancel: cancelGeneration,
  reset: resetGeneration,
} = useTripGeneration(updateCurrentStage)
const copyMessage = ref('')
const manualCopyMarkdown = ref('')
const reuseMessage = ref('')
const dateWarning = ref('')
const isLoggedIn = ref(false)
const router = useRouter()
const notesMaxLength = 500
const REUSE_TRIP_REQUEST_KEY = 'travel_reuse_trip_request'

const maxEndDate = computed(() => addDays(form.start_date, 9))
const notesTooLong = computed(() => submittedNotes.value.length > notesMaxLength)
const canSubmit = computed(() => form.destination.trim().length > 0 && form.days >= 1 && form.days <= 10 && form.travel_style.length > 0 && !notesTooLong.value && !isLoading.value)
const destinationHasError = computed(() => error.value.length > 0 && form.destination.trim().length === 0)
const selectedStyleLabels = computed(() => styleOptions.filter((option) => form.travel_style.includes(option.value)).map((option) => option.label).join('、'))
const paceLabel = computed(() => paceOptions.find((option) => option.value === form.pace)?.label ?? '')
const companionLabel = computed(() => companionOptions.find((option) => option.value === form.companions)?.label ?? '')
const budgetBreakdownText = computed(() => budgetBreakdownFields
  .map((field) => {
    const value = form.budget_breakdown[field.key].trim()
    return value ? `${field.label} ${value}` : ''
  })
  .filter(Boolean)
  .join('，'))
const submittedNotes = computed(() => {
  const items = [
    form.notes.trim(),
    form.pace ? `节奏：${paceLabel.value}` : '',
    form.companions ? `同行人：${companionLabel.value}` : '',
    form.must_see.trim() ? `必去：${form.must_see.trim()}` : '',
    form.avoid.trim() ? `避开：${form.avoid.trim()}` : '',
    budgetBreakdownText.value ? `分项预算：${budgetBreakdownText.value}` : '',
  ].filter(Boolean)

  return items.join('；\n')
})
const optionalSummaryItems = computed(() => [
  { label: '必去', value: form.must_see.trim() },
  { label: '避开', value: form.avoid.trim() },
  { label: '分项预算', value: budgetBreakdownText.value },
  { label: '补充偏好', value: form.notes.trim() },
].filter((item) => item.value))
const summaryItems = computed(() => [
  { label: '目的地', value: form.destination.trim() || '未填写' },
  { label: '出发地', value: form.origin.trim() || '未填写' },
  { label: '日期', value: `${form.start_date || '未定'} 至 ${form.end_date || '未定'}` },
  { label: '天数', value: `${form.days} 天` },
  { label: '风格', value: selectedStyleLabels.value || '未选择' },
  { label: '预算', value: form.budget.trim() ? `¥${form.budget.trim()}` : '未填写' },
  { label: '节奏', value: paceLabel.value || '未选择' },
  { label: '同行', value: companionLabel.value || '未选择' },
])
const loadingSummaryItems = computed(() => summaryItems.value.filter((item) => item.value !== '未填写' && item.value !== '未选择').slice(0, 6))
const currentStageIndex = computed(() => Math.max(generationStages.findIndex((stage) => stage.key === currentStageKey.value), 0))
const activeStage = computed(() => generationStages[currentStageIndex.value])
const completedStageCount = computed(() => isPlanComplete.value ? generationStages.length : currentStageIndex.value)
const progressPercent = computed(() => Math.min(100, Math.round(((completedStageCount.value + (isLoading.value ? 0.45 : 0)) / generationStages.length) * 100)))
const previewDays = computed(() => Array.from({ length: Math.min(Math.max(form.days, 1), 3) }, (_, index) => index + 1))
const hiddenPreviewDays = computed(() => Math.max(form.days - previewDays.value.length, 0))

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

function applyTripRequest(request: Partial<TripPlanRequest>) {
  form.destination = request.destination ?? form.destination
  form.origin = request.origin ?? form.origin
  form.budget = request.budget ?? form.budget
  form.travel_style = request.travel_style?.length ? [...request.travel_style] : form.travel_style
  if (request.start_date && request.end_date) {
    form.start_date = request.start_date
    form.end_date = request.end_date
  }
  form.days = request.days ?? form.days
  form.pace = request.pace ?? form.pace
  form.companions = request.companions ?? form.companions
  form.must_see = request.must_see ?? form.must_see
  form.avoid = request.avoid ?? form.avoid
  form.notes = request.notes ? originalNotesFromRequest(request.notes) : form.notes
  form.budget_breakdown.transport = request.budget_breakdown?.transport ?? form.budget_breakdown.transport
  form.budget_breakdown.hotel = request.budget_breakdown?.hotel ?? form.budget_breakdown.hotel
  form.budget_breakdown.food = request.budget_breakdown?.food ?? form.budget_breakdown.food
  form.budget_breakdown.tickets = request.budget_breakdown?.tickets ?? form.budget_breakdown.tickets
  resetGeneration()
  copyMessage.value = ''
  manualCopyMarkdown.value = ''
  reuseMessage.value = ''
  currentStageKey.value = 'requirements'
}

function originalNotesFromRequest(notes: string): string {
  return notes
    .split('；\n')
    .filter((item) => !['节奏：', '同行人：', '必去：', '避开：', '分项预算：'].some((prefix) => item.startsWith(prefix)))
    .join('；\n')
}

function updateCurrentStage(message: string) {
  const stage = generationStages.find((item) => item.matchers.some((matcher) => message.includes(matcher)))
  if (!stage) return

  currentStageKey.value = stage.key
}

function consumeReusableTripRequest() {
  const value = sessionStorage.getItem(REUSE_TRIP_REQUEST_KEY)
  if (!value) return

  sessionStorage.removeItem(REUSE_TRIP_REQUEST_KEY)
  try {
    applyTripRequest(JSON.parse(value) as Partial<TripPlanRequest>)
    reuseMessage.value = '已载入上次行程配置，你可以调整后重新生成。'
    requestAnimationFrame(() => document.querySelector('#planner')?.scrollIntoView({ behavior: 'smooth' }))
  } catch {
    // ponytail: bad session payload should not block the planner; persistent drafts can validate later.
  }
}

async function createPlan() {
  if (!canSubmit.value) {
    error.value = '请填写目的地，并至少安排 1 天行程。'
    return
  }

  copyMessage.value = ''
  manualCopyMarkdown.value = ''
  reuseMessage.value = ''
  currentStageKey.value = 'requirements'

  const payload = {
    destination: form.destination.trim(),
    origin: form.origin.trim(),
    days: form.days,
    budget: form.budget.trim(),
    budget_breakdown: {
      transport: form.budget_breakdown.transport.trim(),
      hotel: form.budget_breakdown.hotel.trim(),
      food: form.budget_breakdown.food.trim(),
      tickets: form.budget_breakdown.tickets.trim(),
    },
    travel_style: form.travel_style,
    pace: form.pace || 'balanced',
    companions: form.companions || 'friends',
    start_date: form.start_date,
    end_date: form.end_date,
    must_see: form.must_see.trim(),
    avoid: form.avoid.trim(),
    notes: submittedNotes.value,
  }

  await generate(payload)
}

async function viewGeneratedTrip() {
  if (!plan.value) return
  await router.push(`/trips/${plan.value.trip_id}`)
}

async function viewWorkspace() {
  await router.push('/workspace')
}

async function copyGeneratedMarkdown() {
  if (!plan.value) return

  const markdown = planToMarkdown(plan.value)

  if (navigator.clipboard?.writeText) {
    try {
      await navigator.clipboard.writeText(markdown)
      copyMessage.value = '已复制 Markdown。'
      manualCopyMarkdown.value = ''
      return
    } catch {
      // ponytail: mirror the detail page fallback when browser clipboard access is blocked.
    }
  }

  manualCopyMarkdown.value = markdown
  copyMessage.value = '自动复制不可用，请手动复制下方 Markdown。'
}

async function logoutAndReturn() {
  await logout()
  isLoggedIn.value = false
  await router.push('/login')
}

onMounted(() => {
  isLoggedIn.value = getAuthTokens() !== null
  consumeReusableTripRequest()
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

function applyDestinationTemplate(destination: (typeof destinations)[number]) {
  form.destination = destination.name
  form.travel_style = [...destination.styles]
  form.notes = destination.notes
  form.budget = destination.budget
  form.pace = ''
  form.companions = ''
  form.must_see = ''
  form.avoid = ''
  form.budget_breakdown.transport = ''
  form.budget_breakdown.hotel = ''
  form.budget_breakdown.food = ''
  form.budget_breakdown.tickets = ''
  resetGeneration()
  copyMessage.value = ''
  manualCopyMarkdown.value = ''
  reuseMessage.value = ''
  currentStageKey.value = 'requirements'
  document.querySelector('#planner')?.scrollIntoView({ behavior: 'smooth' })
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
          <p class="mb-5 inline-flex rounded-md bg-white/10 px-3 py-1 text-xs font-semibold text-[#f9e79f]">
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
            <p class="text-xs font-semibold text-[#787671]">路书草稿</p>
          </div>

          <div class="p-4">
            <div class="rounded-xl border border-dashed border-[#c8c4be] bg-[#f8f5e8] p-5 shadow-[0_18px_40px_rgba(15,15,15,0.16)]">
              <div class="flex items-start justify-between gap-4 border-b border-[#d8c7a4] pb-4">
                <div>
                  <p class="text-xs font-semibold tracking-[0.2em] text-[#9a5b13]">路书草稿</p>
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
        </div>
      </div>
    </section>

    <section id="planner" class="bg-[#f6f5f4] px-4 py-16 sm:px-6 lg:px-8">
      <div class="mx-auto max-w-7xl">
        <div class="mb-8 max-w-3xl">
          <p class="text-xs font-semibold uppercase text-[#dd5b00]">行程规划</p>
          <h2 class="mt-3 text-4xl font-semibold leading-tight">把想法交给一张清楚的行程单。</h2>
          <p id="planner-helper" class="mt-4 text-base leading-7 text-[#5d5b54]">
            先填必要信息就能生成；预算拆分、同行人和补充偏好都可以之后再加。
          </p>
          <p v-if="reuseMessage" class="mt-4 rounded-xl border border-[#5645d4]/20 bg-[#e6e0f5] px-4 py-3 text-sm font-medium text-[#391c57]">
            {{ reuseMessage }}
          </p>
        </div>

        <div class="grid items-stretch gap-6 lg:grid-cols-[360px_minmax(0,1fr)]">
          <form class="rounded-xl border border-[#e5e3df] bg-white p-4 lg:sticky lg:top-24 lg:self-start" :aria-describedby="error ? 'planner-error' : 'planner-helper'" @submit.prevent="createPlan">
            <div class="mb-4 flex items-center justify-between gap-4">
              <div>
                <p class="text-xs font-semibold text-[#787671]">出行摘要</p>
                <h3 class="mt-1 text-xl font-semibold">这次出发</h3>
              </div>
              <Sparkles class="h-6 w-6 text-[#dd5b00]" aria-hidden="true" />
            </div>

            <div class="space-y-3">
              <div class="rounded-lg bg-[#fafaf9] px-3 py-2">
                <p class="text-sm font-semibold">基础信息</p>
                <p class="mt-1 text-xs leading-5 text-[#5d5b54]">这些足够生成第一版路线。</p>
              </div>

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

              <div class="block">
                <span class="text-sm font-medium">出行日期</span>
                <div class="mt-1.5 grid gap-2 sm:grid-cols-2">
                  <input v-model="form.start_date" type="date" aria-label="出发日期" class="h-10 w-full rounded-md border border-[#c8c4be] bg-white px-3 text-sm outline-none focus:border-[#5645d4] focus:ring-2 focus:ring-[#d6b6f6]" />
                  <input
                    v-model="form.end_date"
                    aria-label="结束日期"
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

              <div class="block">
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

              <p v-if="notesTooLong" class="rounded-md border border-[#e03131]/30 bg-[#fde0ec] px-3 py-2 text-sm font-medium text-[#a02e6d]" role="alert">
                补充偏好太长，请删短到 500 字以内。
              </p>

              <p v-if="error" id="planner-error" class="rounded-md border border-[#e03131]/30 bg-[#fde0ec] px-3 py-2 text-sm font-medium text-[#a02e6d]" role="alert">
                {{ error }}
              </p>

              <button type="submit" :disabled="!canSubmit" class="inline-flex min-h-10 w-full items-center justify-center gap-2 rounded-md bg-[#5645d4] px-5 py-2.5 text-sm font-medium text-white hover:bg-[#4534b3] disabled:cursor-not-allowed disabled:bg-[#e5e3df] disabled:text-[#bbb8b1]">
                {{ isLoading ? '正在整理路线...' : '生成路线草案' }}
                <ArrowRight class="h-4 w-4" aria-hidden="true" />
              </button>
              <button v-if="isLoading" type="button" class="inline-flex min-h-10 w-full items-center justify-center rounded-md border border-[#c8c4be] bg-white px-5 py-2.5 text-sm font-medium text-[#37352f] hover:bg-[#f6f5f4]" @click="cancelGeneration">
                取消生成
              </button>

              <details class="rounded-xl border border-[#e5e3df] bg-[#fafaf9] p-3">
                <summary class="cursor-pointer text-sm font-semibold text-[#37352f]">可选细节：预算、同行人、必去地点</summary>
                <div class="mt-4 space-y-3">
                  <label class="block">
                    <span class="text-sm font-medium">总预算</span>
                    <div class="mt-1.5 flex h-10 overflow-hidden rounded-md border border-[#c8c4be] bg-white focus-within:border-[#5645d4] focus-within:ring-2 focus-within:ring-[#d6b6f6]">
                      <span class="grid w-10 place-items-center border-r border-[#e5e3df] text-sm font-semibold text-[#5d5b54]">¥</span>
                      <input v-model="form.budget" inputmode="numeric" class="min-w-0 flex-1 px-3 text-base outline-none" placeholder="5000" />
                    </div>
                  </label>

                  <details class="rounded-lg border border-[#e5e3df] bg-white p-3">
                    <summary class="cursor-pointer text-sm font-semibold text-[#37352f]">展开分项预算</summary>
                    <div class="mt-3 grid gap-2 sm:grid-cols-2">
                      <label v-for="field in budgetBreakdownFields" :key="field.key" class="block text-xs font-medium text-[#5d5b54]">
                        <span>{{ field.label }}</span>
                        <input v-model="form.budget_breakdown[field.key]" inputmode="numeric" class="mt-1 h-10 w-full rounded-md border border-[#c8c4be] bg-white px-3 text-sm outline-none focus:border-[#5645d4] focus:ring-2 focus:ring-[#d6b6f6]" :placeholder="field.placeholder" />
                      </label>
                    </div>
                  </details>

                  <div class="grid gap-3 sm:grid-cols-2">
                    <label class="block">
                      <span class="text-sm font-medium">节奏</span>
                      <select v-model="form.pace" class="mt-1.5 h-10 w-full rounded-md border border-[#c8c4be] bg-white px-3 text-sm outline-none focus:border-[#5645d4] focus:ring-2 focus:ring-[#d6b6f6]">
                        <option value="">不指定</option>
                        <option v-for="option in paceOptions" :key="option.value" :value="option.value">{{ option.label }}</option>
                      </select>
                    </label>

                    <label class="block">
                      <span class="text-sm font-medium">同行人</span>
                      <select v-model="form.companions" class="mt-1.5 h-10 w-full rounded-md border border-[#c8c4be] bg-white px-3 text-sm outline-none focus:border-[#5645d4] focus:ring-2 focus:ring-[#d6b6f6]">
                        <option value="">不指定</option>
                        <option v-for="option in companionOptions" :key="option.value" :value="option.value">{{ option.label }}</option>
                      </select>
                    </label>
                  </div>

                  <div class="grid gap-3 sm:grid-cols-2">
                    <label class="block">
                      <span class="text-sm font-medium">必去</span>
                      <input v-model="form.must_see" class="mt-1.5 h-10 w-full rounded-md border border-[#c8c4be] bg-white px-3 text-sm outline-none focus:border-[#5645d4] focus:ring-2 focus:ring-[#d6b6f6]" placeholder="例如：故宫、三里屯" />
                    </label>

                    <label class="block">
                      <span class="text-sm font-medium">避开</span>
                      <input v-model="form.avoid" class="mt-1.5 h-10 w-full rounded-md border border-[#c8c4be] bg-white px-3 text-sm outline-none focus:border-[#5645d4] focus:ring-2 focus:ring-[#d6b6f6]" placeholder="例如：太早出门、人挤人景点" />
                    </label>
                  </div>

                  <label class="block">
                    <span class="text-sm font-medium">补充偏好</span>
                    <textarea v-model="form.notes" rows="2" class="mt-1.5 w-full rounded-md border border-[#c8c4be] bg-white px-3 py-2 text-base outline-none focus:border-[#5645d4] focus:ring-2 focus:ring-[#d6b6f6]" placeholder="美食、节奏、必去地点、同行人情况等..." />
                  </label>
                </div>
              </details>

              <div class="sticky bottom-3 z-20 mt-4 space-y-2 rounded-xl border border-[#e5e3df] bg-white/95 p-2 shadow-lg backdrop-blur lg:hidden">
                <button type="submit" :disabled="!canSubmit" class="inline-flex min-h-11 w-full items-center justify-center gap-2 rounded-md bg-[#5645d4] px-5 py-2.5 text-sm font-medium text-white hover:bg-[#4534b3] disabled:cursor-not-allowed disabled:bg-[#e5e3df] disabled:text-[#bbb8b1]">
                  {{ isLoading ? '正在整理路线...' : '生成路线草案' }}
                  <ArrowRight class="h-4 w-4" aria-hidden="true" />
                </button>
                <button v-if="isLoading" type="button" class="inline-flex min-h-10 w-full items-center justify-center rounded-md border border-[#c8c4be] bg-white px-5 py-2.5 text-sm font-medium text-[#37352f] hover:bg-[#f6f5f4]" @click="cancelGeneration">
                  取消生成
                </button>
              </div>
            </div>
          </form>

          <aside class="min-h-0 rounded-xl border border-[#e5e3df] bg-white p-5 sm:p-6 lg:h-full lg:overflow-y-auto" aria-live="polite" :aria-busy="isLoading">
            <div class="mb-5 flex items-center justify-between gap-4">
              <div>
                <p class="text-xs font-semibold text-[#787671]">路线草案</p>
                <h3 class="mt-1 text-2xl font-semibold">路线草案</h3>
              </div>
              <Route class="h-6 w-6 text-[#dd5b00]" aria-hidden="true" />
            </div>

            <div v-if="isLoading" class="overflow-hidden rounded-xl border border-[#e5e3df] bg-white shadow-sm">
              <div class="border-b border-[#e5e3df] bg-[#fafaf9] p-5 sm:p-6">
                <div class="flex flex-col justify-between gap-4 lg:flex-row lg:items-start">
                  <div>
                    <p class="text-xs font-semibold uppercase text-[#dd5b00]">路线草案生成中</p>
                    <h4 class="mt-2 text-2xl font-semibold">{{ activeStage.title }}</h4>
                    <p class="mt-2 max-w-2xl text-sm leading-6 text-[#5d5b54]">
                      {{ streamMessage || activeStage.description }}
                    </p>
                  </div>
                  <div class="rounded-xl border border-[#e5e3df] bg-white px-4 py-3 text-sm font-semibold text-[#37352f]">
                    已完成 {{ completedStageCount }} / {{ generationStages.length }} 步
                  </div>
                </div>

                <div class="mt-5 h-2 overflow-hidden rounded-full bg-[#e5e3df]" aria-hidden="true">
                  <div class="h-full rounded-full bg-[#dd5b00] transition-all duration-500" :style="{ width: `${progressPercent}%` }" />
                </div>
              </div>

              <div class="grid gap-5 p-5 xl:grid-cols-[minmax(0,1.05fr)_minmax(280px,0.95fr)] sm:p-6">
                <div class="space-y-4">
                  <ol class="space-y-3">
                    <li v-for="(stage, index) in generationStages" :key="stage.key" class="grid grid-cols-[32px_minmax(0,1fr)] gap-3">
                      <span
                        class="mt-0.5 grid h-8 w-8 place-items-center rounded-full border text-xs font-semibold transition"
                        :class="[
                          index < currentStageIndex || isPlanComplete ? 'border-[#1aae39]/30 bg-[#d9f3e1] text-[#11752b]' : '',
                          index === currentStageIndex && !isPlanComplete ? 'border-[#dd5b00]/30 bg-[#fff3e6] text-[#793400] shadow-[0_0_0_4px_rgba(221,91,0,0.08)]' : '',
                          index > currentStageIndex && !isPlanComplete ? 'border-[#e5e3df] bg-white text-[#bbb8b1]' : '',
                        ]"
                      >
                        <span v-if="index < currentStageIndex || isPlanComplete">✓</span>
                        <span v-else-if="index === currentStageIndex" class="h-2.5 w-2.5 animate-pulse rounded-full bg-[#dd5b00]" />
                        <span v-else>{{ index + 1 }}</span>
                      </span>
                      <div
                        class="rounded-xl border px-3 py-2.5 transition"
                        :class="index === currentStageIndex && !isPlanComplete ? 'border-[#dd5b00]/30 bg-[#fff8ed]' : 'border-[#e5e3df] bg-[#fafaf9]'"
                      >
                        <p class="text-sm font-semibold text-[#1a1a1a]">{{ stage.title }}</p>
                        <p class="mt-1 text-xs leading-5 text-[#5d5b54]">{{ stage.description }}</p>
                      </div>
                    </li>
                  </ol>

                  <div v-if="loadingSummaryItems.length > 0" class="rounded-xl border border-[#e5e3df] bg-[#f8f5e8] p-4">
                    <p class="text-xs font-semibold uppercase text-[#9a5b13]">本次会优先考虑</p>
                    <dl class="mt-3 grid gap-2 sm:grid-cols-2">
                      <div v-for="item in loadingSummaryItems" :key="item.label" class="rounded-lg bg-white/70 px-3 py-2 text-sm">
                        <dt class="text-xs font-semibold text-[#787671]">{{ item.label }}</dt>
                        <dd class="mt-1 font-medium text-[#1a1a1a]">{{ item.value }}</dd>
                      </div>
                    </dl>
                  </div>
                </div>

                <div class="rounded-xl border border-dashed border-[#d8c7a4] bg-[#f8f5e8] p-4">
                  <div class="flex items-center justify-between gap-3 border-b border-[#d8c7a4] pb-3">
                    <div>
                      <p class="text-xs font-semibold tracking-[0.18em] text-[#9a5b13]">路线预览</p>
                      <h5 class="mt-1 font-semibold">行程单正在成形</h5>
                    </div>
                    <span class="rounded-md bg-white/80 px-2 py-1 text-xs font-semibold text-[#793400]">{{ form.days }} 天</span>
                  </div>

                  <div class="mt-4 space-y-4">
                    <article v-for="day in previewDays" :key="day" class="rounded-xl bg-white/75 p-3 shadow-sm">
                      <div class="flex items-center justify-between gap-3">
                        <p class="text-sm font-semibold text-[#1a1a1a]">第 {{ day }} 天 · {{ day === currentStageIndex ? '正在安排' : '等待填充' }}</p>
                        <span class="h-2 w-2 rounded-full" :class="day <= currentStageIndex + 1 ? 'bg-[#dd5b00]' : 'bg-[#d8c7a4]'" />
                      </div>
                      <div class="mt-3 space-y-2">
                        <div class="grid grid-cols-[48px_1fr] gap-3">
                          <span class="text-xs font-semibold text-[#dd5b00]">09:00</span>
                          <span class="h-3 animate-pulse rounded-full bg-[#523410]/15" />
                        </div>
                        <div class="grid grid-cols-[48px_1fr] gap-3">
                          <span class="text-xs font-semibold text-[#dd5b00]">12:30</span>
                          <span class="h-3 w-4/5 animate-pulse rounded-full bg-[#523410]/15" />
                        </div>
                        <div class="grid grid-cols-[48px_1fr] gap-3">
                          <span class="text-xs font-semibold text-[#dd5b00]">16:00</span>
                          <span class="h-3 w-3/5 animate-pulse rounded-full bg-[#523410]/15" />
                        </div>
                      </div>
                    </article>
                    <p v-if="hiddenPreviewDays > 0" class="text-xs font-medium text-[#787671]">还有 {{ hiddenPreviewDays }} 天会在生成完成后展开。</p>
                  </div>
                </div>
              </div>
            </div>

            <div v-else-if="isCancelled" class="rounded-xl border border-[#d8c7a4] bg-[#f8f5e8] p-6">
              <p class="text-xs font-semibold uppercase text-[#9a5b13]">已取消生成</p>
              <h4 class="mt-2 text-2xl font-semibold">已停止本次路线规划。</h4>
              <p class="mt-3 leading-7 text-[#5d5b54]">你可以调整左侧信息后重新开始。已收到的阶段信息会保留在下方，方便确认停在哪一步。</p>
              <dl class="mt-5 grid gap-3 text-sm sm:grid-cols-2">
                <div class="rounded-lg bg-white/70 px-3 py-2">
                  <dt class="text-xs font-semibold text-[#787671]">Trace ID</dt>
                  <dd class="mt-1 font-medium text-[#1a1a1a]">{{ traceId || '未返回' }}</dd>
                </div>
                <div class="rounded-lg bg-white/70 px-3 py-2">
                  <dt class="text-xs font-semibold text-[#787671]">最后状态</dt>
                  <dd class="mt-1 font-medium text-[#1a1a1a]">{{ streamMessage || '尚未收到阶段状态' }}</dd>
                </div>
              </dl>
              <ul v-if="streamSteps.length" class="mt-4 space-y-2 text-sm leading-6 text-[#5d5b54]">
                <li v-for="step in streamSteps.slice(-4)" :key="step">{{ step }}</li>
              </ul>
            </div>

            <div v-else-if="error && !plan" class="rounded-xl border border-[#e03131]/30 bg-[#fde0ec] p-6">
              <p class="text-xs font-semibold uppercase text-[#a02e6d]">生成失败</p>
              <h4 class="mt-2 text-2xl font-semibold text-[#1a1a1a]">路线草案暂时没有生成成功。</h4>
              <p class="mt-3 leading-7 text-[#5d5b54]">{{ error }}</p>
              <dl class="mt-5 grid gap-3 text-sm sm:grid-cols-2">
                <div class="rounded-lg bg-white/70 px-3 py-2">
                  <dt class="text-xs font-semibold text-[#787671]">Trace ID</dt>
                  <dd class="mt-1 font-medium text-[#1a1a1a]">{{ traceId || '未返回' }}</dd>
                </div>
                <div class="rounded-lg bg-white/70 px-3 py-2">
                  <dt class="text-xs font-semibold text-[#787671]">最后状态</dt>
                  <dd class="mt-1 font-medium text-[#1a1a1a]">{{ streamMessage || '尚未收到阶段状态' }}</dd>
                </div>
              </dl>
              <div v-if="streamSteps.length" class="mt-4 rounded-lg bg-white/70 p-3">
                <p class="text-xs font-semibold text-[#787671]">最近阶段</p>
                <ul class="mt-2 space-y-1 text-sm leading-6 text-[#5d5b54]">
                  <li v-for="step in streamSteps.slice(-4)" :key="step">{{ step }}</li>
                </ul>
              </div>
              <p class="mt-4 text-sm font-medium text-[#a02e6d]">请重试；如果持续失败，请带上 Trace ID 查看后端追踪。</p>
            </div>

            <div v-else-if="!plan" class="rounded-xl border border-dashed border-[#c8c4be] bg-[#fafaf9] p-6">
              <h4 class="text-2xl font-semibold">先生成第一版，再慢慢改。</h4>
              <p class="mt-3 max-w-2xl leading-7 text-[#5d5b54]">
                左侧这些信息已经足够生成路线草案。补充偏好会让结果更准，但不是必填。
              </p>

              <div class="mt-6 rounded-xl border border-[#d8c7a4] bg-[#f8f5e8] p-5">
                <div class="flex items-center justify-between border-b border-[#d8c7a4] pb-3">
                  <p class="text-xs font-semibold tracking-[0.2em] text-[#9a5b13]">出发确认</p>
                  <span class="rounded-md bg-[#dd5b00] px-2 py-1 text-xs font-semibold text-white">草案</span>
                </div>

                <dl class="mt-4 divide-y divide-[#e0d2b6]">
                  <div v-for="item in summaryItems" :key="item.label" class="grid grid-cols-[88px_1fr] gap-4 py-2 text-sm">
                    <dt class="font-semibold text-[#787671]">{{ item.label }}</dt>
                    <dd class="font-medium text-[#1a1a1a]">{{ item.value }}</dd>
                  </div>
                </dl>
              </div>

              <div v-if="optionalSummaryItems.length > 0" class="mt-4 rotate-[-0.5deg] rounded-lg bg-[#f9e79f] p-4 text-sm leading-6 text-[#523410] shadow-sm">
                <p v-for="item in optionalSummaryItems" :key="item.label"><span class="font-semibold">{{ item.label }}：</span>{{ item.value }}</p>
              </div>
            </div>

            <div v-else class="space-y-4">
              <div class="rounded-xl border border-[#1aae39]/20 bg-[#f1fbf4] p-4">
                <div class="flex flex-col justify-between gap-4 lg:flex-row lg:items-center">
                  <div>
                    <p class="text-xs font-semibold uppercase text-[#1aae39]">{{ isPlanComplete ? '已保存到工作台' : '已生成路线草案' }}</p>
                    <h4 class="mt-1 text-xl font-semibold">{{ plan.destination }} 行程已经可以继续处理</h4>
                    <p class="mt-2 text-sm leading-6 text-[#5d5b54]">
                      行程 ID {{ plan.trip_id }}，你可以进入详情页继续复制、复用或重新生成。
                      <span v-if="traceId">Trace ID：{{ traceId }}</span>
                    </p>
                  </div>
                  <div class="flex flex-wrap gap-2">
                    <button type="button" class="rounded-md bg-[#5645d4] px-3 py-2 text-sm font-medium text-white hover:bg-[#4534b3]" @click="viewGeneratedTrip">查看详情</button>
                    <button type="button" class="rounded-md border border-[#c8c4be] bg-white px-3 py-2 text-sm font-medium hover:bg-[#f6f5f4]" @click="copyGeneratedMarkdown">复制 Markdown</button>
                    <button type="button" class="rounded-md border border-[#c8c4be] bg-white px-3 py-2 text-sm font-medium hover:bg-[#f6f5f4]" @click="viewWorkspace">查看工作台</button>
                  </div>
                </div>
                <p v-if="copyMessage" class="mt-3 text-sm font-medium text-[#1aae39]">{{ copyMessage }}</p>
              </div>

              <div v-if="manualCopyMarkdown" class="rounded-xl border border-[#e5e3df] bg-white p-4">
                <label for="home-manual-copy-markdown" class="text-sm font-medium text-[#1a1a1a]">手动复制 Markdown</label>
                <textarea
                  id="home-manual-copy-markdown"
                  readonly
                  :value="manualCopyMarkdown"
                  class="mt-3 min-h-48 w-full rounded-md border border-[#c8c4be] bg-[#f6f5f4] px-3 py-2 text-sm text-[#1a1a1a]"
                />
              </div>

              <TripPlanResult :plan="plan" />
            </div>
          </aside>
        </div>
      </div>
    </section>

    <section id="destinations" class="mx-auto max-w-7xl px-4 py-16 sm:px-6 lg:px-8">
      <div class="mb-8 flex flex-col justify-between gap-4 md:flex-row md:items-end">
        <div>
          <p class="text-xs font-semibold uppercase text-[#dd5b00]">目的地灵感</p>
          <h2 class="mt-3 text-4xl font-semibold leading-tight">先选旅程的质地。</h2>
        </div>
        <p class="max-w-xl text-base leading-7 text-[#5d5b54]">
          这些不是展示卡片，是能直接带你进入规划器的路线模板。
        </p>
      </div>

      <div class="grid gap-4 md:grid-cols-2 xl:grid-cols-4">
        <article v-for="destination in destinations" :key="destination.name" class="rounded-xl border border-[#e5e3df] p-5" :class="destination.tint">
          <p class="text-xs font-semibold text-[#5d5b54]">{{ destination.accent }}</p>
          <h3 class="mt-4 text-3xl font-semibold">{{ destination.name }}</h3>
          <p class="mt-4 text-sm leading-6 text-[#37352f]">{{ destination.description }}</p>
          <button type="button" class="mt-5 rounded-md bg-[#0a1530] px-3 py-2 text-sm font-medium text-white hover:bg-[#1a2a52]" @click="applyDestinationTemplate(destination)">
            用 {{ destination.name }} 开始
          </button>
        </article>
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
              <component :is="feature.icon" class="h-6 w-6 text-[#dd5b00]" aria-hidden="true" />
              <h3 class="mt-4 text-xl font-semibold">{{ feature.title }}</h3>
              <p class="mt-3 text-sm leading-6 text-[#5d5b54]">{{ feature.description }}</p>
            </article>
          </div>
        </div>
      </div>
    </section>
  </main>
</template>
