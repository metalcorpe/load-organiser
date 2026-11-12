"""SQL adapter for the private jump logbook (#153). Every query is owner-scoped."""

import uuid
from collections.abc import Iterator
from contextlib import contextmanager
from datetime import date, datetime
from typing import Any

from sqlalchemy import Engine, and_, delete, func, insert, or_, select, update
from sqlalchemy.exc import IntegrityError
from sqlmodel import Session, col

from app.skydiver.access.policy import Actor
from app.skydiver.access.sql import get_owned, owned
from app.skydiver.directory.service import EditConflict
from app.skydiver.directory.tables import SkydiverProvisionalPlace
from app.skydiver.gear.tables import SkydiverComponent
from app.skydiver.logbook.policy import AltitudeDatum, AltitudeUnit, JumpType
from app.skydiver.logbook.service import (
    ComponentRef,
    Jump,
    JumpEvent,
    LogbookStore,
    PlaceRef,
    Receipt,
    StoreFactory,
)
from app.skydiver.logbook.tables import (
    SkydiverJump,
    SkydiverJumpComponent,
    SkydiverJumpEvent,
    SkydiverJumpReceipt,
)
from app.skydiver.posts import store as posts

_UNIQUE_VIOLATION = "23505"
J, L, R, E = SkydiverJump, SkydiverJumpComponent, SkydiverJumpReceipt, SkydiverJumpEvent

# Facts compared for the likely-duplicate warning (besides the jump number).
CORE = (
    "jumped_on",
    "venue_id",
    "place_id",
    "jump_type",
    "exit_time",
    "exit_altitude",
    "deployment_altitude",
    "freefall_seconds",
    "notes",
)


def _jump(row: SkydiverJump, component_ids: list[uuid.UUID]) -> Jump:
    return Jump(
        id=row.id,
        jumped_on=row.jumped_on,
        venue_id=row.venue_id,
        place_id=row.place_id,
        jump_type=JumpType(row.jump_type),
        jump_number=row.jump_number,
        exit_time=row.exit_time,
        time_zone=row.time_zone,
        exit_altitude=row.exit_altitude,
        deployment_altitude=row.deployment_altitude,
        altitude_unit=AltitudeUnit(row.altitude_unit) if row.altitude_unit else None,
        altitude_datum=AltitudeDatum(row.altitude_datum),
        freefall_seconds=row.freefall_seconds,
        other_gear=row.other_gear,
        notes=row.notes,
        links=tuple(row.links or ()),
        component_ids=tuple(component_ids),
        source=row.source,
        version=row.version,
        created_at=row.created_at,
        updated_at=row.updated_at,
    )


class SqlLogbookStore:
    def __init__(self, session: Session) -> None:
        self._s = session

    def _with_components(self, rows: list[SkydiverJump]) -> list[Jump]:
        ids = [r.id for r in rows]
        used: dict[uuid.UUID, list[uuid.UUID]] = {i: [] for i in ids}
        if ids:
            links = self._s.execute(
                select(col(L.jump_id), col(L.component_id))
                .where(col(L.jump_id).in_(ids))
                .order_by(col(L.jump_id), col(L.component_id))
            )
            for jump_id, component_id in links.all():
                used[jump_id].append(component_id)
        return [_jump(r, used[r.id]) for r in rows]

    # reads -----------------------------------------------------------------------

    def count_jumps(self, actor: Actor) -> int:
        return int(
            self._s.execute(
                select(func.count())
                .select_from(J)
                .where(col(J.owner_person_id) == actor.person_id)
            ).scalar_one()
        )

    def receipt(self, actor: Actor, client_key: uuid.UUID) -> Receipt | None:
        row = (
            self._s.execute(owned(R, actor).where(col(R.client_key) == client_key))
            .scalars()
            .first()
        )
        return Receipt(row.fingerprint, row.jump_id) if row else None

    def get_jump(self, actor: Actor, jump_id: uuid.UUID) -> Jump | None:
        row = get_owned(self._s, J, jump_id, actor)
        return self._with_components([row])[0] if row else None

    def page(
        self, actor: Actor, after: tuple[date, uuid.UUID] | None, limit: int
    ) -> list[Jump]:
        query = owned(J, actor)
        if after is not None:
            on, last_id = after
            query = query.where(
                or_(
                    col(J.jumped_on) < on,
                    and_(col(J.jumped_on) == on, col(J.id) < last_id),
                )
            )
        rows = self._s.execute(
            query.order_by(col(J.jumped_on).desc(), col(J.id).desc()).limit(limit)
        ).scalars()
        return self._with_components(list(rows))

    def find_same(self, actor: Actor, values: dict[str, Any]) -> uuid.UUID | None:
        number = values.get("jump_number")
        if number is not None:
            found = self.same_number(actor, number, uuid.UUID(int=0))
            if found:
                return found[0]
        query = owned(J, actor)
        for name in CORE:
            column = col(getattr(J, name))
            value = values.get(name)
            query = query.where(column.is_(None) if value is None else column == value)
        if number is None:
            query = query.where(col(J.jump_number).is_(None))
        row = self._s.execute(query.order_by(col(J.id)).limit(1)).scalars().first()
        return row.id if row else None

    def same_number(
        self, actor: Actor, number: int, exclude: uuid.UUID
    ) -> list[uuid.UUID]:
        rows = self._s.execute(
            select(col(J.id))
            .where(col(J.owner_person_id) == actor.person_id)
            .where(col(J.jump_number) == number)
            .where(col(J.id) != exclude)
            .order_by(col(J.id))
        ).scalars()
        return list(rows)

    def components(
        self, actor: Actor, component_ids: list[uuid.UUID]
    ) -> list[ComponentRef]:
        if not component_ids:
            return []
        rows = self._s.execute(
            owned(SkydiverComponent, actor).where(
                col(SkydiverComponent.id).in_(component_ids)
            )
        ).scalars()
        return [
            ComponentRef(r.id, r.kind, r.label, r.archived_at is not None) for r in rows
        ]

    def places(self, actor: Actor, place_ids: list[uuid.UUID]) -> list[PlaceRef]:
        if not place_ids:
            return []
        rows = self._s.execute(
            owned(SkydiverProvisionalPlace, actor).where(
                col(SkydiverProvisionalPlace.id).in_(place_ids)
            )
        ).scalars()
        return [PlaceRef(r.id, r.name, r.country) for r in rows]

    def events(self, actor: Actor, jump_id: uuid.UUID) -> list[JumpEvent]:
        rows = self._s.execute(
            owned(E, actor).where(col(E.jump_id) == jump_id).order_by(col(E.id))
        ).scalars()
        return [JumpEvent(r.kind, dict(r.detail), r.created_at) for r in rows]

    # writes ----------------------------------------------------------------------

    def insert_jump(
        self,
        actor: Actor,
        client_key: uuid.UUID,
        fingerprint: str,
        values: dict[str, Any],
        component_ids: list[uuid.UUID],
        now: datetime,
    ) -> uuid.UUID | None:
        attempt = self._s.begin_nested()
        try:
            receipt = R(
                owner_person_id=actor.person_id,
                client_key=client_key,
                fingerprint=fingerprint,
                created_at=now,
            )
            self._s.add(receipt)
            self._s.flush()
        except IntegrityError as error:
            attempt.rollback()
            # Only a concurrent same-key create is a lost race; anything else is a bug.
            if getattr(error.orig, "sqlstate", None) != _UNIQUE_VIOLATION:
                raise
            return None
        row = J(
            owner_person_id=actor.person_id,
            created_at=now,
            updated_at=now,
            **values,
        )
        self._s.add(row)
        self._s.flush()
        receipt.jump_id = row.id
        self._link(actor, row.id, component_ids)
        self._s.flush()
        attempt.commit()
        return row.id

    def update_jump(
        self,
        actor: Actor,
        jump_id: uuid.UUID,
        values: dict[str, Any],
        component_ids: list[uuid.UUID] | None,
        now: datetime,
        *,
        expected_version: int,
    ) -> None:
        result = self._s.execute(
            update(J)
            .where(col(J.id) == jump_id)
            .where(col(J.owner_person_id) == actor.person_id)
            .where(col(J.version) == expected_version)
            .values(**values, version=expected_version + 1, updated_at=now)
        )
        if result.rowcount != 1:  # type: ignore[attr-defined]
            raise EditConflict()
        if component_ids is not None:
            self._s.execute(delete(L).where(col(L.jump_id) == jump_id))
            self._link(actor, jump_id, component_ids)

    def delete_jump(
        self, actor: Actor, jump_id: uuid.UUID, *, expected_version: int
    ) -> None:
        result = self._s.execute(
            delete(J)
            .where(col(J.id) == jump_id)
            .where(col(J.owner_person_id) == actor.person_id)
            .where(col(J.version) == expected_version)
        )
        if result.rowcount != 1:  # type: ignore[attr-defined]
            raise EditConflict()

    def withdraw_post(
        self, actor: Actor, jump_id: uuid.UUID, changed: set[str]
    ) -> bool:
        return posts.withdraw(self._s, actor.person_id, jump_id, changed)

    def record(
        self,
        actor: Actor,
        jump_id: uuid.UUID,
        kind: str,
        detail: dict[str, Any],
        now: datetime,
    ) -> None:
        self._s.add(
            E(
                owner_person_id=actor.person_id,
                jump_id=jump_id,
                kind=kind,
                detail=detail,
                created_at=now,
            )
        )
        self._s.flush()

    def _link(
        self, actor: Actor, jump_id: uuid.UUID, component_ids: list[uuid.UUID]
    ) -> None:
        if component_ids:
            self._s.execute(
                insert(L),
                [
                    {
                        "jump_id": jump_id,
                        "component_id": c,
                        "owner_person_id": actor.person_id,
                    }
                    for c in component_ids
                ],
            )


def sql_logbook_store_factory(engine: Engine) -> StoreFactory:
    """Unit of work: commit on success, roll back on any exception."""

    @contextmanager
    def stores() -> Iterator[LogbookStore]:
        with Session(engine) as session:
            try:
                yield SqlLogbookStore(session)
            except BaseException:
                session.rollback()
                raise
            session.commit()

    return stores
