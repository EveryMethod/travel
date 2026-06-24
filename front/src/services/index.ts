import type { TripPlanRequest, TripPlanResponse } from '@/types'

export async function planTrip(payload: TripPlanRequest): Promise<TripPlanResponse> {
  let response: Response

  try {
    response = await fetch('/api/trips/plan', {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
      },
      body: JSON.stringify(payload),
    })
  } catch {
    throw new Error('无法连接旅行规划 API，请确认后端服务正在运行。')
  }

  if (!response.ok) {
    throw new Error(await getErrorMessage(response))
  }

  return response.json() as Promise<TripPlanResponse>
}

async function getErrorMessage(response: Response): Promise<string> {
  const contentType = response.headers.get('content-type') ?? ''
  const body = await response.text()

  if (contentType.includes('application/json') && body) {
    try {
      const data = JSON.parse(body) as { detail?: unknown }

      if (typeof data.detail === 'string') {
        return data.detail
      }

      if (Array.isArray(data.detail)) {
        return '部分旅行信息不符合要求，请检查表单后重试。'
      }
    } catch {
      // Fall through to status-based messages.
    }
  }

  if (response.status === 422) {
    return '部分旅行信息不符合要求，请检查表单后重试。'
  }

  if (response.status === 500 && contentType.includes('text/plain') && body.trim() === '') {
    return '无法连接旅行规划 API，请确认后端服务正在运行。'
  }

  return '规划器暂时无法生成行程，请稍后重试。'
}
