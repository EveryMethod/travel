export type TravelStyle =
  | 'culture'
  | 'food'
  | 'nature'
  | 'family'
  | 'romantic'
  | 'adventure'
  | 'relaxed'

export interface TripPlanRequest {
  destination: string
  origin: string
  days: number
  budget: string
  travel_style: TravelStyle[]
  start_date: string
  end_date: string
  notes: string
}

export interface TripPlanItem {
  time: string
  place: string
  activity: string
  estimated_cost: string
  booking_hint: string
  source_hint: string
}

export interface TripDay {
  day: number
  date: string
  title: string
  weather: string
  items: TripPlanItem[]
  daily_budget: string
  transport: string
  notes: string[]
}

export interface TripPlanResponse {
  trip_id: string
  destination: string
  summary: string
  days: TripDay[]
  tips: string[]
  disclaimer: string
}

export type OAuthProvider = 'qq' | 'wechat'

export interface AuthUser {
  id: number
  display_name: string
  avatar_url: string | null
}

export interface AuthTokens {
  access_token: string
  refresh_token: string
  token_type: string
  expires_in: number
}

export interface AuthResponse {
  user: AuthUser
  tokens: AuthTokens
}

export interface RegisterRequest {
  display_name: string
  password: string
  email?: string
  username?: string
}

export interface LoginRequest {
  account: string
  password: string
}

export interface RefreshRequest {
  refresh_token: string
}

export interface OAuthAuthorizeResponse {
  authorization_url: string
  state: string
}
