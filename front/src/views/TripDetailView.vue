<script setup lang="ts">
import { computed, nextTick, onBeforeUnmount, ref, watch } from 'vue'
import { useRoute, useRouter } from 'vue-router'

import TripPlanResult from '@/components/TripPlanResult.vue'
import { useTripGeneration } from '@/composables'
import { deleteTrip, getTrip, refreshTripTransport } from '@/services'
import { planToMarkdown } from '@/services/tripMarkdown'
import type { SavedTripDetail } from '@/types'

const route = useRoute()
const router = useRouter()
const trip = ref<SavedTripDetail | null>(null)
const isLoading = ref(false)
const error = ref('')
const copyMessage = ref('')
const isRefreshingTransport = ref(false)
const transportRefreshMessage = ref('')
const revisionInstruction = ref('')
const operation = ref<'regenerate' | 'revise' | null>(null)
const regenerateButton = ref<HTMLButtonElement | null>(null)
const revisionTextarea = ref<HTMLTextAreaElement | null>(null)
const manualCopyMarkdownTextarea = ref<HTMLTextAreaElement | null>(null)
const {
  error: operationError,
  isGenerating: isOperating,
  isCancelled: isOperationCancelled,
  traceId: operationTraceId,
  streamSteps: operationSteps,
  generate: generateTrip,
  revise: reviseTrip,
  cancel: cancelOperation,
  reset: resetOperation,
} = useTripGeneration()
const manualCopyMarkdown = ref('')
const tripId = computed(() => String(route.params.id))
const REUSE_TRIP_REQUEST_KEY = 'travel_reuse_trip_request'
let loadRunId = 0
let operationRunId = 0
let isViewActive = true

async function loadTrip() {
  const activeLoadRunId = ++loadRunId
  operationRunId += 1
  error.value = ''
  copyMessage.value = ''
  transportRefreshMessage.value = ''
  manualCopyMarkdown.value = ''
  revisionInstruction.value = ''
  operation.value = null
  resetOperation()
  trip.value = null
  isLoading.value = true
  try {
    const loadedTrip = await getTrip(tripId.value)
    if (activeLoadRunId === loadRunId) {
      trip.value = loadedTrip
    }
  } catch (caughtError) {
    if (activeLoadRunId === loadRunId) {
      error.value = caughtError instanceof Error ? caughtError.message : '行程加载失败。'
    }
  } finally {
    if (activeLoadRunId === loadRunId) {
      isLoading.value = false
    }
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
  await nextTick()
  manualCopyMarkdownTextarea.value?.focus()
}

async function regenerateTrip() {
  if (!trip.value || isOperating.value) return

  const activeOperationRunId = ++operationRunId
  const sourceTripId = tripId.value
  error.value = ''
  operation.value = 'regenerate'
  const plan = await generateTrip(trip.value.request_json)
  if (activeOperationRunId === operationRunId && sourceTripId === tripId.value && plan) {
    await router.push(`/trips/${plan.trip_id}`)
  }
}

async function reviseSavedTrip() {
  if (!trip.value || isOperating.value) return

  const instruction = revisionInstruction.value.trim()
  if (!instruction) {
    error.value = '请先输入本次调整要求。'
    return
  }

  const activeOperationRunId = ++operationRunId
  const sourceTripId = tripId.value
  error.value = ''
  operation.value = 'revise'
  const plan = await reviseTrip(trip.value.id, { instruction })
  if (activeOperationRunId === operationRunId && sourceTripId === tripId.value && plan) {
    await router.push(`/trips/${plan.trip_id}`)
  }
}

async function cancelCurrentOperation() {
  const focusTarget = operation.value === 'regenerate' ? regenerateButton : revisionTextarea
  operationRunId += 1
  cancelOperation()

  if (!isOperating.value) {
    await nextTick()
    focusTarget.value?.focus()
    return
  }

  const stop = watch(isOperating, async (operating) => {
    if (operating) return
    stop()
    await nextTick()
    focusTarget.value?.focus()
  })
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

async function refreshTransport(): Promise<void> {
  if (!trip.value || isRefreshingTransport.value) return

  const activeTrip = trip.value
  const sourceTripId = tripId.value
  isRefreshingTransport.value = true
  transportRefreshMessage.value = ''
  try {
    const refreshedPlan = await refreshTripTransport(activeTrip.id)
    if (isViewActive && trip.value === activeTrip && sourceTripId === tripId.value) {
      activeTrip.plan_json = refreshedPlan
      transportRefreshMessage.value = '票价与余票已刷新。'
    }
  } catch (caughtError) {
    if (isViewActive && trip.value === activeTrip && sourceTripId === tripId.value) {
      transportRefreshMessage.value = caughtError instanceof Error && caughtError.message
        ? caughtError.message
        : '刷新失败，原行程未修改。'
    }
  } finally {
    isRefreshingTransport.value = false
  }
}

async function removeTrip() {
  if (!trip.value || isOperating.value) return
  const sourceTripId = tripId.value
  if (!window.confirm(`删除 ${trip.value.destination} 的 ${trip.value.days} 天游程？`)) return

  try {
    await deleteTrip(trip.value.id)
    if (isViewActive && sourceTripId === tripId.value) {
      await router.push('/workspace')
    }
  } catch (caughtError) {
    if (isViewActive && sourceTripId === tripId.value) {
      error.value = caughtError instanceof Error ? caughtError.message : '删除失败，请稍后重试。'
    }
  }
}

function formatDate(value: string): string {
  return new Intl.DateTimeFormat('zh-CN', { dateStyle: 'medium', timeStyle: 'short' }).format(new Date(value))
}

watch(tripId, () => {
  void loadTrip()
}, { immediate: true })

onBeforeUnmount(() => {
  isViewActive = false
  loadRunId += 1
  operationRunId += 1
})
</script>

<template>
  <main class="min-h-screen bg-[#f6f5f4] text-[#1a1a1a] [font-family:Inter,-apple-system,BlinkMacSystemFont,'Segoe_UI','PingFang_SC','Microsoft_YaHei',sans-serif]">
    <header class="border-b border-[#e5e3df] bg-white">
      <div class="mx-auto flex max-w-6xl items-center justify-between gap-4 px-4 py-4 sm:px-6 lg:px-8">
        <RouterLink to="/workspace" class="rounded-sm text-sm font-semibold text-[#0a1530] outline-none focus-visible:ring-2 focus-visible:ring-[#d6b6f6]">← 返回工作台</RouterLink>
        <RouterLink to="/home" class="rounded-md bg-[#5645d4] px-3 py-2 text-sm font-medium text-white outline-none hover:bg-[#4534b3] focus-visible:ring-2 focus-visible:ring-[#d6b6f6]">新建规划</RouterLink>
      </div>
    </header>

    <section class="mx-auto max-w-6xl px-4 py-8 sm:px-6 lg:px-8">
      <p v-if="isLoading" class="rounded-xl bg-white p-8 text-center text-sm text-[#5d5b54]">正在加载行程...</p>

      <div v-else-if="error && !trip" class="rounded-xl border border-[#e03131]/30 bg-white p-6">
        <p role="alert" class="text-sm font-medium text-[#a02e6d]">{{ error }}</p>
        <RouterLink to="/workspace" class="mt-4 inline-flex rounded-md bg-[#0a1530] px-3 py-2 text-sm font-medium text-white outline-none focus-visible:ring-2 focus-visible:ring-[#d6b6f6]">返回工作台</RouterLink>
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
              <button type="button" class="rounded-md border border-[#c8c4be] px-3 py-2 text-sm font-medium outline-none hover:bg-[#f6f5f4] focus-visible:ring-2 focus-visible:ring-[#d6b6f6]" @click="copyMarkdown">复制 Markdown</button>
              <button type="button" class="rounded-md border border-[#c8c4be] px-3 py-2 text-sm font-medium outline-none hover:bg-[#f6f5f4] focus-visible:ring-2 focus-visible:ring-[#d6b6f6]" @click="reuseTripRequest">复用此行程</button>
              <button v-if="trip.plan_json.intercity_transport" type="button" :disabled="isRefreshingTransport" class="rounded-md border border-[#c8c4be] px-3 py-2 text-sm font-medium outline-none hover:bg-[#f6f5f4] focus-visible:ring-2 focus-visible:ring-[#d6b6f6] disabled:cursor-not-allowed disabled:bg-[#e5e3df] disabled:text-[#bbb8b1]" @click="refreshTransport">
                {{ isRefreshingTransport ? '正在刷新票价与余票...' : '刷新票价与余票' }}
              </button>
              <button ref="regenerateButton" type="button" :disabled="isOperating" class="rounded-md bg-[#5645d4] px-3 py-2 text-sm font-medium text-white outline-none hover:bg-[#4534b3] focus-visible:ring-2 focus-visible:ring-[#d6b6f6] disabled:cursor-not-allowed disabled:bg-[#e5e3df] disabled:text-[#bbb8b1]" @click="regenerateTrip">
                {{ isOperating && operation === 'regenerate' ? '重新生成中...' : '重新生成' }}
              </button>
              <button v-if="isOperating && operation === 'regenerate'" type="button" class="rounded-md border border-[#c8c4be] px-3 py-2 text-sm font-medium outline-none hover:bg-[#f6f5f4] focus-visible:ring-2 focus-visible:ring-[#d6b6f6]" @click="cancelCurrentOperation">取消重新生成</button>
              <button type="button" :disabled="isOperating" class="rounded-md border border-[#e03131]/40 px-3 py-2 text-sm font-medium text-[#a02e6d] outline-none hover:bg-[#fde0ec] focus-visible:ring-2 focus-visible:ring-[#d6b6f6] disabled:cursor-not-allowed disabled:border-[#e5e3df] disabled:text-[#bbb8b1]" @click="removeTrip">删除</button>
            </div>
          </div>
          <p v-if="copyMessage" role="status" aria-live="polite" class="mt-3 text-sm font-medium text-[#1aae39]">{{ copyMessage }}</p>
          <p v-if="transportRefreshMessage" role="status" aria-live="polite" class="mt-3 text-sm font-medium text-[#5d5b54]">{{ transportRefreshMessage }}</p>
          <p v-if="error" role="alert" class="mt-3 rounded-md border border-[#e03131]/30 bg-[#fde0ec] px-3 py-2 text-sm font-medium text-[#a02e6d]">{{ error }}</p>
        </div>

        <form class="rounded-xl border border-[#e5e3df] bg-white p-5" @submit.prevent="reviseSavedTrip">
          <div class="flex flex-col justify-between gap-4 sm:flex-row sm:items-start">
            <div>
              <h2 class="text-lg font-semibold text-[#0a1530]">用一句话生成一份新行程</h2>
              <p class="mt-1 text-sm text-[#5d5b54]">原行程会保留，调整结果将另存为新行程。</p>
            </div>
            <span class="text-xs tabular-nums text-[#787671]">{{ revisionInstruction.length }}/500</span>
          </div>
          <label for="revision-instruction" class="mt-4 block text-sm font-medium text-[#0a1530]">本次调整要求</label>
          <textarea
            id="revision-instruction"
            ref="revisionTextarea"
            v-model="revisionInstruction"
            maxlength="500"
            rows="3"
            :disabled="isOperating"
            class="mt-2 w-full resize-y rounded-md border border-[#c8c4be] bg-white px-3 py-2 text-base text-[#1a1a1a] outline-none placeholder:text-[#96938c] focus:border-[#5645d4] focus:ring-2 focus:ring-[#d6b6f6] disabled:cursor-not-allowed disabled:bg-[#f6f5f4] disabled:text-[#787671]"
            placeholder="例如：把第二天改成亲子路线，并减少步行安排"
          />
          <div class="mt-3 flex flex-wrap gap-2">
            <button type="submit" :disabled="isOperating || !revisionInstruction.trim()" class="rounded-md bg-[#5645d4] px-4 py-2 text-sm font-medium text-white outline-none hover:bg-[#4534b3] focus-visible:ring-2 focus-visible:ring-[#d6b6f6] disabled:cursor-not-allowed disabled:bg-[#e5e3df] disabled:text-[#bbb8b1]">
              {{ isOperating && operation === 'revise' ? '调整生成中...' : '生成调整后的新行程' }}
            </button>
            <button v-if="isOperating && operation === 'revise'" type="button" class="rounded-md border border-[#c8c4be] px-3 py-2 text-sm font-medium outline-none hover:bg-[#f6f5f4] focus-visible:ring-2 focus-visible:ring-[#d6b6f6]" @click="cancelCurrentOperation">取消调整</button>
          </div>
        </form>

        <div v-if="operation && (isOperating || operationError || isOperationCancelled)" aria-live="polite" class="rounded-xl border border-[#e5e3df] bg-white p-5">
          <p class="text-xs font-semibold uppercase" :class="operationError ? 'text-[#a02e6d]' : 'text-[#5645d4]'">
            {{ isOperating ? (operation === 'revise' ? '调整生成中' : '重新生成中') : isOperationCancelled ? (operation === 'revise' ? '已取消调整' : '已取消重新生成') : (operation === 'revise' ? '调整失败' : '重新生成失败') }}
          </p>
          <h2 class="mt-2 text-xl font-semibold">
            {{ isOperating ? (operation === 'revise' ? '正在根据你的要求创建新行程。' : '正在创建新的行程版本。') : isOperationCancelled ? '操作已取消，原行程未受影响。' : '新的行程没有生成成功，原行程未受影响。' }}
          </h2>
          <p v-if="operationError" class="mt-3 rounded-md border border-[#e03131]/30 bg-[#fde0ec] px-3 py-2 text-sm font-medium text-[#a02e6d]">{{ operationError }}</p>
          <dl class="mt-4 grid gap-3 text-sm sm:grid-cols-2">
            <div class="rounded-lg bg-[#f6f5f4] px-3 py-2">
              <dt class="text-xs font-semibold text-[#787671]">Trace ID</dt>
              <dd class="mt-1 break-all font-medium text-[#1a1a1a]">{{ operationTraceId || '未返回' }}</dd>
            </div>
            <div class="rounded-lg bg-[#f6f5f4] px-3 py-2">
              <dt class="text-xs font-semibold text-[#787671]">当前状态</dt>
              <dd class="mt-1 font-medium text-[#1a1a1a]">{{ operationSteps[operationSteps.length - 1] || '尚未收到阶段状态' }}</dd>
            </div>
          </dl>
          <ul v-if="operationSteps.length" class="ml-1 mt-4 space-y-1 border-l border-[#c8c4be] text-sm leading-6 text-[#5d5b54]">
            <li v-for="(step, index) in operationSteps.slice(-4)" :key="`${index}-${step}`" class="relative pl-4">
              <span aria-hidden="true" class="absolute -left-[5px] top-2 h-2 w-2 rounded-full bg-[#5645d4]" />
              {{ step }}
            </li>
          </ul>
        </div>

        <div v-if="manualCopyMarkdown" class="rounded-xl border border-[#e5e3df] bg-white p-5">
          <label for="manual-copy-markdown" class="text-sm font-medium text-[#1a1a1a]">手动复制 Markdown</label>
          <textarea
            id="manual-copy-markdown"
            ref="manualCopyMarkdownTextarea"
            readonly
            tabindex="-1"
            :value="manualCopyMarkdown"
            class="mt-3 min-h-48 w-full rounded-md border border-[#c8c4be] bg-[#f6f5f4] px-3 py-2 text-sm text-[#1a1a1a]"
          />
        </div>

        <TripPlanResult :plan="trip.plan_json" />
      </div>
    </section>
  </main>
</template>
