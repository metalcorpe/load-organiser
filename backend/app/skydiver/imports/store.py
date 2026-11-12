"""SQL adapter for the logbook import. Every private query is owner-scoped."""

import uuid
from collections.abc import Iterator
from contextlib import contextmanager
from datetime import UTC, datetime
from typing import Any

from sqlalchemy import Engine, and_, delete, exists, func, insert, or_, select, update
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlmodel import Session, SQLModel, col

from app.skydiver.access.policy import Actor
from app.skydiver.access.sql import get_owned, lock_owner, owned
from app.skydiver.directory.policy import PUBLIC_STATUSES
from app.skydiver.directory.tables import (
    SkydiverProvisionalPlace,
    SkydiverVenue,
    SkydiverVenueAlias,
)
from app.skydiver.imports.service import (
    Existing,
    ImportRecord,
    ImportStore,
    PlaceName,
    StoreFactory,
    VenueName,
)
from app.skydiver.logbook.store import CORE
from app.skydiver.logbook.tables import (
    SkydiverJump,
    SkydiverJumpEvent,
    SkydiverJumpImport,
)
from app.skydiver.saves.tables import SkydiverVisitPlan

J, I, P = SkydiverJump, SkydiverJumpImport, SkydiverProvisionalPlace  # noqa: E741
V, A = SkydiverVenue, SkydiverVenueAlias

TABLES: dict[str, type[SQLModel]] = {
    "places": SkydiverProvisionalPlace,
    "jumps": SkydiverJump,
    "jump_events": SkydiverJumpEvent,
}


def _utc(value: datetime | None) -> datetime | None:
    return value.astimezone(UTC) if value is not None else None


def _record(row: SkydiverJumpImport) -> ImportRecord:
    created = _utc(row.created_at)
    assert created is not None
    return ImportRecord(
        id=row.id,
        created_at=created,
        counts={k: int(v) for k, v in dict(row.counts).items()},
        undone_at=_utc(row.undone_at),
        place_ids=tuple(uuid.UUID(str(p)) for p in row.place_ids or ()),
    )


class SqlImportStore:
    def __init__(self, session: Session) -> None:
        self._s = session

    def _count(self, model: type[SQLModel], actor: Actor) -> int:
        owner = col(getattr(model, "owner_person_id"))  # noqa: B009
        return int(
            self._s.execute(
                select(func.count()).select_from(model).where(owner == actor.person_id)
            ).scalar_one()
        )

    def lock_owner(self, actor: Actor) -> None:
        lock_owner(self._s, actor)

    def next_sequence(self, actor: Actor) -> int:
        latest = self._s.execute(
            select(func.max(col(I.sequence))).where(
                col(I.owner_person_id) == actor.person_id
            )
        ).scalar_one()
        return int(latest or 0) + 1

    def count_jumps(self, actor: Actor) -> int:
        return self._count(J, actor)

    def count_places(self, actor: Actor) -> int:
        return self._count(P, actor)

    def venues_named(self, keys: list[str]) -> list[VenueName]:
        public = [s.value for s in PUBLIC_STATUSES]
        rows = self._s.execute(
            select(col(V.id), col(V.name), col(V.country))
            .where(col(V.status).in_(public))
            .where(
                or_(
                    col(V.name_key).in_(keys),
                    exists().where(
                        and_(col(A.venue_id) == V.id, col(A.alias_key).in_(keys))
                    ),
                )
            )
            .order_by(col(V.id))
        ).all()
        if not rows:
            return []
        aliases: dict[uuid.UUID, list[str]] = {}
        for venue_id, alias in self._s.execute(
            select(col(A.venue_id), col(A.alias))
            .where(col(A.venue_id).in_([r[0] for r in rows]))
            .order_by(col(A.alias))
        ).all():
            aliases.setdefault(venue_id, []).append(alias)
        return [
            VenueName(id=i, country=c, names=(n, *aliases.get(i, [])))
            for i, n, c in rows
        ]

    def own_places(self, actor: Actor) -> list[PlaceName]:
        rows = self._s.execute(
            owned(P, actor).order_by(col(P.created_at), col(P.id))
        ).scalars()
        return [PlaceName(r.id, r.name) for r in rows]

    def existing(self, actor: Actor) -> Existing:
        numbers = self._s.execute(
            select(col(J.jump_number))
            .where(col(J.owner_person_id) == actor.person_id)
            .where(col(J.jump_number).is_not(None))
        ).scalars()
        cores = self._s.execute(
            select(*(col(getattr(J, name)) for name in CORE))
            .where(col(J.owner_person_id) == actor.person_id)
            .where(col(J.jump_number).is_(None))
        ).all()
        return Existing(frozenset(numbers), frozenset(tuple(r) for r in cores))

    def by_fingerprint(self, actor: Actor, fingerprint: str) -> ImportRecord | None:
        row = (
            self._s.execute(owned(I, actor).where(col(I.fingerprint) == fingerprint))
            .scalars()
            .first()
        )
        return _record(row) if row else None

    def get(self, actor: Actor, import_id: uuid.UUID) -> ImportRecord | None:
        row = get_owned(self._s, I, import_id, actor)
        return _record(row) if row else None

    def recent(self, actor: Actor, limit: int) -> list[ImportRecord]:
        rows = self._s.execute(
            owned(I, actor).order_by(col(I.id).desc()).limit(limit)
        ).scalars()
        return [_record(r) for r in rows]

    def forget(self, actor: Actor, import_id: uuid.UUID) -> None:
        self._s.execute(
            delete(I)
            .where(col(I.id) == import_id)
            .where(col(I.owner_person_id) == actor.person_id)
            .where(col(I.undone_at).is_not(None))
        )

    def claim(
        self, actor: Actor, record: ImportRecord, fingerprint: str, sequence: int
    ) -> bool:
        result = self._s.execute(
            pg_insert(I)
            .values(
                id=record.id,
                owner_person_id=actor.person_id,
                fingerprint=fingerprint,
                sequence=sequence,
                counts=record.counts,
                place_ids=[str(p) for p in record.place_ids],
                created_at=record.created_at,
            )
            .on_conflict_do_nothing()
            .returning(col(I.id))
        )
        return result.first() is not None

    def insert_rows(self, table: str, rows: list[dict[str, Any]]) -> None:
        if rows:
            self._s.execute(insert(TABLES[table]), rows)

    def mark_undone(
        self, actor: Actor, import_id: uuid.UUID, counts: dict[str, int], now: datetime
    ) -> bool:
        result = self._s.execute(
            update(I)
            .where(col(I.id) == import_id)
            .where(col(I.owner_person_id) == actor.person_id)
            .where(col(I.undone_at).is_(None))
            .values(undone_at=now, counts=counts)
            .returning(col(I.id))
        )
        return result.first() is not None

    def delete_jumps(self, actor: Actor, import_id: uuid.UUID) -> int:
        result = self._s.execute(
            delete(J)
            .where(col(J.owner_person_id) == actor.person_id)
            .where(col(J.import_id) == import_id)
        )
        return int(result.rowcount)  # type: ignore[attr-defined]

    def delete_unused_places(
        self, actor: Actor, place_ids: tuple[uuid.UUID, ...]
    ) -> int:
        if not place_ids:
            return 0
        result = self._s.execute(
            delete(P)
            .where(col(P.owner_person_id) == actor.person_id)
            .where(col(P.id).in_(place_ids))
            .where(~exists().where(col(J.place_id) == P.id))
            .where(~exists().where(col(SkydiverVisitPlan.place_id) == P.id))
        )
        return int(result.rowcount)  # type: ignore[attr-defined]


def sql_import_store_factory(engine: Engine) -> StoreFactory:
    """Unit of work: commit on success, roll back on any exception."""

    @contextmanager
    def stores() -> Iterator[ImportStore]:
        with Session(engine) as session:
            try:
                yield SqlImportStore(session)
            except BaseException:
                session.rollback()
                raise
            session.commit()

    return stores
