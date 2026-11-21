"""Daily and per-network caps for the two routes that call Azure OpenAI.

Counters live in Postgres, so a container restart does not open a new budget.
A failed check refuses the request. The model is not called.
"""

from __future__ import annotations

from datetime import datetime, timedelta, timezone

from fastapi import Request

from app.config import get_settings
from app.db import pool

GLOBAL_SCOPE = "global"
_ROUTES = frozenset({"investigate", "ask"})


class UsageLimitError(Exception):
    """The request is over the daily cap or the per-network hourly cap."""

    def __init__(self, scope: str, route: str, limit: int) -> None:
        self.scope = scope
        self.route = route
        self.limit = limit
        super().__init__(limit_message(scope, route, limit))


class UsageTrackerError(Exception):
    """The cap could not be read or written. Callers must not continue to Azure."""


def limit_message(scope: str, route: str, limit: int) -> str:
    if scope == "day" and route == "investigate":
        return (
            f"This demo has reached its daily limit of {limit} investigations. "
            "It resets at 00:00 UTC."
        )
    if scope == "day" and route == "ask":
        return (
            f"This demo has reached its daily limit of {limit} questions. "
            "It resets at 00:00 UTC."
        )
    if scope == "hour" and route == "investigate":
        return "Too many investigations from this network in the last hour. Try again later."
    if scope == "hour" and route == "ask":
        return "Too many questions from this network in the last hour. Try again later."
    return "This demo has reached its usage limit."


def usage_windows(moment: datetime) -> tuple[datetime, datetime]:
    """UTC midnight and UTC hour that contain moment."""
    utc = moment.astimezone(timezone.utc)
    day = utc.replace(hour=0, minute=0, second=0, microsecond=0)
    hour = utc.replace(minute=0, second=0, microsecond=0)
    return day, hour


def resolve_client_ip(forwarded_for: str | None, socket_host: str | None, trust_proxy: bool) -> str:
    """Use the last forwarded hop when a proxy in front of the API appended it."""
    if trust_proxy and forwarded_for:
        parts = [part.strip() for part in forwarded_for.split(",") if part.strip()]
        if parts:
            return parts[-1][:128]
    if socket_host:
        return socket_host[:128]
    return "unknown"


def client_ip(request: Request) -> str:
    settings = get_settings()
    socket_host = request.client.host if request.client is not None else None
    return resolve_client_ip(request.headers.get("x-forwarded-for"), socket_host, settings.trust_proxy)


def _limits(route: str) -> tuple[int, int]:
    if route not in _ROUTES:
        raise ValueError(f"unknown usage route: {route}")
    settings = get_settings()
    if route == "investigate":
        return settings.investigate_daily_limit, settings.investigate_hourly_limit
    return settings.ask_daily_limit, settings.ask_hourly_limit


def _increment(conn, scope: str, route: str, window_kind: str, window_start: datetime, limit: int) -> bool:
    """Reserve one hit when the window is still under the cap. False means the cap is already met."""
    row = conn.execute(
        """
        INSERT INTO api_usage (scope, route, window_kind, window_start, hits)
        VALUES (%s, %s, %s, %s, 1)
        ON CONFLICT (scope, route, window_kind, window_start)
        DO UPDATE SET hits = api_usage.hits + 1
        WHERE api_usage.hits < %s
        RETURNING hits
        """,
        (scope, route, window_kind, window_start, limit),
    ).fetchone()
    return row is not None


def consume_usage(route: str, ip: str, now: datetime | None = None) -> None:
    """Count this request, or raise before the caller reaches Azure OpenAI."""
    if not get_settings().usage_limits_enabled:
        return
    moment = now or datetime.now(timezone.utc)
    day_start, hour_start = usage_windows(moment)
    daily_limit, hourly_limit = _limits(route)
    cutoff = moment.astimezone(timezone.utc) - timedelta(days=2)
    try:
        with pool().connection() as conn:
            with conn.transaction():
                conn.execute("DELETE FROM api_usage WHERE window_start < %s", (cutoff,))
                if not _increment(conn, GLOBAL_SCOPE, route, "day", day_start, daily_limit):
                    raise UsageLimitError("day", route, daily_limit)
                if not _increment(conn, ip, route, "hour", hour_start, hourly_limit):
                    raise UsageLimitError("hour", route, hourly_limit)
    except UsageLimitError:
        raise
    except Exception as exc:
        raise UsageTrackerError("The usage limit could not be checked.") from exc


def enforce_usage(request: Request, route: str) -> None:
    consume_usage(route, client_ip(request))
