"""SQL adapter for profiles, follows, blocks and reports (#156)."""

import uuid
from collections.abc import Iterator
from contextlib import contextmanager
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import (
    DateTime,
    Engine,
    String,
    Uuid,
    and_,
    delete,
    exists,
    func,
    literal,
    or_,
    select,
    update,
)
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlmodel import Session, col

from app.skydiver.directory.service import EditConflict
from app.skydiver.social.service import (
    Person,
    ProfileRow,
    Report,
    SocialStore,
    StoreFactory,
)
from app.skydiver.social.tables import (
    SkydiverBlock,
    SkydiverFollow,
    SkydiverProfile,
    SkydiverSocialReport,
)

P, F, B, R = SkydiverProfile, SkydiverFollow, SkydiverBlock, SkydiverSocialReport


def _row(p: SkydiverProfile) -> ProfileRow:
    return ProfileRow(
        person_id=p.person_id,
        handle=p.handle,
        display_name=p.display_name,
        bio=p.bio,
        disciplines=tuple(p.disciplines or ()),
        home_venue_id=p.home_venue_id,
        discoverable=p.discoverable,
        hidden=p.hidden_at is not None,
        publishing_restricted=p.publishing_restricted_at is not None,
        moderation_reason=p.moderation_reason,
        version=p.version,
        created_at=p.created_at,
        updated_at=p.updated_at,
    )


def _blocked(a: Any, b: Any) -> Any:
    """A block between persons `a` and `b`, in either direction."""
    return exists().where(
        or_(
            and_(col(B.blocker_person_id) == a, col(B.blocked_person_id) == b),
            and_(col(B.blocker_person_id) == b, col(B.blocked_person_id) == a),
        )
    )


def _utc(value: datetime | None) -> datetime | None:
    return value.astimezone(UTC) if value is not None else None


class SqlSocialStore:
    def __init__(self, session: Session) -> None:
        self._s = session

    # profiles ---------------------------------------------------------------------

    def profile(self, person_id: uuid.UUID) -> ProfileRow | None:
        row = self._s.get(P, person_id, populate_existing=True)
        return _row(row) if row else None

    def profile_by_handle(self, handle: str) -> ProfileRow | None:
        row = (
            self._s.execute(select(P).where(col(P.handle) == handle)).scalars().first()
        )
        return _row(row) if row else None

    def insert_profile(
        self, person_id: uuid.UUID, values: dict[str, Any], now: datetime
    ) -> bool:
        result = self._s.execute(
            pg_insert(P)
            .values(
                person_id=person_id, version=1, created_at=now, updated_at=now, **values
            )
            .on_conflict_do_nothing()
            .returning(col(P.person_id))
        )
        return result.first() is not None

    def update_profile(
        self,
        person_id: uuid.UUID,
        values: dict[str, Any],
        now: datetime,
        *,
        expected_version: int,
    ) -> None:
        result = self._s.execute(
            update(P)
            .where(col(P.person_id) == person_id)
            .where(col(P.version) == expected_version)
            .values(**values, version=expected_version + 1, updated_at=now)
        )
        if result.rowcount != 1:  # type: ignore[attr-defined]
            raise EditConflict()

    def moderate_profile(self, person_id: uuid.UUID, values: dict[str, Any]) -> None:
        # Reviewer state is not the owner's edit: the owner's version is unchanged.
        self._s.execute(update(P).where(col(P.person_id) == person_id).values(**values))

    # follows and blocks -------------------------------------------------------------

    def follow_status(self, follower: uuid.UUID, followee: uuid.UUID) -> str | None:
        return self._s.execute(
            select(col(F.status))
            .where(col(F.follower_person_id) == follower)
            .where(col(F.followee_person_id) == followee)
        ).scalar_one_or_none()

    def blocks(self, blocker: uuid.UUID, blocked: uuid.UUID) -> bool:
        return bool(
            self._s.execute(
                select(
                    exists()
                    .where(col(B.blocker_person_id) == blocker)
                    .where(col(B.blocked_person_id) == blocked)
                )
            ).scalar_one()
        )

    def insert_follow(
        self, follower: uuid.UUID, followee: uuid.UUID, now: datetime
    ) -> bool:
        source = select(
            literal(follower, Uuid()),
            literal(followee, Uuid()),
            literal("pending", String()),
            literal(now, DateTime(timezone=True)),
        ).where(~_blocked(follower, followee))
        result = self._s.execute(
            pg_insert(F)
            .from_select(
                ["follower_person_id", "followee_person_id", "status", "created_at"],
                source,
            )
            .on_conflict_do_nothing()
            .returning(col(F.follower_person_id))
        )
        return result.first() is not None

    def approve_follow(
        self, follower: uuid.UUID, followee: uuid.UUID, now: datetime
    ) -> bool:
        result = self._s.execute(
            update(F)
            .where(col(F.follower_person_id) == follower)
            .where(col(F.followee_person_id) == followee)
            .where(col(F.status) == "pending")
            .where(~_blocked(follower, followee))
            .values(status="approved", approved_at=now)
        )
        return bool(result.rowcount == 1)  # type: ignore[attr-defined]

    def delete_follow(
        self, follower: uuid.UUID, followee: uuid.UUID, status: str | None
    ) -> bool:
        query = (
            delete(F)
            .where(col(F.follower_person_id) == follower)
            .where(col(F.followee_person_id) == followee)
        )
        if status is not None:
            query = query.where(col(F.status) == status)
        return bool(self._s.execute(query).rowcount)  # type: ignore[attr-defined]

    def count_following(self, follower: uuid.UUID) -> int:
        return int(
            self._s.execute(
                select(func.count())
                .select_from(F)
                .where(col(F.follower_person_id) == follower)
            ).scalar_one()
        )

    def count_pending(self, followee: uuid.UUID) -> int:
        return int(
            self._s.execute(
                select(func.count())
                .select_from(F)
                .where(col(F.followee_person_id) == followee)
                .where(col(F.status) == "pending")
                .where(~_blocked(col(F.follower_person_id), followee))
            ).scalar_one()
        )

    def insert_block(
        self, blocker: uuid.UUID, blocked: uuid.UUID, now: datetime
    ) -> None:
        self._s.execute(
            pg_insert(B)
            .values(
                blocker_person_id=blocker, blocked_person_id=blocked, created_at=now
            )
            .on_conflict_do_nothing()
        )
        self._s.execute(
            delete(F).where(
                or_(
                    and_(
                        col(F.follower_person_id) == blocker,
                        col(F.followee_person_id) == blocked,
                    ),
                    and_(
                        col(F.follower_person_id) == blocked,
                        col(F.followee_person_id) == blocker,
                    ),
                )
            )
        )

    def delete_block(self, blocker: uuid.UUID, blocked: uuid.UUID) -> bool:
        result = self._s.execute(
            delete(B)
            .where(col(B.blocker_person_id) == blocker)
            .where(col(B.blocked_person_id) == blocked)
        )
        return bool(result.rowcount)  # type: ignore[attr-defined]

    def count_blocks(self, blocker: uuid.UUID) -> int:
        return int(
            self._s.execute(
                select(func.count())
                .select_from(B)
                .where(col(B.blocker_person_id) == blocker)
            ).scalar_one()
        )

    def people(self, person_id: uuid.UUID, relation: str, limit: int) -> list[Person]:
        query: Any
        if relation == "blocked":
            query = (
                select(col(P.handle), col(P.display_name), col(B.created_at))
                .join(B, col(B.blocked_person_id) == col(P.person_id))
                .where(col(B.blocker_person_id) == person_id)
                .order_by(col(B.created_at).desc())
            )
        else:
            other, me = (
                (F.follower_person_id, F.followee_person_id)
                if relation in ("requests", "followers")
                else (F.followee_person_id, F.follower_person_id)
            )
            status = "pending" if relation == "requests" else "approved"
            when = F.created_at if relation == "requests" else F.approved_at
            query = (
                select(col(P.handle), col(P.display_name), col(when))
                .join(F, col(other) == col(P.person_id))
                .where(col(me) == person_id)
                .where(col(F.status) == status)
                .where(~_blocked(col(other), person_id))
                .order_by(col(when).desc())
            )
        rows = self._s.execute(query.limit(limit)).all()
        return [Person(h, n, _utc(at)) for h, n, at in rows]

    def search(self, viewer: uuid.UUID, query: str, limit: int) -> list[Person]:
        pattern = (
            "%"
            + query.replace("\\", "\\\\").replace("%", "\\%").replace("_", "\\_")
            + "%"
        )
        rows = self._s.execute(
            select(col(P.handle), col(P.display_name))
            .where(col(P.discoverable).is_(True))
            .where(col(P.hidden_at).is_(None))
            .where(col(P.person_id) != viewer)
            .where(~_blocked(col(P.person_id), viewer))
            .where(
                or_(
                    col(P.handle).ilike(pattern, escape="\\"),
                    col(P.display_name).ilike(pattern, escape="\\"),
                )
            )
            .order_by(col(P.handle))
            .limit(limit)
        ).all()
        return [Person(h, n) for h, n in rows]

    # reports ----------------------------------------------------------------------

    def insert_report(self, values: dict[str, Any]) -> bool:
        result = self._s.execute(
            pg_insert(R)
            .values(id=uuid.uuid7(), **values)
            .on_conflict_do_nothing(
                index_elements=["reporter_person_id", "target_person_id"],
                index_where=col(R.status) == "open",
            )
            .returning(col(R.id))
        )
        return result.first() is not None

    def _reports(self, *where: Any, limit: int) -> list[Report]:
        reporter = P.__table__.alias("reporter")  # type: ignore[attr-defined]
        target = P.__table__.alias("target")  # type: ignore[attr-defined]
        rows = self._s.execute(
            select(
                R,
                reporter.c.handle.label("reporter_handle"),
                reporter.c.display_name.label("reporter_name"),
                target.c.handle.label("target_handle"),
                target.c.display_name.label("target_name"),
                target.c.hidden_at.label("target_hidden_at"),
                target.c.publishing_restricted_at.label("target_restricted_at"),
            )
            .join(target, target.c.person_id == col(R.target_person_id))
            .outerjoin(reporter, reporter.c.person_id == col(R.reporter_person_id))
            .where(*where)
            .order_by(col(R.id).desc())
            .limit(limit)
        ).all()
        out = []
        for row in rows:
            r, m = row[0], row._mapping
            out.append(
                Report(
                    id=r.id,
                    reporter=Person(m["reporter_handle"], m["reporter_name"])
                    if m["reporter_handle"]
                    else None,
                    target=Person(m["target_handle"], m["target_name"]),
                    reason=r.reason,
                    note=r.note,
                    snapshot=dict(r.snapshot),
                    status=r.status,
                    decision=r.decision,
                    decision_reason=r.decision_reason,
                    created_at=r.created_at.astimezone(UTC),
                    decided_at=_utc(r.decided_at),
                    target_hidden=m["target_hidden_at"] is not None,
                    target_publishing_restricted=m["target_restricted_at"] is not None,
                )
            )
        return out

    def reports(self, status: str, limit: int) -> list[Report]:
        return self._reports(col(R.status) == status, limit=limit)

    def report(self, report_id: uuid.UUID) -> Report | None:
        found = self._reports(col(R.id) == report_id, limit=1)
        return found[0] if found else None

    def close_report(
        self,
        report_id: uuid.UUID,
        decision: str,
        reason: str | None,
        reviewer: uuid.UUID,
        now: datetime,
    ) -> bool:
        result = self._s.execute(
            update(R)
            .where(col(R.id) == report_id)
            .where(col(R.status) == "open")
            .values(
                status="closed",
                decision=decision,
                decision_reason=reason,
                decided_by_account_id=reviewer,
                decided_at=now,
            )
        )
        return bool(result.rowcount == 1)  # type: ignore[attr-defined]


def sql_social_store_factory(engine: Engine) -> StoreFactory:
    """Unit of work: commit on success, roll back on any exception."""

    @contextmanager
    def stores() -> Iterator[SocialStore]:
        with Session(engine) as session:
            try:
                yield SqlSocialStore(session)
            except BaseException:
                session.rollback()
                raise
            session.commit()

    return stores
