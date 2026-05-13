export interface Meta {
  total_events: number
  total_users: number
  total_sessions: number
  time_range: { start: string | null; end: string | null }
  missing_timestamps: number
}

export interface FunnelStep {
  step: string
  sessions: number
  pct_of_total: number
  dropoff_from_prev: number
}

export interface Funnel {
  steps: FunnelStep[]
  checkout_outcomes: Record<string, number>
  checkout_conversion_rate: number
}

export interface SessionEvent {
  time: string | null
  path: string
  css: string | null
  text: string | null
  value: string | null
}

export interface Journey {
  session_id: string
  user_id: string
  start_time: string | null
  end_time: string | null
  event_count: number
  pages: string[]
  has_error: boolean
  completed_order: boolean
  events: SessionEvent[]
}

export interface Issue {
  id: string
  severity: 'critical' | 'high' | 'medium' | 'low'
  title: string
  description: string
  affected_sessions: string[]
  recommendation: string
  evidence?: unknown[]
}

export interface Behavior {
  id: string
  title: string
  description: string
  insight: string
  evidence?: unknown[]
  affected_sessions?: string[]
}

export interface Insights {
  generated_at: string
  meta: Meta
  funnel: Funnel
  journeys: {
    most_common: { path: string[]; count: number; pct: number }[]
    all: Journey[]
  }
  issues: Issue[]
  behaviors: Behavior[]
}
