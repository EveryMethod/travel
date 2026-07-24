export type TravelStyle =
  | 'culture'
  | 'food'
  | 'nature'
  | 'family'
  | 'romantic'
  | 'adventure'
  | 'relaxed'

export type TravelPace = 'relaxed' | 'balanced' | 'packed'

export type TravelCompanions = 'solo' | 'couple' | 'friends' | 'family' | 'seniors'

export type TransportMode = 'flight' | 'rail' | 'drive'

export type TransportDataQuality = 'live' | 'provider_live' | 'estimate'

export interface TravelerParty {
  adults: number
  children: number
  infants: number
}

export interface TransportSegment {
  service_number: string
  carrier: string
  departure_at: string | null
  arrival_at: string | null
  from_terminal: string
  to_terminal: string
}

export interface TransportLeg {
  direction: 'outbound' | 'return'
  departure_at: string | null
  arrival_at: string | null
  duration_minutes: number | null
  transfer_count: number
  segments: TransportSegment[]
}

export interface TransportOption {
  id: string
  mode: TransportMode
  provider: string
  data_quality: TransportDataQuality
  total_price: string
  currency: string
  estimated_price_range: string
  fare_details: string[]
  outbound: TransportLeg
  return_leg: TransportLeg
  booking_hint: string
  source_url: string
}

export interface IntercityTransportPlan {
  origin: string
  destination: string
  recommended_option_id: string | null
  recommendation_reason: string
  options: TransportOption[]
  destination_ready_at: string | null
  destination_depart_by: string | null
  searched_at: string
  warnings: string[]
}

export interface BudgetBreakdown {
  transport: string
  hotel: string
  food: string
  tickets: string
}

export interface TripPlanRequest {
  destination: string
  origin: string
  days: number
  budget: string
  budget_breakdown: BudgetBreakdown
  travel_style: TravelStyle[]
  pace: TravelPace
  companions: TravelCompanions
  start_date: string
  end_date: string
  must_see: string
  avoid: string
  notes: string
  revision_instructions?: string[]
  travelers: TravelerParty
}

export interface TripRevisionRequest {
  instruction: string
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
  intercity_transport?: IntercityTransportPlan | null
}

export interface SavedTripListItem {
  id: number
  destination: string
  days: number
  status: 'completed'
  created_at: string
}

export interface SavedTripDetail extends SavedTripListItem {
  trace_id: string | null
  request_json: TripPlanRequest
  plan_json: TripPlanResponse
  updated_at: string
}

export type TripStreamEvent =
  | { type: 'trace'; trace_id: string }
  | { type: 'status'; message: string }
  | { type: 'context'; data: unknown }
  | { type: 'plan'; data: TripPlanResponse }
  | { type: 'done' }
  | { type: 'error'; message: string }

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
