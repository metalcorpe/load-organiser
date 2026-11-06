"""SQL adapter for jump posts (#157).

Concurrency is compare-and-swap, no explicit locks:
- Publishing re-checks the jump with `UPDATE ... SET version = version WHERE
  version = :seen`. Under read committed a concurrent edit either commits first
  (the condition fails: edit_conflict) or waits for the publish to commit and then
  sees the new post when it withdraws affected posts.
- The profile gets the same conditional touch, so hiding, restricting or making
  the profile non-discoverable cannot interleave with a publish.
"""

import uuid
from collections.abc import Iterator
from contextlib import contextmanager
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import Engine, and_, delete, exists, or_, select, update
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlmodel import Session, col

from app.skydiver.logbook.tables import SkydiverJump, SkydiverJumpEvent
from app.skydiver.posts import policy
from app.skydiver.posts.policy import Audience, Share
from app.skydiver.posts.service import Post, PostStore, Source, StoreFactory
from app.skydiver.posts.tables import SkydiverJumpPost
from app.skydiver.social.service import Person, ProfileRow
from app.skydiver.social.store import _blocked, _row
from app.skydiver.social.tables import (
    SkydiverFollow,
    SkydiverProfile,
    SkydiverSocialReport,
)

J, E, T = SkydiverJump, SkydiverJumpEvent, SkydiverJumpPost
P, F, R = SkydiverProfile, SkydiverFollow, SkydiverSocialReport

_SHARED_COLUMN = {
    Share.TYPE: T.jump_type,
    Share.VENUE: T.venue_id,
    Share.ALTITUDE: T.exit_altitude,
    Share.FREEFALL: T.freefall_seconds,
}


def readable_by(viewer: uuid.UUID | None) -> Any:
    """Whether `viewer` may read a post row; needs `P` joined on the post's owner.

    The owner always. Anyone else only while the owner's profile is not hidden and,
    signed in, no block exists either way; then a public post of a discoverable
    profile, or any post when the viewer is an approved follower.
    """
    public = and_(col(T.audience) == Audience.PUBLIC.value, col(P.discoverable))
    shown = col(P.hidden_at).is_(None)
    if viewer is None:
        return and_(shown, public)
    follower = (
        exists()
        .where(col(F.follower_person_id) == viewer)
        .where(col(F.followee_person_id) == col(T.owner_person_id))
        .where(col(F.status) == "approved")
    )
    return or_(
        col(T.owner_person_id) == viewer,
        and_(shown, ~_blocked(viewer, col(T.owner_person_id)), or_(public, follower)),
    )


def withdraw(
    session: Session,
    owner: uuid.UUID,
    jump_id: uuid.UUID,
    changed: set[str],
) -> bool:
    """Delete the jump's post if `changed` touches a value it shares. Same transaction."""
    date_changed, parts = policy.touched(changed)
    if not date_changed and not parts:
        return False
    query = (
        delete(T)
        .where(col(T.jump_id) == jump_id)
        .where(col(T.owner_person_id) == owner)
    )
    if not date_changed:
        query = query.where(
            or_(*(col(_SHARED_COLUMN[part]).is_not(None) for part in parts))
        )
    return session.execute(query.returning(col(T.id))).first() is not None


def _utc(value: datetime) -> datetime:
    return value.astimezone(UTC)


def _post(t: SkydiverJumpPost) -> Post:
    return Post(
        id=t.id,
        owner_person_id=t.owner_person_id,
        jump_id=t.jump_id,
        source_version=t.source_version,
        audience=Audience(t.audience),
        jumped_on=t.jumped_on,
        jump_type=t.jump_type,
        venue_id=t.venue_id,
        exit_altitude=t.exit_altitude,
        altitude_unit=t.altitude_unit,
        altitude_datum=t.altitude_datum,
        freefall_seconds=t.freefall_seconds,
        caption=t.caption,
        link=t.link,
        version=t.version,
        published_at=_utc(t.published_at),
    )


_SOURCE_COLUMNS = (
    col(J.id),
    col(J.version),
    col(J.jumped_on),
    col(J.jump_type),
    col(J.venue_id),
    col(J.exit_altitude),
    col(J.altitude_unit),
    col(J.altitude_datum),
    col(J.freefall_seconds),
)


def _source(row: Any) -> Source:
    return Source(*row)


class SqlPostStore:
    def __init__(self, session: Session) -> None:
        self._s = session

    def source(self, owner: uuid.UUID, jump_id: uuid.UUID) -> Source | None:
        row = self._s.execute(
            select(*_SOURCE_COLUMNS)
            .where(col(J.id) == jump_id)
            .where(col(J.owner_person_id) == owner)
        ).first()
        return _source(row) if row else None

    def lock_source(
        self, owner: uuid.UUID, jump_id: uuid.UUID, version: int
    ) -> Source | None:
        row = self._s.execute(
            update(J)
            .where(col(J.id) == jump_id)
            .where(col(J.owner_person_id) == owner)
            .where(col(J.version) == version)
            .values(version=col(J.version))
            .returning(*_SOURCE_COLUMNS)
        ).first()
        return _source(row) if row else None

    def profile(self, person_id: uuid.UUID) -> ProfileRow | None:
        found = self._s.get(P, person_id)
        return _row(found) if found else None

    def admit_profile(self, person_id: uuid.UUID, audience: Audience) -> bool:
        query = (
            update(P)
            .where(col(P.person_id) == person_id)
            .where(col(P.hidden_at).is_(None))
            .where(col(P.publishing_restricted_at).is_(None))
            .values(version=col(P.version))
        )
        if audience is Audience.PUBLIC:
            query = query.where(col(P.discoverable))
        return self._s.execute(query.returning(col(P.person_id))).first() is not None

    def post_for_jump(self, owner: uuid.UUID, jump_id: uuid.UUID) -> Post | None:
        found = self._s.execute(
            select(T)
            .where(col(T.jump_id) == jump_id)
            .where(col(T.owner_person_id) == owner)
        ).scalar_one_or_none()
        return _post(found) if found else None

    def insert_post(self, values: dict[str, Any]) -> Post | None:
        inserted = self._s.execute(
            pg_insert(T)
            .values(id=uuid.uuid7(), version=1, **values)
            .on_conflict_do_nothing(index_elements=["jump_id"])
            .returning(col(T.id))
        ).first()
        if inserted is None:
            return None
        found = self._s.get(T, inserted[0])
        assert found is not None
        return _post(found)

    def set_audience(
        self,
        owner: uuid.UUID,
        post_id: uuid.UUID,
        audience: Audience,
        now: datetime,
        *,
        expected_version: int,
    ) -> bool:
        result = self._s.execute(
            update(T)
            .where(col(T.id) == post_id)
            .where(col(T.owner_person_id) == owner)
            .where(col(T.version) == expected_version)
            .values(
                audience=audience.value, version=expected_version + 1, updated_at=now
            )
        )
        return bool(result.rowcount == 1)  # type: ignore[attr-defined]

    def delete_post(
        self, owner: uuid.UUID, post_id: uuid.UUID, expected_version: int | None
    ) -> uuid.UUID | None:
        query = (
            delete(T).where(col(T.id) == post_id).where(col(T.owner_person_id) == owner)
        )
        if expected_version is not None:
            query = query.where(col(T.version) == expected_version)
        row = self._s.execute(query.returning(col(T.jump_id))).first()
        return row[0] if row else None

    def owned(self, owner: uuid.UUID, post_id: uuid.UUID) -> Post | None:
        found = self._s.execute(
            select(T).where(col(T.id) == post_id).where(col(T.owner_person_id) == owner)
        ).scalar_one_or_none()
        return _post(found) if found else None

    def _readable(self, viewer: uuid.UUID | None, *where: Any, limit: int) -> list[tuple[Post, Person]]:  # fmt: skip
        rows = self._s.execute(
            select(T, col(P.handle), col(P.display_name))
            .join(P, col(P.person_id) == col(T.owner_person_id))
            .where(readable_by(viewer), *where)
            .order_by(col(T.id).desc())
            .limit(limit)
        ).all()
        return [(_post(t), Person(handle, name)) for t, handle, name in rows]

    def readable(
        self, viewer: uuid.UUID | None, post_id: uuid.UUID
    ) -> tuple[Post, Person] | None:
        found = self._readable(viewer, col(T.id) == post_id, limit=1)
        return found[0] if found else None

    def by_owner(
        self,
        viewer: uuid.UUID | None,
        owner: uuid.UUID,
        before: uuid.UUID | None,
        limit: int,
    ) -> list[tuple[Post, Person]]:
        where = [col(T.owner_person_id) == owner]
        if before is not None:
            where.append(col(T.id) < before)
        return self._readable(viewer, *where, limit=limit)

    def record(
        self,
        owner: uuid.UUID,
        jump_id: uuid.UUID,
        kind: str,
        detail: dict[str, Any],
        now: datetime,
    ) -> None:
        self._s.add(
            E(
                owner_person_id=owner,
                jump_id=jump_id,
                kind=kind,
                detail=detail,
                created_at=now,
            )
        )
        self._s.flush()

    def insert_report(self, values: dict[str, Any]) -> bool:
        result = self._s.execute(
            pg_insert(R)
            .values(id=uuid.uuid7(), **values)
            .on_conflict_do_nothing(
                index_elements=["reporter_person_id", "target_person_id", "post_key"],
                index_where=col(R.status) == "open",
            )
            .returning(col(R.id))
        )
        return result.first() is not None


def sql_post_store_factory(engine: Engine) -> StoreFactory:
    """Unit of work: commit on success, roll back on any exception."""

    @contextmanager
    def stores() -> Iterator[PostStore]:
        with Session(engine) as session:
            try:
                yield SqlPostStore(session)
            except BaseException:
                session.rollback()
                raise
            session.commit()

    return stores
