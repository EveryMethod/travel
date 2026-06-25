<script setup lang="ts">
import { computed, reactive, ref } from 'vue'

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
  <main class="min-h-screen bg-[#eef3ef] px-4 py-8 text-[#17201b] sm:px-6 lg:px-8">
    <section class="mx-auto grid max-w-6xl gap-6 lg:grid-cols-[0.9fr_1.1fr]">
      <div class="rounded-[2rem] border border-[#c8d8cf] bg-[#f8fbf7] p-6 shadow-[0_24px_80px_rgba(37,60,49,0.12)] sm:p-8">
        <p class="mb-3 text-xs font-semibold uppercase tracking-[0.35em] text-[#3d7665]">路线档案</p>
        <h1 class="text-4xl font-black tracking-[-0.05em] text-[#17201b] sm:text-5xl">
          像写旅行手札一样，生成你的第一版行程。
        </h1>
        <p class="mt-4 max-w-xl text-base leading-7 text-[#52645b]">
          输入旅行偏好后，前端会通过 FastAPI 后端调用本地 LangGraph 规划骨架，并返回一份结构化演示行程。
        </p>

        <form class="mt-8 space-y-5" @submit.prevent="createPlan">
          <label class="block">
            <span class="text-sm font-semibold text-[#26362f]">目的地</span>
            <input
              v-model="form.destination"
              class="mt-2 w-full rounded-2xl border border-[#c8d8cf] bg-white px-4 py-3 outline-none ring-[#3d7665]/30 transition focus:ring-4"
              placeholder="京都"
            />
          </label>

          <div class="grid gap-4 sm:grid-cols-2">
            <label class="block">
              <span class="text-sm font-semibold text-[#26362f]">出发地</span>
              <input
                v-model="form.origin"
                class="mt-2 w-full rounded-2xl border border-[#c8d8cf] bg-white px-4 py-3 outline-none ring-[#3d7665]/30 transition focus:ring-4"
                placeholder="上海"
              />
            </label>

            <label class="block">
              <span class="text-sm font-semibold text-[#26362f]">旅行天数</span>
              <input
                v-model.number="form.days"
                min="1"
                max="14"
                type="number"
                class="mt-2 w-full rounded-2xl border border-[#c8d8cf] bg-white px-4 py-3 outline-none ring-[#3d7665]/30 transition focus:ring-4"
              />
            </label>
          </div>

          <div class="grid gap-4 sm:grid-cols-2">
            <label class="block">
              <span class="text-sm font-semibold text-[#26362f]">预算</span>
              <select
                v-model="form.budget"
                class="mt-2 w-full rounded-2xl border border-[#c8d8cf] bg-white px-4 py-3 outline-none ring-[#3d7665]/30 transition focus:ring-4"
              >
                <option v-for="option in budgetOptions" :key="option.value" :value="option.value">
                  {{ option.label }}
                </option>
              </select>
            </label>

            <label class="block">
              <span class="text-sm font-semibold text-[#26362f]">旅行风格</span>
              <select
                v-model="form.travel_style"
                class="mt-2 w-full rounded-2xl border border-[#c8d8cf] bg-white px-4 py-3 outline-none ring-[#3d7665]/30 transition focus:ring-4"
              >
                <option v-for="option in styleOptions" :key="option.value" :value="option.value">
                  {{ option.label }}
                </option>
              </select>
            </label>
          </div>

          <label class="block">
            <span class="text-sm font-semibold text-[#26362f]">出行月份</span>
            <input
              v-model="form.month"
              class="mt-2 w-full rounded-2xl border border-[#c8d8cf] bg-white px-4 py-3 outline-none ring-[#3d7665]/30 transition focus:ring-4"
              placeholder="10月"
            />
          </label>

          <label class="block">
            <span class="text-sm font-semibold text-[#26362f]">补充偏好</span>
            <textarea
              v-model="form.notes"
              rows="4"
              class="mt-2 w-full rounded-2xl border border-[#c8d8cf] bg-white px-4 py-3 outline-none ring-[#3d7665]/30 transition focus:ring-4"
              placeholder="美食、节奏、必去地点、同行人情况等..."
            />
          </label>

          <p v-if="error" class="rounded-2xl border border-[#d98564] bg-[#fff4ef] px-4 py-3 text-sm text-[#9a3f20]">
            {{ error }}
          </p>

          <button
            type="submit"
            :disabled="!canSubmit"
            class="w-full rounded-2xl bg-[#243b35] px-5 py-3 font-bold text-white shadow-lg shadow-[#243b35]/20 transition hover:-translate-y-0.5 hover:bg-[#315248] disabled:cursor-not-allowed disabled:opacity-50 disabled:hover:translate-y-0"
          >
            {{ isLoading ? '正在生成行程…' : '生成行程' }}
          </button>
        </form>
      </div>

      <aside class="rounded-[2rem] border border-[#c8d8cf] bg-[#17201b] p-4 text-white shadow-[0_24px_80px_rgba(23,32,27,0.2)] sm:p-6">
        <div class="rounded-[1.5rem] border border-dashed border-[#86a99a] bg-[#21312b] p-5 sm:p-6">
          <p class="text-xs font-semibold uppercase tracking-[0.35em] text-[#9cc7b6]">生成的行程</p>

          <div v-if="!plan" class="mt-10 rounded-3xl bg-[#eef3ef] p-6 text-[#17201b]">
            <p class="text-2xl font-black tracking-[-0.04em]">还没有生成路线。</p>
            <p class="mt-3 leading-7 text-[#52645b]">
              提交左侧表单后，可以验证前端、后端和 LangGraph 占位规划器的完整链路。
            </p>
          </div>

          <div v-else class="mt-6 space-y-5">
            <div class="rounded-3xl bg-[#eef3ef] p-5 text-[#17201b]">
              <p class="text-sm font-bold uppercase tracking-[0.2em] text-[#3d7665]">{{ plan.trip_id }}</p>
              <h2 class="mt-2 text-3xl font-black tracking-[-0.05em]">{{ plan.destination }}</h2>
              <p class="mt-3 leading-7 text-[#52645b]">{{ plan.summary }}</p>
            </div>

            <article
              v-for="day in plan.days"
              :key="day.day"
              class="rounded-3xl border border-[#40554c] bg-[#1c2a25] p-5"
            >
              <div class="flex items-start justify-between gap-4">
                <div>
                  <p class="text-xs font-bold uppercase tracking-[0.25em] text-[#9cc7b6]">第 {{ day.day }} 天</p>
                  <h3 class="mt-1 text-xl font-black">{{ day.title }}</h3>
                </div>
                <span class="rounded-full bg-[#d78b5f] px-3 py-1 text-xs font-bold text-[#17201b]">
                  {{ day.theme }}
                </span>
              </div>

              <dl class="mt-5 space-y-3 text-sm leading-6 text-[#dfe8e2]">
                <div>
                  <dt class="font-bold text-white">上午</dt>
                  <dd>{{ day.morning }}</dd>
                </div>
                <div>
                  <dt class="font-bold text-white">下午</dt>
                  <dd>{{ day.afternoon }}</dd>
                </div>
                <div>
                  <dt class="font-bold text-white">晚上</dt>
                  <dd>{{ day.evening }}</dd>
                </div>
              </dl>

              <ul class="mt-4 list-disc space-y-1 pl-5 text-sm text-[#bdd4ca]">
                <li v-for="note in day.notes" :key="note">{{ note }}</li>
              </ul>
            </article>

            <div class="rounded-3xl bg-[#eef3ef] p-5 text-[#17201b]">
              <h3 class="font-black">旅行提示</h3>
              <ul class="mt-3 list-disc space-y-2 pl-5 text-sm leading-6 text-[#52645b]">
                <li v-for="tip in plan.tips" :key="tip">{{ tip }}</li>
              </ul>
              <p class="mt-4 border-t border-[#c8d8cf] pt-4 text-xs font-semibold uppercase tracking-[0.18em] text-[#6b7c73]">
                {{ plan.disclaimer }}
              </p>
            </div>
          </div>
        </div>
      </aside>
    </section>
  </main>
</template>
