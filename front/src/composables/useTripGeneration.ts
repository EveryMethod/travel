import { onUnmounted, ref } from 'vue'

import { isAbortError, planTripStream, reviseTripStream } from '@/services'
import type { TripPlanRequest, TripPlanResponse, TripRevisionRequest, TripStreamEvent } from '@/types'

type TripStreamCall = (
  onEvent: (event: TripStreamEvent) => void,
  options: { signal?: AbortSignal },
) => Promise<TripPlanResponse>

export function useTripGeneration() {
  const plan = ref<TripPlanResponse | null>(null)
  const error = ref('')
  const isGenerating = ref(false)
  const isCancelled = ref(false)
  const traceId = ref('')
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
    isCancelled.value = false
    traceId.value = ''
    streamSteps.value = []
  }

  function cancel() {
    if (!controller || !isGenerating.value) return
    isCancelled.value = true
    controller.abort()
  }

  async function run(streamCall: TripStreamCall): Promise<TripPlanResponse | null> {
    controller?.abort()
    const activeRunId = runId + 1
    runId = activeRunId
    controller = new AbortController()
    plan.value = null
    error.value = ''
    isGenerating.value = true
    isCancelled.value = false
    traceId.value = ''
    streamSteps.value = []

    try {
      const generatedPlan = await streamCall(
        (event: TripStreamEvent) => {
          if (activeRunId !== runId) return
          if (event.type === 'trace') {
            traceId.value = event.trace_id
          }
          if (event.type === 'status') {
            streamSteps.value = [...streamSteps.value, event.message].slice(-4)
          }
          if (event.type === 'plan') {
            plan.value = event.data
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

  function generate(payload: TripPlanRequest): Promise<TripPlanResponse | null> {
    return run((onEvent, options) => planTripStream(payload, onEvent, options))
  }

  function revise(tripId: number | string, payload: TripRevisionRequest): Promise<TripPlanResponse | null> {
    return run((onEvent, options) => reviseTripStream(tripId, payload, onEvent, options))
  }

  onUnmounted(() => cancel())

  return {
    plan,
    error,
    isGenerating,
    isCancelled,
    traceId,
    streamSteps,
    generate,
    revise,
    cancel,
    reset,
  }
}
