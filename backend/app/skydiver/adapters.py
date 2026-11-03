"""Concrete adapters for skydiver ports. Imported only by the composition root."""

import logging
import secrets
import threading
import time
from collections.abc import Callable

from sqlalchemy import Engine, create_engine, text
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.pool import NullPool

from app.skydiver.health import DatabaseProbe

logger = logging.getLogger(__name__)

PROBE_TIMEOUT_SECONDS = 2
PROBE_CACHE_SECONDS = 5.0


def create_probe_engine(url: str) -> Engine:
    """Engine dedicated to the unauthenticated health probe.

    NullPool keeps probe traffic out of the application pool, and the libpq
    connect/statement timeouts bound how long a blackholed host can hold a worker.
    """
    return create_engine(
        url,
        poolclass=NullPool,
        connect_args={
            "connect_timeout": PROBE_TIMEOUT_SECONDS,
            "options": f"-c statement_timeout={PROBE_TIMEOUT_SECONDS * 1000}",
        },
    )


def sql_database_probe(engine: Engine) -> DatabaseProbe:
    def probe() -> bool:
        try:
            with engine.connect() as connection:
                connection.execute(text("SELECT 1"))
        except SQLAlchemyError as exc:
            # Log the exception class only: driver messages can contain hosts/users.
            logger.warning("Database probe failed: %s", type(exc).__name__)
            return False
        return True

    return probe


def cached_probe(
    probe: DatabaseProbe,
    *,
    ttl_seconds: float = PROBE_CACHE_SECONDS,
    monotonic: Callable[[], float] = time.monotonic,
) -> DatabaseProbe:
    """Share one probe result for `ttl_seconds`.

    Anonymous callers cannot make the backend open more than one database
    connection per interval; concurrent callers wait for the in-flight probe.
    """
    lock = threading.Lock()
    last: tuple[float, bool] | None = None

    def cached() -> bool:
        nonlocal last
        with lock:
            now = monotonic()
            if last is None or now - last[0] >= ttl_seconds:
                last = (now, probe())
            return last[1]

    return cached


class AppPasswordHasher:
    """#170 hashing (Argon2id, legacy bcrypt verification and upgrade) as a port."""

    def __init__(self) -> None:
        from app.core import security

        self._security = security
        # A real Argon2 hash to verify against when no account exists.
        self._decoy = security.get_password_hash(secrets.token_urlsafe(24))

    def hash(self, password: str) -> str:
        return self._security.get_password_hash(password)

    def verify_and_update(
        self, password: str, stored_hash: str
    ) -> tuple[bool, str | None]:
        try:
            return self._security.verify_and_update_password(password, stored_hash)
        except Exception as exc:  # unknown/corrupt hash format: fail closed
            logger.warning("Password hash not verifiable: %s", type(exc).__name__)
            return False, None

    def burn(self, password: str) -> None:
        self._security.verify_password(password, self._decoy)
