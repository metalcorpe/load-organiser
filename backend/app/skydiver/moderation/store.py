"""SQL adapter for submissions (#151)."""

import uuid
from collections.abc import Iterator
from contextlib import contextmanager
from datetime import datetime
from typing import Any

from sqlalchemy import Engine, func, select, tuple_, update
from sqlmodel import Session, col

from app.skydiver.access.policy import Actor
from app.skydiver.directory.service import EditConflict
from app.skydiver.moderation.service import (
    Kind,
    Status,
    StoreFactory,
    Submission,
    SubmissionStore,
    TargetKind,
)
from app.skydiver.moderation.tables import SkydiverSubmission

S = SkydiverSubmission


def _submission(row: SkydiverSubmission) -> Submission:
    return Submission(
        id=row.id,
        kind=Kind(row.kind),
        target_kind=TargetKind(row.target_kind) if row.target_kind else None,
        target_id=row.target_id,
        message=row.message,
        source_url=row.source_url,
        status=Status(row.status),
        resolution_note=row.resolution_note,
        resolved_at=row.resolved_at,
        created_at=row.created_at,
        version=row.version,
        fingerprint=row.fingerprint,
    )


class SqlSubmissionStore:
    def __init__(self, session: Session) -> None:
        self._s = session

    def _own(self, actor: Actor) -> Any:
        return select(S).where(col(S.submitter_person_id) == actor.person_id)

    def by_key(self, actor: Actor, client_key: uuid.UUID) -> Submission | None:
        row = (
            self._s.execute(self._own(actor).where(col(S.client_key) == client_key))
            .scalars()
            .first()
        )
        return _submission(row) if row else None

    def _count(self, query: Any) -> int:
        return int(
            self._s.execute(
                select(func.count()).select_from(query.subquery())
            ).scalar_one()
        )

    def count_since(self, actor: Actor, since: datetime) -> int:
        return self._count(self._own(actor).where(col(S.created_at) >= since))

    def count_open(self, actor: Actor) -> int:
        return self._count(self._own(actor).where(col(S.status) == Status.OPEN.value))

    def insert(
        self, actor: Actor, client_key: uuid.UUID, values: dict[str, Any], now: datetime
    ) -> uuid.UUID:
        row = SkydiverSubmission(
            submitter_person_id=actor.person_id,
            client_key=client_key,
            status=Status.OPEN.value,
            created_at=now,
            **values,
        )
        self._s.add(row)
        self._s.flush()
        return row.id

    def get(self, submission_id: uuid.UUID) -> Submission | None:
        row = self._s.get(S, submission_id)
        return _submission(row) if row else None

    def mine(self, actor: Actor, limit: int) -> list[Submission]:
        rows = self._s.execute(
            self._own(actor)
            .order_by(col(S.created_at).desc(), col(S.id).desc())
            .limit(limit)
        ).scalars()
        return [_submission(row) for row in rows]

    def queue(
        self,
        status: Status | None,
        after: tuple[str, uuid.UUID] | None,
        limit: int,
    ) -> list[Submission]:
        query = select(S)
        if status is not None:
            query = query.where(col(S.status) == status.value)
        if after:
            query = query.where(
                tuple_(col(S.created_at), col(S.id))
                > (datetime.fromisoformat(after[0]), after[1])
            )
        query = query.order_by(col(S.created_at), col(S.id)).limit(limit)
        return [_submission(row) for row in self._s.execute(query).scalars()]

    def resolve(
        self,
        submission_id: uuid.UUID,
        *,
        status: Status,
        note: str | None,
        actor: Actor,
        now: datetime,
        expected_version: int,
    ) -> None:
        result = self._s.execute(
            update(S)
            .where(col(S.id) == submission_id)
            .where(col(S.version) == expected_version)
            .values(
                status=status.value,
                resolution_note=note,
                resolved_at=now,
                resolved_by_account_id=actor.account_id,
                version=expected_version + 1,
            )
        )
        if result.rowcount != 1:  # type: ignore[attr-defined]
            raise EditConflict()


def sql_submission_store_factory(engine: Engine) -> StoreFactory:
    """Unit of work: commit on success, roll back on any exception."""

    @contextmanager
    def stores() -> Iterator[SubmissionStore]:
        with Session(engine) as session:
            try:
                yield SqlSubmissionStore(session)
            except BaseException:
                session.rollback()
                raise
            session.commit()

    return stores
