import type {
  AuthResponse,
  AuthTokens,
  LoginRequest,
  OAuthAuthorizeResponse,
  OAuthProvider,
  RefreshRequest,
  RegisterRequest,
  TripPlanRequest,
  TripPlanResponse,
} from '@/types'

const AUTH_TOKEN_KEY = 'travel_auth_tokens'

export async function planTrip(payload: TripPlanRequest): Promise<TripPlanResponse> {
  return request<TripPlanResponse>('/api/trips/plan', {
    method: 'POST',
    body: payload,
  })
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
  if (tokens) {
    await request('/api/auth/logout', {
      method: 'POST',
      body: {
        access_token: tokens.access_token,
        refresh_token: tokens.refresh_token,
      },
    })
  }
  clearAuthTokens()
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

  try {
    response = await fetch(url, {
      method: options.method ?? 'GET',
      headers: {
        ...(options.body === undefined ? {} : { 'Content-Type': 'application/json' }),
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

  return '请求失败，请稍后重试。'
}
