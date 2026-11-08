"""Submissions kept after account deletion are purged after the retention period (#162)."""

import uuid
from datetime import UTC, datetime, timedelta

import pytest
from sqlalchemy import text
from sqlalchemy.exc import IntegrityError

from app.core.db import engine
from app.skydiver.moderation import retention


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
    assert retention.purge(engine, 30, now=now) >= 1
    assert _left(old, recent) == {recent}
    with pytest.raises(retention.RetentionError):
        retention.purge(engine, 0)


def test_an_author_and_a_removal_time_cannot_coexist() -> None:
    with pytest.raises(IntegrityError), engine.begin() as conn:
        _insert(conn, removed=None)  # no author and no removal time
