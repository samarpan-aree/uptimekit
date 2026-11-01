# UptimeKit

**Self-hosted API uptime and latency monitoring. FastAPI + React + SQLite, no external services.**

[![CI](https://github.com/ROYAL-SMP/uptimekit/actions/workflows/ci.yml/badge.svg)](https://github.com/ROYAL-SMP/uptimekit/actions/workflows/ci.yml)
[![Python](https://img.shields.io/badge/python-3.10%E2%80%933.12-blue)](https://www.python.org/)
[![React](https://img.shields.io/badge/react-18-61dafb)](https://react.dev/)
[![License: MIT](https://img.shields.io/badge/license-MIT-green.svg)](LICENSE)
[![Tests](https://img.shields.io/badge/tests-65%20passing-brightgreen)](backend/tests)

SaaS uptime monitors charge per check and keep your probe history behind a paywall. UptimeKit inverts that: one container, one SQLite file, every probe you have ever taken, yours to query. It records status codes and latency per endpoint, rolls them into an uptime percentage, and exposes a badge endpoint you can drop straight into a README.

```mermaid
flowchart LR
    UI[React dashboard] -->|JSON over /api| R[routes main.py]
    R --> SCH[contracts schemas.py]
    R --> REPO[queries repository.py]
    R --> P[prober probe.py]
    REPO --> DB[(SQLite monitors + checks)]
    P -->|HTTP GET| TARGET[monitored endpoint]
```

## Features

- **Monitor CRUD** — register any HTTP endpoint with its own check interval (30s–24h).
- **Explicit probing** — `POST /api/monitors/{id}/check` runs a probe now and stores it. No hidden timer you cannot observe.
- **Honest failure capture** — timeouts, DNS and TLS errors are recorded as failed checks with the reason, never swallowed.
- **Rolling uptime** — percentage of successful probes and mean latency, computed from real history.
- **Badge endpoint** — `GET /api/monitors/{id}/badge` returns shields.io endpoint text.
- **Pause without deleting** — stop probing an endpoint while keeping its history.

## Quick start

```bash
docker compose up --build     # UI :5173, API :8000
```

Without Docker:

```bash
cd backend && pip install -e ".[dev]" && uvicorn app.main:app --reload --port 8000
cd frontend && npm install && npm run dev
```

Vite proxies `/api` to port 8000, so there is no CORS setup in development.
