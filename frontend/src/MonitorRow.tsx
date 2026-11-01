import { useState } from 'react'
import {
  api,
  formatLatency,
  formatUptime,
  healthOf,
  relativeTime,
  type Monitor,
} from './api'

type Props = {
  monitor: Monitor
  onChanged: () => void
}

/** One monitor row: status, metrics, and actions. */
export function MonitorRow({ monitor, onChanged }: Props) {
  const [busy, setBusy] = useState(false)
  const health = healthOf(monitor)

  async function runCheck() {
    setBusy(true)
    try {
      await api.runCheck(monitor.id)
      onChanged()
    } finally {
      setBusy(false)
    }
  }

  async function toggle() {
    setBusy(true)
    try {
      await api.toggleMonitor(monitor.id, !monitor.active)
      onChanged()
    } finally {
      setBusy(false)
    }
  }

  async function remove() {
    setBusy(true)
    try {
      await api.deleteMonitor(monitor.id)
      onChanged()
    } finally {
      setBusy(false)
    }
  }

  return (
    <li className={`monitor ${health}${monitor.active ? '' : ' paused'}`}>
      <div>
        <div className="monitor-name">
          <span className="dot" aria-hidden="true" />
          {monitor.name}
          {!monitor.active && (
            <span className="mono" style={{ color: 'var(--unknown)', fontSize: 11 }}>
              paused
            </span>
          )}
        </div>
        <div className="monitor-url mono">{monitor.url}</div>
        <div className="metrics">
          <span>
            status{' '}
            <b data-testid="status">
              {health === 'unknown' ? 'not checked' : monitor.last_check?.status_code ?? '—'}
            </b>
          </span>
          <span>
            uptime <b>{formatUptime(monitor.uptime_pct)}</b>
          </span>
          <span>
            avg <b>{formatLatency(monitor.avg_latency_ms)}</b>
          </span>
          <span>
            checked <b>{relativeTime(monitor.last_check?.checked_at ?? null)}</b>
          </span>
        </div>
      </div>
      <div className="actions">
        <button onClick={runCheck} disabled={busy}>
          Probe
        </button>
        <button className="ghost" onClick={toggle} disabled={busy}>
          {monitor.active ? 'Pause' : 'Resume'}
        </button>
        <button className="ghost" onClick={remove} disabled={busy}>
          Delete
        </button>
      </div>
    </li>
  )
}
