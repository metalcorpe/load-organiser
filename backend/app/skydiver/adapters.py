"""Concrete adapters for skydiver ports. Imported only by the composition root."""

import logging

from sqlalchemy import Engine, text
from sqlalchemy.exc import SQLAlchemyError

from app.skydiver.health import DatabaseProbe

logger = logging.getLogger(__name__)


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
