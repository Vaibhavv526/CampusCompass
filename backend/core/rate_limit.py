from __future__ import annotations

import math
import threading
import time
from typing import Callable

from fastapi import Depends, HTTPException, Request, Response, status

from backend.auth.dependencies import get_current_user
from backend.models.user import User


class RateLimiter:
    """Thread-safe, process-local sliding window rate limiter.

    Deployment Notice:
        This rate limiter maintains state in process-local memory.
        In multi-worker (e.g. Uvicorn with --workers > 1) or multi-container
        deployments, each worker process tracks its own quotas independently.
        For distributed architectures requiring shared, global quotas across
        replicas, a shared state store (such as Redis or Valkey) should be
        introduced as a drop-in replacement backend for this class.
    """

    def __init__(self) -> None:
        self._lock = threading.Lock()
        self._records: dict[str, list[float]] = {}
        self._cleanup_counter: int = 0

    def check(
        self,
        key: str,
        max_requests: int,
        window_seconds: int,
        now: float | None = None,
    ) -> tuple[bool, int, int, int]:
        """Check whether a request is allowed under the sliding window.

        Args:
            key: Unique identifier for the quota (e.g. user ID or client IP).
            max_requests: Maximum allowed requests within the time window.
            window_seconds: Duration of the sliding window in seconds.
            now: Optional timestamp override for deterministic testing.

        Returns:
            tuple of (allowed, remaining, reset_time, retry_after)
        """
        with self._lock:
            current_time = time.time() if now is None else now
            window_start = current_time - window_seconds

            timestamps = [
                t for t in self._records.get(key, []) if t > window_start
            ]

            if len(timestamps) >= max_requests:
                oldest = timestamps[0]
                retry_after = max(1, int(math.ceil(oldest + window_seconds - current_time)))
                reset_time = int(math.ceil(oldest + window_seconds))
                self._records[key] = timestamps
                return False, 0, reset_time, retry_after

            timestamps.append(current_time)
            self._records[key] = timestamps
            remaining = max(0, max_requests - len(timestamps))
            reset_time = int(math.ceil(timestamps[0] + window_seconds))

            self._cleanup_counter += 1
            if self._cleanup_counter >= 100:
                self._maybe_prune_locked(current_time)

            return True, remaining, reset_time, 0

    def _maybe_prune_locked(self, current_time: float, max_idle_seconds: int = 3600) -> None:
        self._cleanup_counter = 0
        cutoff = current_time - max_idle_seconds
        stale_keys = [
            k for k, v in self._records.items()
            if not v or v[-1] < cutoff
        ]
        for k in stale_keys:
            del self._records[k]

    def cleanup(self, max_idle_seconds: int = 3600, now: float | None = None) -> int:
        """Prune idle or expired keys from storage. Returns count of pruned keys."""
        with self._lock:
            current_time = time.time() if now is None else now
            cutoff = current_time - max_idle_seconds
            stale_keys = [
                k for k, v in self._records.items()
                if not v or v[-1] < cutoff
            ]
            for k in stale_keys:
                del self._records[k]
            return len(stale_keys)

    def reset(self) -> None:
        """Reset all rate limiter state. Intended for deterministic test teardown."""
        with self._lock:
            self._records.clear()
            self._cleanup_counter = 0


rate_limiter = RateLimiter()


def rate_limit_user(
    max_requests: int,
    window_seconds: int = 60,
    group: str = "default",
) -> Callable:
    """FastAPI dependency to rate limit by authenticated user ID."""

    def dependency(
        response: Response,
        current_user: User = Depends(get_current_user),
    ) -> None:
        key = f"user:{current_user.id}:{group}"
        allowed, remaining, reset_time, retry_after = rate_limiter.check(
            key=key,
            max_requests=max_requests,
            window_seconds=window_seconds,
        )

        response.headers["X-RateLimit-Limit"] = str(max_requests)
        response.headers["X-RateLimit-Remaining"] = str(remaining)
        response.headers["X-RateLimit-Reset"] = str(reset_time)

        if not allowed:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Too many requests. Please try again later.",
                headers={
                    "Retry-After": str(retry_after),
                    "X-RateLimit-Limit": str(max_requests),
                    "X-RateLimit-Remaining": str(remaining),
                    "X-RateLimit-Reset": str(reset_time),
                },
            )

    return dependency


def rate_limit_ip(
    max_requests: int,
    window_seconds: int = 60,
    group: str = "default",
) -> Callable:
    """FastAPI dependency to rate limit by client IP without trusting spoofable headers."""

    def dependency(
        request: Request,
        response: Response,
    ) -> None:
        client_ip = request.client.host if request.client else "unknown"
        key = f"ip:{client_ip}:{group}"
        allowed, remaining, reset_time, retry_after = rate_limiter.check(
            key=key,
            max_requests=max_requests,
            window_seconds=window_seconds,
        )

        response.headers["X-RateLimit-Limit"] = str(max_requests)
        response.headers["X-RateLimit-Remaining"] = str(remaining)
        response.headers["X-RateLimit-Reset"] = str(reset_time)

        if not allowed:
            raise HTTPException(
                status_code=status.HTTP_429_TOO_MANY_REQUESTS,
                detail="Too many requests. Please try again later.",
                headers={
                    "Retry-After": str(retry_after),
                    "X-RateLimit-Limit": str(max_requests),
                    "X-RateLimit-Remaining": str(remaining),
                    "X-RateLimit-Reset": str(reset_time),
                },
            )

    return dependency