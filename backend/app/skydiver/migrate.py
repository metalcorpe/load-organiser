"""Apply database migrations when the app starts (#161).

FastAPI Cloud has no release step, so a hosted deploy migrates on start-up when
SKYDIVER_MIGRATE_ON_START is true:

- over the direct connection: Neon's pooled host (`...-pooler...`) runs through
  PgBouncer in transaction mode, which is not safe for schema changes; the direct
  host is the same name without `-pooler`;
- in one transaction, without locks (the beta takes none; compare-and-swap instead):
  Alembic moves `alembic_version` only from the version it read, and PostgreSQL's
  DDL is transactional, so of several instances starting at once one commits and the
  others roll back whole; they then find the database at the latest version and go on;
- and a failure stops the start-up: the new instances do not serve, while the ones
  already running keep the previous version.

Every migration must still work with the code that is running during a rollover
(docs/product/deploy-runbook.md).
"""

import logging
from pathlib import Path

from alembic import command
from alembic.config import Config
from alembic.script import ScriptDirectory
from sqlalchemy import create_engine, pool, text
from sqlalchemy.engine import Engine, make_url

logger = logging.getLogger(__name__)

ALEMBIC_DIR = Path(__file__).resolve().parents[1] / "alembic"


def direct_url(url: str) -> str:
    """The same database through Neon's direct host instead of its pooler."""
    parsed = make_url(url)
    host = parsed.host or ""
    first, dot, rest = host.partition(".")
    if first.endswith("-pooler"):
        parsed = parsed.set(host=f"{first.removesuffix('-pooler')}{dot}{rest}")
    return parsed.render_as_string(hide_password=False)


def _config() -> Config:
    config = Config()
    config.set_main_option("script_location", str(ALEMBIC_DIR))
    return config


def _current(engine: Engine) -> str | None:
    with engine.connect() as connection:
        found = connection.execute(
            text("SELECT to_regclass('alembic_version') IS NOT NULL")
        ).scalar_one()
        if not found:
            return None
        return connection.execute(
            text("SELECT version_num FROM alembic_version")
        ).scalar_one_or_none()


def migrate(url: str) -> None:
    """Upgrade to the latest migration; another instance doing it first is fine."""
    config = _config()
    head = ScriptDirectory.from_config(config).get_current_head()
    engine = create_engine(direct_url(url), poolclass=pool.NullPool)
    try:
        if _current(engine) == head:
            return
        try:
            with engine.begin() as connection:
                config.attributes["connection"] = connection
                command.upgrade(config, "head")
        except Exception:
            # Lost the race: the winner's commit made this one roll back whole.
            if _current(engine) != head:
                raise
            logger.info("Another instance applied the migrations")
            return
    finally:
        engine.dispose()
    logger.info("Database migrations applied up to %s", head)
