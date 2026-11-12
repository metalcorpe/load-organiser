"""#161 migrations at app start-up: direct connection, advisory lock, idempotent."""

import multiprocessing
import uuid
from concurrent.futures import ProcessPoolExecutor

from alembic.config import Config
from alembic.script import ScriptDirectory
from sqlalchemy import create_engine, text
from sqlalchemy.engine import make_url
from sqlalchemy.pool import NullPool

from app.core.config import settings
from app.core.db import engine
from app.skydiver.migrate import ALEMBIC_DIR, direct_url, migrate

POOLED = (
    "postgresql+psycopg://owner:pw@ep-winter-math-123456-pooler.c-7.eu-central-1"
    ".aws.neon.tech/neondb?sslmode=require&channel_binding=require"
)


def test_neon_pooled_host_becomes_the_direct_host() -> None:
    url = direct_url(POOLED)
    assert "@ep-winter-math-123456.c-7.eu-central-1.aws.neon.tech/neondb" in url
    assert "-pooler" not in url
    assert "sslmode=require" in url and "channel_binding=require" in url
    assert ":pw@" in url  # the password is kept, not masked
    local = "postgresql+psycopg://verify:pw@127.0.0.1:55432/verify_backend"
    assert direct_url(local) == local


def _head() -> str:
    config = Config()
    config.set_main_option("script_location", str(ALEMBIC_DIR))
    head = ScriptDirectory.from_config(config).get_current_head()
    assert head is not None
    return head


def _current() -> str:
    with engine.connect() as connection:
        return str(
            connection.execute(
                text("SELECT version_num FROM alembic_version")
            ).scalar_one()
        )


def test_instances_starting_together_all_start_and_the_schema_is_current() -> None:
    """Three processes race the whole chain on a fresh, empty database (a first deploy).

    A database of its own: the shared test database holds data that some downgrades
    rightly refuse to drop (imported jumps), so it is never stepped back.
    """
    name = f"verify_migrate_{uuid.uuid4().hex[:10]}"
    url = make_url(str(settings.SQLALCHEMY_DATABASE_URI))
    admin = create_engine(url.set(database="postgres"), isolation_level="AUTOCOMMIT")
    with admin.connect() as connection:
        connection.execute(text(f'CREATE DATABASE "{name}"'))
    fresh = url.set(database=name).render_as_string(hide_password=False)
    try:
        # Separate processes, like instances on the host (Alembic's context is per process).
        spawn = multiprocessing.get_context("spawn")
        with ProcessPoolExecutor(max_workers=3, mp_context=spawn) as pool:
            list(pool.map(migrate, [fresh] * 3))  # none of them raises
        own = create_engine(fresh, poolclass=NullPool)
        try:
            with own.connect() as connection:
                current = connection.execute(
                    text("SELECT version_num FROM alembic_version")
                ).scalar_one()
        finally:
            own.dispose()
        assert current == _head()
        migrate(fresh)  # already current: nothing to do
    finally:
        with admin.connect() as connection:
            connection.execute(text(f'DROP DATABASE IF EXISTS "{name}" WITH (FORCE)'))
        admin.dispose()


def test_the_reviewer_bootstrap_needs_the_address_confirmed() -> None:
    from app.skydiver.access.grant import bootstrap_reviewer
    from app.tests.skydiver.support import Accounts

    accounts = Accounts.create()
    missing = f"nobody-{uuid.uuid4().hex[:10]}@example.com"
    assert bootstrap_reviewer(engine, email=missing) == "no_unique_account"

    # Someone registers the owner's address first but cannot confirm it: no role.
    squatter = accounts.session(verified=False)
    unconfirmed = accounts.service.current_viewer(secret=squatter)
    assert bootstrap_reviewer(engine, email=unconfirmed.email) == "not_confirmed"
    assert "reviewer" not in accounts.service.current_viewer(secret=squatter).roles

    # The confirmed owner gets it, case-insensitively, and again is a no-op.
    owner = accounts.session(verified=True)
    confirmed = accounts.service.current_viewer(secret=owner)
    assert bootstrap_reviewer(engine, email=confirmed.email.upper()) == "granted"
    assert bootstrap_reviewer(engine, email=confirmed.email) == "granted"
    assert "reviewer" in accounts.service.current_viewer(secret=owner).roles
