<script setup lang="ts">
import { computed, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'

import TripPlanResult from '@/components/TripPlanResult.vue'
import { useTripGeneration } from '@/composables'
import { deleteTrip, getTrip } from '@/services'
import { planToMarkdown } from '@/services/tripMarkdown'
import type { SavedTripDetail } from '@/types'

const route = useRoute()
const router = useRouter()
const trip = ref<SavedTripDetail | null>(null)
const isLoading = ref(false)
const error = ref('')
const copyMessage = ref('')
const {
  error: regenerationError,
  isGenerating: isRegenerating,
  isCancelled: isRegenerationCancelled,
  traceId: regenerationTraceId,
  lastStatus: regenerationStatus,
  streamSteps: regenerationSteps,
  generate: generateTrip,
  cancel: cancelRegeneration,
  reset: resetRegeneration,
} = useTripGeneration()
const manualCopyMarkdown = ref('')
const tripId = computed(() => String(route.params.id))
const REUSE_TRIP_REQUEST_KEY = 'travel_reuse_trip_request'

async function loadTrip() {
  error.value = ''
  copyMessage.value = ''
  manualCopyMarkdown.value = ''
  resetRegeneration()
  trip.value = null
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

  if (navigator.clipboard?.writeText) {
    try {
      await navigator.clipboard.writeText(markdown)
      copyMessage.value = '已复制 Markdown。'
      manualCopyMarkdown.value = ''
      return
    } catch {
      // ponytail: keep the fallback inline; add a richer copy UX only if browser limits become a real product issue.
    }
  }

  manualCopyMarkdown.value = markdown
  copyMessage.value = '自动复制不可用，请手动复制下方 Markdown。'
}

async function regenerateTrip() {
  if (!trip.value) return

  error.value = ''
  try {
    const plan = await generateTrip(trip.value.request_json)
    if (plan) {
      await router.push(`/trips/${plan.trip_id}`)
    }
  } catch (caughtError) {
    error.value = caughtError instanceof Error ? caughtError.message : '重新生成失败，请稍后重试。'
  }
}

async function reuseTripRequest() {
  if (!trip.value) return

  error.value = ''
  try {
    sessionStorage.setItem(REUSE_TRIP_REQUEST_KEY, JSON.stringify(trip.value.request_json))
    await router.push('/home#planner')
  } catch {
    error.value = '无法复用此行程，请稍后重试。'
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

watch(tripId, () => {
  void loadTrip()
}, { immediate: true })
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
              <button type="button" class="rounded-md border border-[#c8c4be] px-3 py-2 text-sm font-medium hover:bg-[#f6f5f4]" @click="reuseTripRequest">复用此行程</button>
              <button type="button" :disabled="isRegenerating" class="rounded-md bg-[#5645d4] px-3 py-2 text-sm font-medium text-white hover:bg-[#4534b3] disabled:bg-[#e5e3df] disabled:text-[#bbb8b1]" @click="regenerateTrip">
                {{ isRegenerating ? '重新生成中...' : '重新生成' }}
              </button>
              <button v-if="isRegenerating" type="button" class="rounded-md border border-[#c8c4be] px-3 py-2 text-sm font-medium hover:bg-[#f6f5f4]" @click="cancelRegeneration">取消重新生成</button>
              <button type="button" class="rounded-md border border-[#e03131]/40 px-3 py-2 text-sm font-medium text-[#a02e6d] hover:bg-[#fde0ec]" @click="removeTrip">删除</button>
            </div>
          </div>
          <p v-if="copyMessage" class="mt-3 text-sm font-medium text-[#1aae39]">{{ copyMessage }}</p>
          <p v-if="error" class="mt-3 rounded-md border border-[#e03131]/30 bg-[#fde0ec] px-3 py-2 text-sm font-medium text-[#a02e6d]">{{ error }}</p>
        </div>

        <div v-if="isRegenerating || regenerationError || isRegenerationCancelled" class="rounded-xl border border-[#e5e3df] bg-white p-5">
          <p class="text-xs font-semibold uppercase" :class="regenerationError ? 'text-[#a02e6d]' : 'text-[#5645d4]'">
            {{ isRegenerating ? '重新生成中' : isRegenerationCancelled ? '已取消重新生成' : '重新生成失败' }}
          </p>
          <h2 class="mt-2 text-xl font-semibold">
            {{ isRegenerating ? '正在创建新的行程版本。' : isRegenerationCancelled ? '原行程已保留。' : '新的行程版本没有生成成功。' }}
          </h2>
          <p v-if="regenerationError" class="mt-3 rounded-md border border-[#e03131]/30 bg-[#fde0ec] px-3 py-2 text-sm font-medium text-[#a02e6d]">{{ regenerationError }}</p>
          <dl class="mt-4 grid gap-3 text-sm sm:grid-cols-2">
            <div class="rounded-lg bg-[#f6f5f4] px-3 py-2">
              <dt class="text-xs font-semibold text-[#787671]">Trace ID</dt>
              <dd class="mt-1 font-medium text-[#1a1a1a]">{{ regenerationTraceId || '未返回' }}</dd>
            </div>
            <div class="rounded-lg bg-[#f6f5f4] px-3 py-2">
              <dt class="text-xs font-semibold text-[#787671]">当前状态</dt>
              <dd class="mt-1 font-medium text-[#1a1a1a]">{{ regenerationStatus || '尚未收到阶段状态' }}</dd>
            </div>
          </dl>
          <ul v-if="regenerationSteps.length" class="mt-4 space-y-1 text-sm leading-6 text-[#5d5b54]">
            <li v-for="step in regenerationSteps.slice(-4)" :key="step">{{ step }}</li>
          </ul>
        </div>

        <div v-if="manualCopyMarkdown" class="rounded-xl border border-[#e5e3df] bg-white p-5">
          <label for="manual-copy-markdown" class="text-sm font-medium text-[#1a1a1a]">手动复制 Markdown</label>
          <textarea
            id="manual-copy-markdown"
            readonly
            :value="manualCopyMarkdown"
            class="mt-3 min-h-48 w-full rounded-md border border-[#c8c4be] bg-[#f6f5f4] px-3 py-2 text-sm text-[#1a1a1a]"
          />
        </div>

        <TripPlanResult :plan="trip.plan_json" />
      </div>
    </section>
  </main>
</template>
