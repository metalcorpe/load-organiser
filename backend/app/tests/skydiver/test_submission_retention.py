"""Submissions kept after account deletion are purged after the retention period (#162)."""

import uuid
from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError

from app.core.db import engine
from app.skydiver.moderation import retention
from app.tests.skydiver.support import Accounts


@pytest.fixture(scope="module")
def api_person() -> uuid.UUID:
    accounts = Accounts.create()
    secret = accounts.session()
    return accounts.service.current_viewer(secret=secret).person_id


def _insert(conn, *, removed: datetime | None, person: uuid.UUID | None = None) -> uuid.UUID:  # type: ignore[no-untyped-def]  # fmt: skip
    row = uuid.uuid4()
    conn.execute(
        text(
            "INSERT INTO skydiver_submission (id, submitter_person_id, client_key, "
            "fingerprint, kind, message, status, version, created_at, author_removed_at) "
            "VALUES (:id, :person, :key, 'f', 'feedback', 'kept', 'open', 1, now(), :removed)"
        ),
        {"id": row, "person": person, "key": uuid.uuid4(), "removed": removed},
    )
    return row


def _left(*ids: uuid.UUID) -> set[uuid.UUID]:
    with engine.connect() as conn:
        return set(
            conn.execute(
                text("SELECT id FROM skydiver_submission WHERE id = ANY(:ids)"),
                {"ids": list(ids)},
            ).scalars()
        )


def test_purge_deletes_only_submissions_unlinked_longer_than_the_period() -> None:
    now = datetime.now(UTC)
    with engine.begin() as conn:
        old = _insert(conn, removed=now - timedelta(days=31))
        recent = _insert(conn, removed=now - timedelta(days=29))
    try:
        assert retention.purge(engine, 30, now=now) >= 1
        assert _left(old, recent) == {recent}
        with pytest.raises(retention.RetentionError):
            retention.purge(engine, 0)
    finally:
        with engine.begin() as conn:
            conn.execute(text("DELETE FROM skydiver_submission WHERE id = ANY(:ids)"), {"ids": [old, recent]})  # fmt: skip


def test_exactly_one_of_author_and_removal_time_is_set(api_person: uuid.UUID) -> None:
    with pytest.raises(IntegrityError), engine.begin() as conn:
        _insert(conn, removed=None)  # neither
    with pytest.raises(IntegrityError), engine.begin() as conn:
        _insert(conn, removed=datetime.now(UTC), person=api_person)  # both
