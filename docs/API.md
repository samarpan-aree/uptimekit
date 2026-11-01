# API

Base URL: `http://localhost:8000`. Interactive docs at `/docs` (Swagger) and `/redoc`.

| Method | Path | Purpose |
| --- | --- | --- |
| `GET` | `/api/health` | Liveness of UptimeKit itself |
| `GET` | `/api/status` | Counts of up / down / unchecked monitors |
| `GET` | `/api/monitors` | List monitors with health rollups |
| `POST` | `/api/monitors` | Register a monitor |
| `GET` | `/api/monitors/{id}` | Single monitor with last check |
| `PATCH` | `/api/monitors/{id}` | Update name, interval, or active state |
| `DELETE` | `/api/monitors/{id}` | Remove a monitor and its history |
| `POST` | `/api/monitors/{id}/check` | Probe now and record the result |
| `GET` | `/api/monitors/{id}/checks` | Recent history (`?limit=`, 1–500) |
| `GET` | `/api/monitors/{id}/badge` | Uptime badge text |

## Walkthrough

```bash
# register an endpoint
curl -X POST localhost:8000/api/monitors \
  -H 'Content-Type: application/json' \
  -d '{"name":"Payments API","url":"https://api.example.com/health","interval_s":300}'

# probe it now
curl -X POST localhost:8000/api/monitors/1/check

# read the rollup
curl localhost:8000/api/monitors/1
```

The monitor response carries the last check plus two derived fields:

```json
{
  "id": 1,
  "name": "Payments API",
  "url": "https://api.example.com/health",
  "interval_s": 300,
  "active": true,
  "uptime_pct": 98.5,
  "avg_latency_ms": 48.1,
  "last_check": {
    "ok": true,
    "status_code": 200,
    "latency_ms": 41.2,
    "error": null,
    "checked_at": "2026-11-01T11:20:00+00:00"
  }
}
```

## Validation

`POST /api/monitors` rejects with `422` when:

- `name` is blank or longer than 80 characters
- `url` is not a valid http(s) URL
- `interval_s` is outside 30–86,400

## Badge

`GET /api/monitors/{id}/badge` returns plain text in shields.io endpoint format, so it can drive a README badge:

```
100.0%25%20uptime-brightgreen
```

Colour bands: `brightgreen` at 99.5%+, `green` at 98%+, `orange` below that. Returns `unknown` when no probe has run yet.
