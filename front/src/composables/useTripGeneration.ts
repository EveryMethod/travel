import { onUnmounted, ref } from 'vue'

import { isAbortError, planTripStream } from '@/services'
import type { TripPlanRequest, TripPlanResponse, TripStreamEvent } from '@/types'

export function useTripGeneration(onStatus?: (message: string) => void) {
  const plan = ref<TripPlanResponse | null>(null)
  const error = ref('')
  const isGenerating = ref(false)
  const isComplete = ref(false)
  const isCancelled = ref(false)
  const traceId = ref('')
  const lastStatus = ref('')
  const streamSteps = ref<string[]>([])

  let controller: AbortController | null = null
  let runId = 0

  function reset() {
    controller?.abort()
    controller = null
    runId += 1
    plan.value = null
    error.value = ''
    isGenerating.value = false
    isComplete.value = false
    isCancelled.value = false
    traceId.value = ''
    lastStatus.value = ''
    streamSteps.value = []
  }

  function cancel() {
    if (!controller || !isGenerating.value) return
    isCancelled.value = true
    controller.abort()
  }

  async function generate(payload: TripPlanRequest): Promise<TripPlanResponse | null> {
    controller?.abort()
    const activeRunId = runId + 1
    runId = activeRunId
    controller = new AbortController()
    plan.value = null
    error.value = ''
    isGenerating.value = true
    isComplete.value = false
    isCancelled.value = false
    traceId.value = ''
    lastStatus.value = ''
    streamSteps.value = []

    try {
      const generatedPlan = await planTripStream(
        payload,
        (event: TripStreamEvent) => {
          if (activeRunId !== runId) return
          if (event.type === 'trace') {
            traceId.value = event.trace_id
          }
          if (event.type === 'status') {
            lastStatus.value = event.message
            streamSteps.value = [...streamSteps.value, event.message].slice(-4)
            onStatus?.(event.message)
          }
          if (event.type === 'plan') {
            plan.value = event.data
          }
          if (event.type === 'done') {
            isComplete.value = true
          }
        },
        { signal: controller.signal },
      )
      if (activeRunId !== runId) return null
      plan.value = generatedPlan
      return generatedPlan
    } catch (caughtError) {
      if (activeRunId !== runId) return null
      if (isAbortError(caughtError)) {
        if (plan.value) {
          isComplete.value = true
          isCancelled.value = false
          error.value = ''
          return plan.value
        }
        isCancelled.value = true
        error.value = ''
        return null
      }
      error.value = caughtError instanceof Error ? caughtError.message : '规划器暂时无法生成行程。'
      return null
    } finally {
      if (activeRunId === runId) {
        isGenerating.value = false
        controller = null
      }
    }
  }

  onUnmounted(() => cancel())

  return {
    plan,
    error,
    isGenerating,
    isComplete,
    isCancelled,
    traceId,
    lastStatus,
    streamSteps,
    generate,
    cancel,
    reset,
  }
}
