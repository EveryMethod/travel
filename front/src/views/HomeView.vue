<script setup lang="ts">
import { computed, reactive, ref } from 'vue'
import { ArrowRight, CalendarDays, CheckCircle2, Compass, MapPinned, Route, Sparkles } from 'lucide-vue-next'

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

const destinations = [
  { name: '京都', accent: '人文 / 秋季', description: '庭院、町屋和本地料理排成一条慢路线。', tint: 'bg-[#ffe8d4]' },
  { name: '大理', accent: '自然 / 民宿', description: '把洱海、古城和留白时间放在同一张行程里。', tint: 'bg-[#d9f3e1]' },
  { name: '巴黎', accent: '艺术 / 步行', description: '用清楚坐标串起左岸、画廊和晨咖啡。', tint: 'bg-[#fde0ec]' },
  { name: '冰岛', accent: '公路 / 季节', description: '给天气、温泉和远距离交通留出弹性。', tint: 'bg-[#dcecfa]' },
]

const features = [
  { icon: Compass, title: '偏好成形', description: '预算、月份、旅行风格和补充偏好先收束成一条路线。' },
  { icon: CalendarDays, title: '按天展开', description: '每天拆成上午、下午、晚上，避免只得到景点清单。' },
  { icon: Route, title: '动线清楚', description: '围绕相邻区域安排重点，减少无意义往返。' },
  { icon: CheckCircle2, title: '提醒完整', description: '保留交通、预约、天气和开放时间的核对意识。' },
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
          <RouterLink to="/login" class="rounded-md border border-[#c8c4be] px-3 py-2 text-sm font-medium hover:bg-[#f6f5f4]">
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
            AI travel workspace
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
            <p class="text-xs font-semibold text-[#787671]">Route workspace</p>
          </div>

          <div class="grid gap-4 p-4 sm:grid-cols-[0.8fr_1.2fr]">
            <aside class="rounded-lg bg-[#f6f5f4] p-4">
              <p class="text-xs font-semibold text-[#787671]">Trip brief</p>
              <h2 class="mt-2 text-2xl font-semibold">京都，10月</h2>
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
                  <span class="rounded bg-[#fef7d6] px-2 py-1 text-xs font-semibold">上午 / 下午 / 晚上</span>
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
          <p class="text-xs font-semibold uppercase text-[#5645d4]">Destinations</p>
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
          <p class="text-xs font-semibold uppercase text-[#5645d4]">Planner</p>
          <h2 class="mt-3 text-4xl font-semibold leading-tight">把想法交给一张清楚的行程单。</h2>
          <p id="planner-helper" class="mt-4 text-base leading-7 text-[#5d5b54]">
            保留原来的生成能力，只把表单和结果区改成更像工作台的双栏布局。
          </p>
        </div>

        <div class="grid gap-6 lg:grid-cols-[420px_1fr]">
          <form class="rounded-xl border border-[#e5e3df] bg-white p-5 sm:p-6" :aria-describedby="error ? 'planner-error' : 'planner-helper'" @submit.prevent="createPlan">
            <div class="mb-6 flex items-center justify-between gap-4">
              <div>
                <p class="text-xs font-semibold text-[#787671]">Route brief</p>
                <h3 class="mt-1 text-2xl font-semibold">这次出发</h3>
              </div>
              <Sparkles class="h-6 w-6 text-[#5645d4]" aria-hidden="true" />
            </div>

            <div class="space-y-4">
              <label class="block">
                <span class="text-sm font-medium">目的地</span>
                <input
                  v-model="form.destination"
                  :aria-invalid="destinationHasError ? 'true' : undefined"
                  :aria-describedby="error ? 'planner-error' : undefined"
                  class="mt-2 h-11 w-full rounded-md border border-[#c8c4be] bg-white px-3 text-base outline-none focus:border-[#5645d4] focus:ring-2 focus:ring-[#d6b6f6]"
                  placeholder="京都"
                />
              </label>

              <div class="grid gap-4 sm:grid-cols-2">
                <label class="block">
                  <span class="text-sm font-medium">出发地</span>
                  <input v-model="form.origin" class="mt-2 h-11 w-full rounded-md border border-[#c8c4be] bg-white px-3 text-base outline-none focus:border-[#5645d4] focus:ring-2 focus:ring-[#d6b6f6]" placeholder="上海" />
                </label>

                <label class="block">
                  <span class="text-sm font-medium">旅行天数</span>
                  <input v-model.number="form.days" min="1" max="14" type="number" class="mt-2 h-11 w-full rounded-md border border-[#c8c4be] bg-white px-3 text-base outline-none focus:border-[#5645d4] focus:ring-2 focus:ring-[#d6b6f6]" />
                </label>
              </div>

              <div class="grid gap-4 sm:grid-cols-2">
                <label class="block">
                  <span class="text-sm font-medium">预算</span>
                  <select v-model="form.budget" class="mt-2 h-11 w-full rounded-md border border-[#c8c4be] bg-white px-3 text-base outline-none focus:border-[#5645d4] focus:ring-2 focus:ring-[#d6b6f6]">
                    <option v-for="option in budgetOptions" :key="option.value" :value="option.value">{{ option.label }}</option>
                  </select>
                </label>

                <label class="block">
                  <span class="text-sm font-medium">旅行风格</span>
                  <select v-model="form.travel_style" class="mt-2 h-11 w-full rounded-md border border-[#c8c4be] bg-white px-3 text-base outline-none focus:border-[#5645d4] focus:ring-2 focus:ring-[#d6b6f6]">
                    <option v-for="option in styleOptions" :key="option.value" :value="option.value">{{ option.label }}</option>
                  </select>
                </label>
              </div>

              <label class="block">
                <span class="text-sm font-medium">出行月份</span>
                <input v-model="form.month" class="mt-2 h-11 w-full rounded-md border border-[#c8c4be] bg-white px-3 text-base outline-none focus:border-[#5645d4] focus:ring-2 focus:ring-[#d6b6f6]" placeholder="10月" />
              </label>

              <label class="block">
                <span class="text-sm font-medium">补充偏好</span>
                <textarea v-model="form.notes" rows="4" class="mt-2 w-full rounded-md border border-[#c8c4be] bg-white px-3 py-2 text-base outline-none focus:border-[#5645d4] focus:ring-2 focus:ring-[#d6b6f6]" placeholder="美食、节奏、必去地点、同行人情况等..." />
              </label>

              <p v-if="error" id="planner-error" class="rounded-md border border-[#e03131]/30 bg-[#fde0ec] px-3 py-2 text-sm font-medium text-[#a02e6d]" role="alert">
                {{ error }}
              </p>

              <button type="submit" :disabled="!canSubmit" class="inline-flex min-h-11 w-full items-center justify-center gap-2 rounded-md bg-[#5645d4] px-5 py-3 text-sm font-medium text-white hover:bg-[#4534b3] disabled:cursor-not-allowed disabled:bg-[#e5e3df] disabled:text-[#bbb8b1]">
                {{ isLoading ? '正在整理路线...' : '生成路线草案' }}
                <ArrowRight class="h-4 w-4" aria-hidden="true" />
              </button>
            </div>
          </form>

          <aside class="rounded-xl border border-[#e5e3df] bg-white p-5 sm:p-6" aria-live="polite" :aria-busy="isLoading">
            <div class="mb-6 flex items-center justify-between gap-4">
              <div>
                <p class="text-xs font-semibold text-[#787671]">Route draft</p>
                <h3 class="mt-1 text-2xl font-semibold">路线草案</h3>
              </div>
              <Route class="h-6 w-6 text-[#5645d4]" aria-hidden="true" />
            </div>

            <div v-if="!plan" class="rounded-xl border border-dashed border-[#c8c4be] bg-[#fafaf9] p-6">
              <h4 class="text-2xl font-semibold">还没有路线草案。</h4>
              <p class="mt-3 max-w-2xl leading-7 text-[#5d5b54]">
                填写左侧信息后，这里会出现按天整理的上午、下午、晚上安排，以及出发前提醒。
              </p>
              <div class="mt-6 grid gap-3 sm:grid-cols-3">
                <div class="rounded-lg bg-[#ffe8d4] p-4 text-sm font-medium">上午 · 轻一点开始</div>
                <div class="rounded-lg bg-[#e6e0f5] p-4 text-sm font-medium">下午 · 安排重点</div>
                <div class="rounded-lg bg-[#d9f3e1] p-4 text-sm font-medium">晚上 · 留给回味</div>
              </div>
            </div>

            <div v-else class="space-y-4">
              <div class="rounded-xl bg-[#f9e79f] p-5">
                <p class="text-xs font-semibold text-[#523410]">{{ plan.trip_id }}</p>
                <h2 class="mt-2 text-3xl font-semibold">{{ plan.destination }}</h2>
                <p class="mt-3 leading-7 text-[#37352f]">{{ plan.summary }}</p>
              </div>

              <article v-for="day in plan.days" :key="day.day" class="rounded-xl border border-[#e5e3df] p-5">
                <div class="flex flex-col gap-3 sm:flex-row sm:items-start sm:justify-between">
                  <div>
                    <p class="text-xs font-semibold text-[#5645d4]">第 {{ day.day }} 天</p>
                    <h3 class="mt-1 text-xl font-semibold">{{ day.title }}</h3>
                  </div>
                  <span class="w-fit rounded-md bg-[#e6e0f5] px-2 py-1 text-xs font-semibold text-[#391c57]">{{ day.theme }}</span>
                </div>

                <dl class="mt-5 grid gap-3 md:grid-cols-3">
                  <div class="rounded-lg bg-[#fafaf9] p-4">
                    <dt class="font-semibold">上午</dt>
                    <dd class="mt-2 text-sm leading-6 text-[#5d5b54]">{{ day.morning }}</dd>
                  </div>
                  <div class="rounded-lg bg-[#fafaf9] p-4">
                    <dt class="font-semibold">下午</dt>
                    <dd class="mt-2 text-sm leading-6 text-[#5d5b54]">{{ day.afternoon }}</dd>
                  </div>
                  <div class="rounded-lg bg-[#fafaf9] p-4">
                    <dt class="font-semibold">晚上</dt>
                    <dd class="mt-2 text-sm leading-6 text-[#5d5b54]">{{ day.evening }}</dd>
                  </div>
                </dl>

                <ul class="mt-4 list-disc space-y-1 pl-5 text-sm leading-6 text-[#5d5b54]">
                  <li v-for="note in day.notes" :key="note">{{ note }}</li>
                </ul>
              </article>

              <div class="rounded-xl bg-[#d9f3e1] p-5">
                <h3 class="font-semibold">出发前提醒</h3>
                <ul class="mt-3 list-disc space-y-2 pl-5 text-sm leading-6 text-[#37352f]">
                  <li v-for="tip in plan.tips" :key="tip">{{ tip }}</li>
                </ul>
                <p class="mt-4 border-t border-[#1aae39]/20 pt-4 text-xs font-semibold text-[#5d5b54]">{{ plan.disclaimer }}</p>
              </div>
            </div>
          </aside>
        </div>
      </div>
    </section>

    <section id="features" class="mx-auto max-w-7xl px-4 py-16 sm:px-6 lg:px-8">
      <div class="rounded-xl bg-[#f9e79f] p-6 sm:p-8 lg:p-10">
        <div class="grid gap-8 lg:grid-cols-[0.8fr_1.2fr] lg:items-start">
          <div>
            <p class="text-xs font-semibold uppercase text-[#523410]">Method</p>
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
