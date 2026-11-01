"""Pydantic request/response models - the API's public contract."""

from __future__ import annotations

from datetime import datetime
from typing import Optional

from pydantic import BaseModel, Field, HttpUrl, field_validator


class MonitorCreate(BaseModel):
    """Payload for registering a new monitor."""

    name: str = Field(..., min_length=1, max_length=80)
    url: HttpUrl
    interval_s: int = Field(300, ge=30, le=86400)

    @field_validator("name")
    @classmethod
    def _strip_name(cls, value: str) -> str:
        cleaned = value.strip()
        if not cleaned:
            raise ValueError("name must not be blank")
        return cleaned


class MonitorUpdate(BaseModel):
    """Partial update; omitted fields are left untouched."""

    name: Optional[str] = Field(None, min_length=1, max_length=80)
    interval_s: Optional[int] = Field(None, ge=30, le=86400)
    active: Optional[bool] = None


class CheckRead(BaseModel):
    """A single probe result."""

    id: int
    monitor_id: int
    ok: bool
    status_code: Optional[int] = None
    latency_ms: Optional[float] = None
    error: Optional[str] = None
    checked_at: datetime


class MonitorRead(BaseModel):
    """A monitor plus its rolled-up health."""

    id: int
    name: str
    url: str
    interval_s: int
    active: bool
    created_at: datetime
    last_check: Optional[CheckRead] = None
    uptime_pct: Optional[float] = None
    avg_latency_ms: Optional[float] = None


class StatusResponse(BaseModel):
    """Aggregate service health."""

    monitors: int
    up: int
    down: int
    unknown: int
