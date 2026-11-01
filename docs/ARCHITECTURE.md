# Architecture

```
uptimekit/
├── backend/app/
│   ├── db.py          # connection, schema bootstrap, transaction scope
│   ├── probe.py       # HTTP probe -> immutable Probe dataclass
│   ├── repository.py  # all SQL; no HTTP concepts
│   ├── schemas.py     # Pydantic contracts (validation lives here)
│   └── main.py        # application factory, routes, error mapping
├── backend/tests/     # 48 tests: probe, repository, API contract
├── frontend/src/
│   ├── api.ts         # typed client + pure formatters
│   ├── MonitorRow.tsx # per-monitor interaction
│   ├── App.tsx        # fetching, summary, add form
│   └── *.test.ts      # 17 tests
└── .github/workflows/ci.yml
```

Four layers, each independently testable.

## 1. `probe.py` — the only network boundary

`probe(url)` returns an immutable `Probe(ok, status_code, latency_ms, error)`. It never raises: `httpx` timeouts and transport errors become failed probes, so a dead endpoint cannot crash the caller. 2xx and 3xx count as healthy, since a redirect still proves the host is serving.

Because it is one small function, the test suite patches `httpx.get` and asserts every branch with no network access.

## 2. `repository.py` — the only module that knows SQL

Every function takes a connection as its first argument. That is what lets tests open a real SQLite file in `tmp_path` instead of mocking a database layer. Partial updates go through an allow-list (`name`, `interval_s`, `active`), so an unexpected key in a request body cannot reach the SQL string.

## 3. `schemas.py` — validation at the boundary

`interval_s` is bounded 30–86,400 and `url` is typed as `HttpUrl`, so no route contains a range check. `name` is stripped by a field validator, which is why `"  Padded  "` is stored as `"Padded"`.

## 4. `main.py` — a factory, not a module-level app

`create_app()` builds a fresh application each call, and the database path comes from `UPTIMEKIT_DB`. Tests therefore get an isolated database per test with no teardown dance.

## Design decisions

**Why SQLite.** The read pattern is a single indexed range scan on `(monitor_id, checked_at DESC)`; the write volume is one row per probe. Postgres would add an operational dependency for no measurable benefit. `PRAGMA foreign_keys = ON` plus `ON DELETE CASCADE` keeps check history from outliving its monitor.

**Why probing is explicit.** A background scheduler you cannot trigger on demand is hard to test and hard to trust. `POST /check` makes the unit of work obvious and inspectable. A cron job or worker can call the same endpoint later without a second code path.

**Why uptime is derived, not stored.** `uptime_pct` and `avg_latency_ms` are computed from the checks table on read. Storing them would mean a second write per probe and a second thing to keep consistent; the aggregate query is cheap against a single index.

## Testing strategy

- `test_probe.py` — health bands, timeouts, transport errors, redirect following, immutability
- `test_repository.py` — CRUD, partial updates, uptime maths, cascade delete
- `test_api.py` — status codes, validation rejections, error mapping, badge format
- `api.test.ts` / `App.test.tsx` — formatters, empty state, create flow, metrics rendering

Backend runs on Python 3.10–3.12; frontend typechecks and builds before its tests run.
