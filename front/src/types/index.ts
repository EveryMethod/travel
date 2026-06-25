export type BudgetLevel = 'low' | 'medium' | 'high'

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
  budget: BudgetLevel
  travel_style: TravelStyle
  month: string
  notes: string
}

export interface TripDay {
  day: number
  title: string
  theme: string
  morning: string
  afternoon: string
  evening: string
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
