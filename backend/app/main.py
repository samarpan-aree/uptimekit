"""UptimeKit API - application factory and routes."""

from __future__ import annotations

from contextlib import asynccontextmanager
from typing import Iterator

from fastapi import Depends, FastAPI, HTTPException, Query, Response, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import PlainTextResponse

from . import repository as repo
from .db import init_db, session
from .probe import probe
from .schemas import (
    CheckRead,
    MonitorCreate,
    MonitorRead,
    MonitorUpdate,
    StatusResponse,
)

API_VERSION = "1.0.0"


@asynccontextmanager
async def lifespan(app: FastAPI):
    init_db()
    yield


def get_conn() -> Iterator:
    """Yield a transactional connection for the duration of a request."""
    with session() as conn:
        yield conn


def _row_to_monitor(conn, row) -> MonitorRead:
    latest = repo.last_check(conn, row["id"])
    uptime, latency = repo.health_summary(conn, row["id"])
    last = None
    if latest is not None:
        last = CheckRead(
            id=latest["id"],
            monitor_id=latest["monitor_id"],
            ok=bool(latest["ok"]),
            status_code=latest["status_code"],
            latency_ms=latest["latency_ms"],
            error=latest["error"],
            checked_at=latest["checked_at"],
        )
    return MonitorRead(
        id=row["id"],
        name=row["name"],
        url=row["url"],
        interval_s=row["interval_s"],
        active=bool(row["active"]),
        created_at=row["created_at"],
        last_check=last,
        uptime_pct=uptime,
        avg_latency_ms=latency,
    )


def create_app() -> FastAPI:
    app = FastAPI(
        title="UptimeKit",
        version=API_VERSION,
        description="Self-hosted API uptime and latency monitoring.",
        lifespan=lifespan,
    )

    app.add_middleware(
        CORSMiddleware,
        allow_origins=["*"],
        allow_methods=["*"],
        allow_headers=["*"],
    )

    @app.get("/api/health", tags=["meta"])
    def health() -> dict[str, str]:
        """Liveness probe for UptimeKit itself."""
        return {"status": "ok", "version": API_VERSION}

    @app.get("/api/status", response_model=StatusResponse, tags=["monitors"])
    def status_(conn=Depends(get_conn)) -> StatusResponse:
        """Aggregate health across all active monitors."""
        return StatusResponse(**repo.status_counts(conn))

    @app.get("/api/monitors", response_model=list[MonitorRead], tags=["monitors"])
    def list_monitors(
        include_inactive: bool = Query(True),
        conn=Depends(get_conn),
    ) -> list[MonitorRead]:
        rows = repo.list_monitors(conn, include_inactive=include_inactive)
        return [_row_to_monitor(conn, row) for row in rows]

    @app.post(
        "/api/monitors",
        response_model=MonitorRead,
        status_code=status.HTTP_201_CREATED,
        tags=["monitors"],
    )
    def create_monitor(payload: MonitorCreate, conn=Depends(get_conn)) -> MonitorRead:
        monitor_id = repo.create_monitor(
            conn, payload.name, str(payload.url), payload.interval_s
        )
        row = repo.get_monitor(conn, monitor_id)
        assert row is not None
        return _row_to_monitor(conn, row)

    @app.get("/api/monitors/{monitor_id}", response_model=MonitorRead, tags=["monitors"])
    def get_monitor(monitor_id: int, conn=Depends(get_conn)) -> MonitorRead:
        row = repo.get_monitor(conn, monitor_id)
        if row is None:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "monitor not found")
        return _row_to_monitor(conn, row)

    @app.patch("/api/monitors/{monitor_id}", response_model=MonitorRead, tags=["monitors"])
    def update_monitor(
        monitor_id: int, payload: MonitorUpdate, conn=Depends(get_conn)
    ) -> MonitorRead:
        row = repo.get_monitor(conn, monitor_id)
        if row is None:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "monitor not found")
        repo.update_monitor(conn, monitor_id, payload.model_dump(exclude_none=True))
        updated = repo.get_monitor(conn, monitor_id)
        assert updated is not None
        return _row_to_monitor(conn, updated)

    @app.delete(
        "/api/monitors/{monitor_id}",
        status_code=status.HTTP_204_NO_CONTENT,
        tags=["monitors"],
    )
    def delete_monitor(monitor_id: int, conn=Depends(get_conn)) -> Response:
        if not repo.delete_monitor(conn, monitor_id):
            raise HTTPException(status.HTTP_404_NOT_FOUND, "monitor not found")
        return Response(status_code=status.HTTP_204_NO_CONTENT)

    @app.post(
        "/api/monitors/{monitor_id}/check",
        response_model=CheckRead,
        status_code=status.HTTP_201_CREATED,
        tags=["checks"],
    )
    def run_check(monitor_id: int, conn=Depends(get_conn)) -> CheckRead:
        """Probe the monitor's URL now and record the result."""
        row = repo.get_monitor(conn, monitor_id)
        if row is None:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "monitor not found")
        result = probe(row["url"])
        check_id = repo.record_check(conn, monitor_id, result)
        conn.commit()
        return CheckRead(
            id=check_id,
            monitor_id=monitor_id,
            ok=result.ok,
            status_code=result.status_code,
            latency_ms=result.latency_ms,
            error=result.error,
            checked_at=repo.recent_checks(conn, monitor_id, limit=1)[0]["checked_at"],
        )

    @app.get(
        "/api/monitors/{monitor_id}/checks",
        response_model=list[CheckRead],
        tags=["checks"],
    )
    def list_checks(
        monitor_id: int,
        limit: int = Query(50, ge=1, le=500),
        conn=Depends(get_conn),
    ) -> list[CheckRead]:
        if repo.get_monitor(conn, monitor_id) is None:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "monitor not found")
        return [
            CheckRead(
                id=r["id"],
                monitor_id=r["monitor_id"],
                ok=bool(r["ok"]),
                status_code=r["status_code"],
                latency_ms=r["latency_ms"],
                error=r["error"],
                checked_at=r["checked_at"],
            )
            for r in repo.recent_checks(conn, monitor_id, limit=limit)
        ]

    @app.get(
        "/api/monitors/{monitor_id}/badge",
        response_class=PlainTextResponse,
        tags=["checks"],
    )
    def badge(monitor_id: int, conn=Depends(get_conn)) -> str:
        """Shields.io endpoint: returns uptime and a colour."""
        row = repo.get_monitor(conn, monitor_id)
        if row is None:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "monitor not found")
        uptime, _ = repo.health_summary(conn, monitor_id)
        if uptime is None:
            return "unknown"
        colour = "brightgreen" if uptime >= 99.5 else "green" if uptime >= 98 else "orange"
        return f"{uptime}%25%20uptime-{colour}"

    return app


app = create_app()
