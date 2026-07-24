import type {
  AuthResponse,
  AuthTokens,
  LoginRequest,
  OAuthAuthorizeResponse,
  OAuthProvider,
  RefreshRequest,
  RegisterRequest,
  SavedTripDetail,
  SavedTripListItem,
  TripPlanRequest,
  TripPlanResponse,
  TripRevisionRequest,
  TripStreamEvent,
} from '@/types'

const AUTH_TOKEN_KEY = 'travel_auth_tokens'

export async function planTripStream(
  payload: TripPlanRequest,
  onEvent: (event: TripStreamEvent) => void,
  options: { signal?: AbortSignal } = {},
): Promise<TripPlanResponse> {
  return streamTrip('/api/trips/plan/stream', payload, onEvent, options)
}

export async function reviseTripStream(
  tripId: number | string,
  payload: TripRevisionRequest,
  onEvent: (event: TripStreamEvent) => void,
  options: { signal?: AbortSignal } = {},
): Promise<TripPlanResponse> {
  return streamTrip(`/api/trips/${tripId}/revise/stream`, payload, onEvent, options)
}

async function streamTrip(
  url: string,
  payload: TripPlanRequest | TripRevisionRequest,
  onEvent: (event: TripStreamEvent) => void,
  options: { signal?: AbortSignal },
): Promise<TripPlanResponse> {
  let response: Response
  const tokens = getAuthTokens()

  try {
    response = await fetch(url, {
      method: 'POST',
      headers: {
        'Content-Type': 'application/json',
        ...(tokens ? { Authorization: `Bearer ${tokens.access_token}` } : {}),
      },
      body: JSON.stringify(payload),
      signal: options.signal,
    })
  } catch (caughtError) {
    if (isAbortError(caughtError)) {
      throw caughtError
    }
    throw new Error('无法连接后端 API，请确认服务正在运行。')
  }

  if (!response.ok || !response.body) {
    const traceId = response.headers.get('X-Trace-Id')
    if (traceId) {
      onEvent({ type: 'trace', trace_id: traceId })
    }
    throw new Error(await getErrorMessage(response))
  }

  const reader = response.body.pipeThrough(new TextDecoderStream()).getReader()
  let buffer = ''
  let plan: TripPlanResponse | null = null
  let finished = false

  const handleLine = (line: string) => {
    if (!line.trim()) return
    const event = parseTripStreamEvent(line)
    onEvent(event)
    if (event.type === 'error') {
      throw new Error(event.message ?? '规划器暂时无法生成行程。')
    }
    if (event.type === 'plan') {
      plan = event.data
    }
  }

  try {
    for (;;) {
      const { value, done } = await reader.read()
      if (done) {
        finished = true
        break
      }

      buffer += value
      const lines = buffer.split('\n')
      buffer = lines.pop() ?? ''

      for (const line of lines) {
        handleLine(line)
      }
    }

    if (buffer.trim()) {
      handleLine(buffer)
    }
  } finally {
    if (!finished) {
      try {
        await reader.cancel()
      } catch {
        // Reader cleanup is best-effort; preserve the original stream error.
      }
    }
    reader.releaseLock()
  }

  if (!plan) {
    throw new Error('规划器暂时没有返回完整行程。')
  }
  return plan
}

export function isAbortError(error: unknown): boolean {
  return error instanceof Error && error.name === 'AbortError'
}

function parseTripStreamEvent(line: string): TripStreamEvent {
  try {
    return JSON.parse(line) as TripStreamEvent
  } catch {
    throw new Error('规划器返回了无法解析的进度数据，请稍后重试。')
  }
}

export async function listTrips(): Promise<SavedTripListItem[]> {
  return request<SavedTripListItem[]>('/api/trips')
}

export async function getTrip(id: number | string): Promise<SavedTripDetail> {
  return request<SavedTripDetail>(`/api/trips/${id}`)
}

export async function deleteTrip(id: number | string): Promise<void> {
  await request<void>(`/api/trips/${id}`, { method: 'DELETE' })
}

export function refreshTripTransport(tripId: number | string): Promise<TripPlanResponse> {
  return request<TripPlanResponse>(`/api/trips/${tripId}/transport/refresh`, { method: 'POST' })
}

export async function register(payload: RegisterRequest, remember: boolean): Promise<AuthResponse> {
  const auth = await request<AuthResponse>('/api/auth/register', {
    method: 'POST',
    body: payload,
  })
  saveAuthTokens(auth.tokens, remember)
  return auth
}

export async function login(payload: LoginRequest, remember: boolean): Promise<AuthResponse> {
  const auth = await request<AuthResponse>('/api/auth/login', {
    method: 'POST',
    body: payload,
  })
  saveAuthTokens(auth.tokens, remember)
  return auth
}

export async function getOAuthAuthorizeUrl(provider: OAuthProvider): Promise<OAuthAuthorizeResponse> {
  return request<OAuthAuthorizeResponse>(`/api/auth/oauth/${provider}/authorize`)
}

export async function completeOAuthLogin(
  provider: OAuthProvider,
  code: string,
  state: string,
  remember: boolean,
): Promise<AuthResponse> {
  const params = new URLSearchParams({ code, state })
  const auth = await request<AuthResponse>(`/api/auth/oauth/${provider}/callback?${params.toString()}`)
  saveAuthTokens(auth.tokens, remember)
  return auth
}

export async function refreshAuth(): Promise<AuthResponse> {
  const tokens = getAuthTokens()
  if (!tokens) {
    throw new Error('登录状态已失效，请重新登录。')
  }

  const payload: RefreshRequest = { refresh_token: tokens.refresh_token }
  const auth = await request<AuthResponse>('/api/auth/refresh', {
    method: 'POST',
    body: payload,
  })
  saveAuthTokens(auth.tokens, isAuthRemembered())
  return auth
}

export async function logout(): Promise<void> {
  const tokens = getAuthTokens()
  try {
    if (tokens) {
      await request('/api/auth/logout', {
        method: 'POST',
        body: {
          access_token: tokens.access_token,
          refresh_token: tokens.refresh_token,
        },
      })
    }
  } catch {
    // ponytail: logout is best-effort; local tokens must clear even if backend is down.
  } finally {
    clearAuthTokens()
  }
}

export function getAuthTokens(): AuthTokens | null {
  return readTokens(localStorage) ?? readTokens(sessionStorage)
}

export function saveAuthTokens(tokens: AuthTokens, remember: boolean): void {
  const target = remember ? localStorage : sessionStorage
  const stale = remember ? sessionStorage : localStorage

  target.setItem(AUTH_TOKEN_KEY, JSON.stringify(tokens))
  stale.removeItem(AUTH_TOKEN_KEY)
}

export function clearAuthTokens(): void {
  localStorage.removeItem(AUTH_TOKEN_KEY)
  sessionStorage.removeItem(AUTH_TOKEN_KEY)
}

export function isAuthRemembered(): boolean {
  return localStorage.getItem(AUTH_TOKEN_KEY) !== null
}

async function request<T = unknown>(
  url: string,
  options: { method?: string; body?: unknown; headers?: HeadersInit } = {},
): Promise<T> {
  let response: Response
  const tokens = getAuthTokens()

  try {
    response = await fetch(url, {
      method: options.method ?? 'GET',
      headers: {
        ...(options.body === undefined ? {} : { 'Content-Type': 'application/json' }),
        ...(tokens ? { Authorization: `Bearer ${tokens.access_token}` } : {}),
        ...options.headers,
      },
      body: options.body === undefined ? undefined : JSON.stringify(options.body),
    })
  } catch {
    throw new Error('无法连接后端 API，请确认服务正在运行。')
  }

  if (!response.ok) {
    throw new Error(await getErrorMessage(response))
  }

  if (response.status === 204) {
    return undefined as T
  }

  return response.json() as Promise<T>
}

function readTokens(storage: Storage): AuthTokens | null {
  const value = storage.getItem(AUTH_TOKEN_KEY)
  if (!value) return null

  try {
    return JSON.parse(value) as AuthTokens
  } catch {
    storage.removeItem(AUTH_TOKEN_KEY)
    return null
  }
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
        return '部分信息不符合要求，请检查后重试。'
      }
    } catch {
      // Fall through to status-based messages.
    }
  }

  if (response.status === 422) {
    return '部分信息不符合要求，请检查后重试。'
  }

  if (response.status === 500 && contentType.includes('text/plain') && body.trim() === '') {
    return '无法连接后端 API，请确认服务正在运行。'
  }

  const detail = body.trim().slice(0, 160)
  return detail ? `请求失败（HTTP ${response.status}）：${detail}` : `请求失败（HTTP ${response.status}），请稍后重试。`
}
