/** Typed API client and shared domain types. */

export type Check = {
  id: number
  monitor_id: number
  ok: boolean
  status_code: number | null
  latency_ms: number | null
  error: string | null
  checked_at: string
}

export type Monitor = {
  id: number
  name: string
  url: string
  interval_s: number
  active: boolean
  created_at: string
  last_check: Check | null
  uptime_pct: number | null
  avg_latency_ms: number | null
}

export type StatusSummary = {
  monitors: number
  up: number
  down: number
  unknown: number
}

export type NewMonitor = {
  name: string
  url: string
  interval_s: number
}

const BASE = '/api'

async function request<T>(path: string, init?: RequestInit): Promise<T> {
  const response = await fetch(`${BASE}${path}`, {
    headers: { 'Content-Type': 'application/json' },
    ...init,
  })
  if (!response.ok) {
    let detail = `HTTP ${response.status}`
    try {
      const body = await response.json()
      if (typeof body.detail === 'string') detail = body.detail
    } catch {
      /* response had no JSON body - keep the status text */
    }
    throw new Error(detail)
  }
  if (response.status === 204) return undefined as T
  return (await response.json()) as T
}

export const api = {
  listMonitors: () => request<Monitor[]>('/monitors'),
  status: () => request<StatusSummary>('/status'),
  createMonitor: (payload: NewMonitor) =>
    request<Monitor>('/monitors', { method: 'POST', body: JSON.stringify(payload) }),
  deleteMonitor: (id: number) => request<void>(`/monitors/${id}`, { method: 'DELETE' }),
  toggleMonitor: (id: number, active: boolean) =>
    request<Monitor>(`/monitors/${id}`, {
      method: 'PATCH',
      body: JSON.stringify({ active }),
    }),
  runCheck: (id: number) => request<Check>(`/monitors/${id}/check`, { method: 'POST' }),
  history: (id: number, limit = 30) =>
    request<Check[]>(`/monitors/${id}/checks?limit=${limit}`),
}

/** A monitor is "up" when its most recent probe succeeded. */
export function healthOf(monitor: Monitor): 'up' | 'down' | 'unknown' {
  if (!monitor.last_check) return 'unknown'
  return monitor.last_check.ok ? 'up' : 'down'
}

/** Format a latency in ms for display, tolerating nulls. */
export function formatLatency(value: number | null): string {
  if (value === null) return '—'
  return value < 10 ? `${value.toFixed(1)} ms` : `${Math.round(value)} ms`
}

/** Format a percentage to one decimal, tolerating nulls. */
export function formatUptime(value: number | null): string {
  if (value === null) return '—'
  return `${value.toFixed(1)}%`
}

/** Render an ISO timestamp as a compact relative age. */
export function relativeTime(iso: string | null, now = Date.now()): string {
  if (!iso) return 'never'
  const delta = now - new Date(iso).getTime()
  if (Number.isNaN(delta)) return 'never'
  const seconds = Math.max(0, Math.floor(delta / 1000))
  if (seconds < 60) return `${seconds}s ago`
  const minutes = Math.floor(seconds / 60)
  if (minutes < 60) return `${minutes}m ago`
  const hours = Math.floor(minutes / 60)
  if (hours < 24) return `${hours}h ago`
  return `${Math.floor(hours / 24)}d ago`
}
