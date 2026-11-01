import { render, screen, waitFor } from '@testing-library/react'
import userEvent from '@testing-library/user-event'
import { afterEach, beforeEach, describe, expect, it, vi } from 'vitest'
import App from './App'

const monitor = {
  id: 7,
  name: 'Payments API',
  url: 'https://pay.example.com/health',
  interval_s: 300,
  active: true,
  created_at: '2026-01-01T00:00:00+00:00',
  last_check: {
    id: 3,
    monitor_id: 7,
    ok: true,
    status_code: 200,
    latency_ms: 41.2,
    error: null,
    checked_at: new Date().toISOString(),
  },
  uptime_pct: 98.5,
  avg_latency_ms: 48.1,
}

function mockFetch(routes: Record<string, unknown>) {
  return vi.fn(async (input: RequestInfo | URL, init?: RequestInit) => {
    const url = String(input)
    const method = init?.method ?? 'GET'
    for (const [suffix, body] of Object.entries(routes)) {
      const wanted = suffix.startsWith('POST') ? 'POST' : 'GET'
      if (url.endsWith(suffix) && method === wanted) {
        return new Response(JSON.stringify(body), {
          status: 200,
          headers: { 'Content-Type': 'application/json' },
        })
      }
    }
    if (url.endsWith('/api/monitors') && method === 'POST') {
      return new Response(JSON.stringify(monitor), { status: 201 })
    }
    if (url.endsWith('/api/monitors/7/check')) {
      return new Response(JSON.stringify(monitor.last_check), { status: 201 })
    }
    if (url.endsWith('/api/status')) {
      return new Response(JSON.stringify({ monitors: 1, up: 1, down: 0, unknown: 0 }), {
        status: 200,
      })
    }
    if (url.endsWith('/api/monitors')) {
      return new Response(JSON.stringify([monitor]), { status: 200 })
    }
    return new Response('{}', { status: 200 })
  })
}

describe('App', () => {
  beforeEach(() => {
    vi.stubGlobal(
      'fetch',
      mockFetch({
        '/api/monitors': [monitor],
        '/api/status': { monitors: 1, up: 1, down: 0, unknown: 0 },
      }),
    )
  })

  afterEach(() => {
    vi.unstubAllGlobals()
    vi.restoreAllMocks()
  })

  it('renders the heading and tagline', async () => {
    render(<App />)
    expect(screen.getByRole('heading', { name: 'UptimeKit' })).toBeInTheDocument()
    expect(await screen.findByText(/self-hosted uptime/i)).toBeInTheDocument()
  })

  it('lists monitors returned by the API', async () => {
    render(<App />)
    expect(await screen.findByText('Payments API')).toBeInTheDocument()
    expect(screen.getByText('https://pay.example.com/health')).toBeInTheDocument()
  })

  it('shows the aggregate summary counts', async () => {
    render(<App />)
    await screen.findByText('Payments API')
    const summary = screen.getByRole('region', { name: 'Summary' })
    expect(summary).toHaveTextContent('1monitors')
  })

  it('renders uptime and latency metrics', async () => {
    render(<App />)
    await screen.findByText('Payments API')
    expect(screen.getByText('98.5%')).toBeInTheDocument()
    expect(screen.getByText('48 ms')).toBeInTheDocument()
  })

  it('submits a new monitor and clears the form', async () => {
    const user = userEvent.setup()
    render(<App />)
    await screen.findByText('Payments API')

    await user.type(screen.getByLabelText('Monitor name'), 'Docs')
    await user.type(screen.getByLabelText('Monitor URL'), 'https://docs.example.com')
    await user.click(screen.getByRole('button', { name: 'Add monitor' }))

    await waitFor(() =>
      expect((screen.getByLabelText('Monitor name') as HTMLInputElement).value).toBe(''),
    )
  })

  it('shows an empty state when there are no monitors', async () => {
    vi.stubGlobal(
      'fetch',
      mockFetch({
        '/api/monitors': [],
        '/api/status': { monitors: 0, up: 0, down: 0, unknown: 0 },
      }),
    )
    render(<App />)
    expect(await screen.findByText(/no monitors yet/i)).toBeInTheDocument()
  })
})
