"""SQL adapter for the private jump logbook (#153). Every query is owner-scoped."""

import uuid
from collections.abc import Iterator
from contextlib import contextmanager
from datetime import date, datetime
from typing import Any

from sqlalchemy import (
    ColumnElement,
    Engine,
    and_,
    delete,
    false,
    func,
    insert,
    or_,
    select,
    type_coerce,
    update,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.exc import IntegrityError
from sqlmodel import Session, col

from app.skydiver.access.policy import Actor
from app.skydiver.access.sql import get_owned, lock_owner, owned
from app.skydiver.directory.service import EditConflict
from app.skydiver.directory.tables import SkydiverProvisionalPlace
from app.skydiver.gear.tables import SkydiverComponent
from app.skydiver.logbook.policy import AltitudeDatum, AltitudeUnit, JumpType
from app.skydiver.logbook.service import (
    BatchRecord,
    ComponentRef,
    Criteria,
    Jump,
    JumpEvent,
    LogbookStore,
    NumberedRef,
    PlaceRef,
    Receipt,
    StoreFactory,
    Totals,
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
        aircraft=row.aircraft,
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

    def lock_owner(self, actor: Actor) -> None:
        lock_owner(self._s, actor)

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

    def jumps_by_ids(self, actor: Actor, jump_ids: list[uuid.UUID]) -> list[Jump]:
        if not jump_ids:
            return []
        rows = self._s.execute(
            owned(J, actor).where(col(J.id).in_(jump_ids)).order_by(col(J.id))
        ).scalars()
        return self._with_components(list(rows))

    def latest_batch(self, actor: Actor) -> BatchRecord | None:
        # The newest change of many jumps still on record. If every jump of the
        # newest one was deleted, the one before it is found again: its undo still
        # needs the 24 hours and puts back only jumps untouched since (compare-and-
        # swap on the version it produced), so it never overwrites later work. No
        # extra per-person storage is kept for that case.
        detail = type_coerce(col(E.detail), JSONB())
        latest = (
            self._s.execute(
                owned(E, actor)
                .where(detail.has_key("batch"))
                .order_by(col(E.id).desc())
                .limit(1)
            )
            .scalars()
            .first()
        )
        if latest is None:
            return None
        batch_id = str(latest.detail["batch"]["id"])
        entries = self._s.execute(
            owned(E, actor)
            .where(detail["batch"]["id"].astext == batch_id)
            .order_by(col(E.id))
        ).scalars()
        undone = self._s.execute(
            select(func.count())
            .select_from(E)
            .where(col(E.owner_person_id) == actor.person_id)
            .where(detail["undo_of"].astext == batch_id)
        ).scalar_one()
        return BatchRecord(
            id=uuid.UUID(batch_id),
            created_at=latest.created_at,
            entries=[(e.jump_id, dict(e.detail)) for e in entries],
            undone=bool(undone),
        )

    def page(
        self,
        actor: Actor,
        after: tuple[date, uuid.UUID] | None,
        limit: int,
        where: Criteria = Criteria(),
    ) -> list[Jump]:
        query = owned(J, actor).where(*_conditions(actor, where))
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

    def totals(self, actor: Actor, where: Criteria) -> Totals:
        jumps, seconds, recorded, first, last = self._s.execute(
            select(
                func.count(),
                func.sum(col(J.freefall_seconds)),
                func.count(col(J.freefall_seconds)),
                func.min(col(J.jumped_on)),
                func.max(col(J.jumped_on)),
            )
            .where(col(J.owner_person_id) == actor.person_id)
            .where(*_conditions(actor, where))
        ).one()
        return Totals(
            jumps=int(jumps),
            freefall_seconds=int(seconds) if seconds is not None else None,
            freefall_recorded=int(recorded),
            first_on=first,
            last_on=last,
        )

    def latest_aircraft(self, actor: Actor, where: Criteria) -> str | None:
        found = self._s.execute(
            select(col(J.aircraft))
            .where(col(J.owner_person_id) == actor.person_id)
            .where(col(J.aircraft).is_not(None))
            .where(*_conditions(actor, where))
            .order_by(col(J.jumped_on).desc(), col(J.id).desc())
            .limit(1)
        ).scalar()
        return str(found) if found is not None else None

    def venue_ids(self, actor: Actor) -> list[uuid.UUID]:
        rows = self._s.execute(
            select(col(J.venue_id))
            .where(col(J.owner_person_id) == actor.person_id)
            .where(col(J.venue_id).is_not(None))
            .distinct()
        ).scalars()
        return [v for v in rows if v is not None]

    def numbered(self, actor: Actor) -> list[NumberedRef]:
        rows = self._s.execute(
            select(col(J.id), col(J.jumped_on), col(J.jump_number))
            .where(col(J.owner_person_id) == actor.person_id)
            .where(col(J.jump_number).is_not(None))
            .order_by(col(J.jump_number), col(J.jumped_on), col(J.id))
        )
        return [NumberedRef(i, on, int(n)) for i, on, n in rows.all()]

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
        # Same facts only count against a jump without a number: one with a different
        # number is the jumper's own word that it is another jump (the same number is
        # caught above). An unnumbered match may be this jump entered again, numbered.
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

    def in_order(
        self,
        actor: Actor,
        from_on: date | None,
        until_on: date | None,
        after: tuple[date, uuid.UUID] | None,
        limit: int,
    ) -> list[Jump]:
        query = owned(J, actor)
        if from_on is not None:
            query = query.where(col(J.jumped_on) >= from_on)
        if until_on is not None:
            query = query.where(col(J.jumped_on) <= until_on)
        if after is not None:
            on, last_id = after
            query = query.where(
                or_(
                    col(J.jumped_on) > on,
                    and_(col(J.jumped_on) == on, col(J.id) > last_id),
                )
            )
        rows = self._s.execute(
            query.order_by(col(J.jumped_on), col(J.id)).limit(limit)
        ).scalars()
        return self._with_components(list(rows))

    def totals_before(self, actor: Actor, on: date) -> tuple[int, int]:
        count, freefall = self._s.execute(
            select(func.count(), func.coalesce(func.sum(col(J.freefall_seconds)), 0))
            .where(col(J.owner_person_id) == actor.person_id)
            .where(col(J.jumped_on) < on)
        ).one()
        return int(count), int(freefall)

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


def _conditions(actor: Actor, where: Criteria) -> list[ColumnElement[bool]]:
    """Filter conditions; the caller already scopes the query to the owner."""
    found: list[ColumnElement[bool]] = []
    if where.text:
        P = SkydiverProvisionalPlace
        places = (
            select(col(P.id))
            .where(col(P.owner_person_id) == actor.person_id)
            .where(col(P.name).icontains(where.text, autoescape=True))
        )
        matches: list[ColumnElement[bool]] = [
            col(J.notes).icontains(where.text, autoescape=True),
            col(J.aircraft).icontains(where.text, autoescape=True),
            col(J.place_id).in_(places),
        ]
        if where.text_venue_ids:
            matches.append(col(J.venue_id).in_(where.text_venue_ids))
        found.append(or_(*matches))
    if where.jump_type is not None:
        found.append(col(J.jump_type) == where.jump_type)
    if where.venue_ids is not None:
        found.append(
            col(J.venue_id).in_(where.venue_ids) if where.venue_ids else false()
        )
    if where.place_id is not None:
        found.append(col(J.place_id) == where.place_id)
    if where.from_date is not None:
        found.append(col(J.jumped_on) >= where.from_date)
    if where.to_date is not None:
        found.append(col(J.jumped_on) <= where.to_date)
    if where.number_from is not None:
        found.append(col(J.jump_number) >= where.number_from)
    if where.number_to is not None:
        found.append(col(J.jump_number) <= where.number_to)
    return found


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
