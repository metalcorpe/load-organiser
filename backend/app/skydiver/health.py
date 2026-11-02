"""Unauthenticated beta health contract (#144).

Proves the web -> API -> PostgreSQL path without exposing configuration,
versions, hostnames or error details.
"""

from collections.abc import Callable
from datetime import UTC, datetime
from typing import Literal

from pydantic import BaseModel, Field

DatabaseProbe = Callable[[], bool]
"""Port: returns True when the database answered a trivial query."""

Clock = Callable[[], datetime]


def utc_now() -> datetime:
    return datetime.now(UTC)


class HealthStatus(BaseModel):
    status: Literal["ok", "unavailable"] = Field(
        description="Overall API availability for beta requests."
    )
    database: Literal["ok", "unavailable"] = Field(
        description="Whether the API could reach its database."
    )
    checked_at: datetime = Field(description="UTC instant the check ran.")


def check_health(
    *, database_probe: DatabaseProbe, clock: Clock = utc_now
) -> HealthStatus:
    database_ok = database_probe()
    state: Literal["ok", "unavailable"] = "ok" if database_ok else "unavailable"
    return HealthStatus(status=state, database=state, checked_at=clock())
