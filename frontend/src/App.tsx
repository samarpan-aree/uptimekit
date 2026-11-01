import { useEffect, useState } from 'react'
import { api, type Monitor, type NewMonitor, type StatusSummary } from './api'
import { MonitorRow } from './MonitorRow'
import './styles.css'

const BLANK: NewMonitor = { name: '', url: '', interval_s: 300 }

export default function App() {
  const [monitors, setMonitors] = useState<Monitor[]>([])
  const [summary, setSummary] = useState<StatusSummary | null>(null)
  const [draft, setDraft] = useState<NewMonitor>(BLANK)
  const [error, setError] = useState<string | null>(null)
  const [loading, setLoading] = useState(true)

  async function refresh() {
    try {
      const [list, counts] = await Promise.all([api.listMonitors(), api.status()])
      setMonitors(list)
      setSummary(counts)
      setError(null)
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Could not reach the API')
    } finally {
      setLoading(false)
    }
  }

  useEffect(() => {
    void refresh()
  }, [])

  async function add(event: React.FormEvent) {
    event.preventDefault()
    if (!draft.name.trim() || !draft.url.trim()) return
    try {
      await api.createMonitor({ ...draft, name: draft.name.trim() })
      setDraft(BLANK)
      await refresh()
    } catch (err) {
      setError(err instanceof Error ? err.message : 'Could not create monitor')
    }
  }

  return (
    <div className="shell">
      <header className="top">
        <h1>UptimeKit</h1>
        <button className="ghost" onClick={() => void refresh()}>
          Refresh
        </button>
      </header>
      <p className="tagline">Self-hosted uptime and latency monitoring for your APIs.</p>

      {error && <div className="error-banner">{error}</div>}

      <section className="summary" aria-label="Summary">
        <div className="stat">
          <div className="value">{summary?.monitors ?? 0}</div>
          <div className="label">monitors</div>
        </div>
        <div className="stat up">
          <div className="value">{summary?.up ?? 0}</div>
          <div className="label">up</div>
        </div>
        <div className="stat down">
          <div className="value">{summary?.down ?? 0}</div>
          <div className="label">down</div>
        </div>
        <div className="stat">
          <div className="value">{summary?.unknown ?? 0}</div>
          <div className="label">unchecked</div>
        </div>
      </section>

      <form className="add" onSubmit={add}>
        <input
          name="name"
          placeholder="Name (e.g. Payments API)"
          value={draft.name}
          onChange={(e) => setDraft({ ...draft, name: e.target.value })}
          aria-label="Monitor name"
        />
        <input
          name="url"
          placeholder="https://api.example.com/health"
          value={draft.url}
          onChange={(e) => setDraft({ ...draft, url: e.target.value })}
          aria-label="Monitor URL"
        />
        <select
          name="interval"
          value={draft.interval_s}
          onChange={(e) => setDraft({ ...draft, interval_s: Number(e.target.value) })}
          aria-label="Check interval"
        >
          <option value={60}>every 1 min</option>
          <option value={300}>every 5 min</option>
          <option value={900}>every 15 min</option>
          <option value={3600}>every hour</option>
        </select>
        <button type="submit">Add monitor</button>
      </form>

      {loading ? (
        <div className="empty">Loading…</div>
      ) : monitors.length === 0 ? (
        <div className="empty">
          No monitors yet. Add your first endpoint above to start tracking uptime.
        </div>
      ) : (
        <ul className="monitors">
          {monitors.map((monitor) => (
            <MonitorRow key={monitor.id} monitor={monitor} onChanged={refresh} />
          ))}
        </ul>
      )}

      <footer>UptimeKit 1.0.0 — MIT licensed</footer>
    </div>
  )
}
