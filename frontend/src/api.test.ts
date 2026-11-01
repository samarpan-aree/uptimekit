import { describe, expect, it } from 'vitest'
import {
  formatLatency,
  formatUptime,
  healthOf,
  relativeTime,
  type Monitor,
} from './api'

function makeMonitor(overrides: Partial<Monitor> = {}): Monitor {
  return {
    id: 1,
    name: 'API',
    url: 'https://example.com',
    interval_s: 300,
    active: true,
    created_at: '2026-01-01T00:00:00+00:00',
    last_check: null,
    uptime_pct: null,
    avg_latency_ms: null,
    ...overrides,
  }
}

const OK_CHECK = {
  id: 1,
  monitor_id: 1,
  ok: true,
  status_code: 200,
  latency_ms: 12,
  error: null,
  checked_at: '2026-01-01T00:00:00+00:00',
}

describe('healthOf', () => {
  it('is unknown when never checked', () => {
    expect(healthOf(makeMonitor())).toBe('unknown')
  })

  it('is up when the last probe succeeded', () => {
    expect(healthOf(makeMonitor({ last_check: OK_CHECK }))).toBe('up')
  })

  it('is down when the last probe failed', () => {
    const failed = { ...OK_CHECK, ok: false, status_code: 500 }
    expect(healthOf(makeMonitor({ last_check: failed }))).toBe('down')
  })
})

describe('formatLatency', () => {
  it('renders an em dash for null', () => {
    expect(formatLatency(null)).toBe('—')
  })

  it('keeps one decimal below 10ms', () => {
    expect(formatLatency(4.25)).toBe('4.3 ms')
  })

  it('rounds to whole milliseconds above 10ms', () => {
    expect(formatLatency(142.7)).toBe('143 ms')
  })
})

describe('formatUptime', () => {
  it('renders an em dash for null', () => {
    expect(formatUptime(null)).toBe('—')
  })

  it('always shows one decimal', () => {
    expect(formatUptime(100)).toBe('100.0%')
    expect(formatUptime(99.956)).toBe('100.0%')
    expect(formatUptime(0)).toBe('0.0%')
  })
})

describe('relativeTime', () => {
  const now = new Date('2026-01-01T12:00:00Z').getTime()

  it('says never for null or invalid input', () => {
    expect(relativeTime(null, now)).toBe('never')
    expect(relativeTime('not-a-date', now)).toBe('never')
  })

  it('scales from seconds to days', () => {
    expect(relativeTime('2026-01-01T11:59:30Z', now)).toBe('30s ago')
    expect(relativeTime('2026-01-01T11:55:00Z', now)).toBe('5m ago')
    expect(relativeTime('2026-01-01T09:00:00Z', now)).toBe('3h ago')
    expect(relativeTime('2025-12-30T12:00:00Z', now)).toBe('2d ago')
  })

  it('never goes negative for future timestamps', () => {
    expect(relativeTime('2026-01-02T12:00:00Z', now)).toBe('0s ago')
  })
})
