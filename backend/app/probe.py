"""HTTP probing: turn a URL into an immutable Probe."""

from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Optional

import httpx

DEFAULT_TIMEOUT_S = 10.0


@dataclass(frozen=True)
class Probe:
    """Result of a single HTTP probe."""

    ok: bool
    status_code: Optional[int]
    latency_ms: Optional[float]
    error: Optional[str]


def probe(url: str, timeout: float = DEFAULT_TIMEOUT_S) -> Probe:
    """GET a URL and report whether it answered, how fast, and any failure.

    Treats 2xx and 3xx as healthy: a redirect still proves the host is serving.
    Never raises - transport failures come back as a failed Probe so the
    caller records them instead of crashing.
    """
    started = time.perf_counter()
    try:
        response = httpx.get(url, timeout=timeout, follow_redirects=True)
    except httpx.TimeoutException:
        return Probe(False, None, None, f"timeout after {timeout:g}s")
    except httpx.HTTPError as exc:
        return Probe(False, None, None, f"{type(exc).__name__}: {exc}")
    finally:
        elapsed_ms = (time.perf_counter() - started) * 1000

    healthy = 200 <= response.status_code < 400
    error = None if healthy else f"HTTP {response.status_code}"
    return Probe(healthy, response.status_code, round(elapsed_ms, 2), error)
