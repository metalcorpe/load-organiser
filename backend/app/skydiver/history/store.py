"""SQL adapter for personal history (#154). Every query is owner-scoped."""

import uuid
from collections.abc import Iterator
from contextlib import contextmanager
from datetime import date, datetime
from typing import Any

from sqlalchemy import Engine, delete, func, select, update
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlmodel import Session, col

from app.skydiver.access.policy import Actor
from app.skydiver.access.sql import owned
from app.skydiver.directory.service import EditConflict
from app.skydiver.directory.tables import SkydiverProvisionalPlace
from app.skydiver.gear.tables import SkydiverComponent
from app.skydiver.history.currency import Licence
from app.skydiver.history.policy import Baseline
from app.skydiver.history.service import (
    BaselineEvent,
    BaselineState,
    EntryFacts,
    EntryRow,
    HistoryStore,
    StoreFactory,
)
from app.skydiver.history.tables import (
    SkydiverExitWeight,
    SkydiverJumpBaseline,
    SkydiverJumpBaselineEvent,
    SkydiverJumperLicence,
)
from app.skydiver.identity.tables import SkydiverPerson
from app.skydiver.logbook import loading
from app.skydiver.logbook.loading import WeightUnit
from app.skydiver.logbook.service import ComponentRef, ExitWeight, PlaceRef
from app.skydiver.logbook.store import main_canopies, usual_exit_weight
from app.skydiver.logbook.tables import SkydiverJump, SkydiverJumpComponent

B, E = SkydiverJumpBaseline, SkydiverJumpBaselineEvent
J, L, C = SkydiverJump, SkydiverJumpComponent, SkydiverComponent


class SqlHistoryStore:
    def __init__(self, session: Session) -> None:
        self._s = session

    def snapshot(self) -> None:
        # Must precede every query in the transaction; summaries then agree.
        self._s.connection(execution_options={"isolation_level": "REPEATABLE READ"})

    # baseline ---------------------------------------------------------------------

    def baseline(self, actor: Actor) -> BaselineState | None:
        row = self._s.execute(owned(B, actor)).scalars().first()
        if row is None:
            return None
        return BaselineState(
            row.prior_jumps, row.before_on, row.source, row.version, row.updated_at
        )

    def insert_baseline(self, actor: Actor, base: Baseline, now: datetime) -> bool:
        result = self._s.execute(
            pg_insert(B)
            .values(
                owner_person_id=actor.person_id,
                prior_jumps=base.prior_jumps,
                before_on=base.before_on,
                source="manual",
                version=1,
                created_at=now,
                updated_at=now,
            )
            .on_conflict_do_nothing(index_elements=["owner_person_id"])
            .returning(col(B.owner_person_id))
        )
        return result.first() is not None

    def update_baseline(
        self, actor: Actor, base: Baseline, now: datetime, *, expected_version: int
    ) -> None:
        result = self._s.execute(
            update(B)
            .where(col(B.owner_person_id) == actor.person_id)
            .where(col(B.version) == expected_version)
            .values(
                prior_jumps=base.prior_jumps,
                before_on=base.before_on,
                version=expected_version + 1,
                updated_at=now,
            )
        )
        if result.rowcount != 1:  # type: ignore[attr-defined]
            raise EditConflict()

    def delete_baseline(self, actor: Actor, *, expected_version: int) -> None:
        result = self._s.execute(
            delete(B)
            .where(col(B.owner_person_id) == actor.person_id)
            .where(col(B.version) == expected_version)
        )
        if result.rowcount != 1:  # type: ignore[attr-defined]
            raise EditConflict()

    def record(
        self, actor: Actor, kind: str, detail: dict[str, Any], now: datetime
    ) -> None:
        self._s.add(
            E(owner_person_id=actor.person_id, kind=kind, detail=detail, created_at=now)
        )
        self._s.flush()

    def events(self, actor: Actor, limit: int) -> list[BaselineEvent]:
        rows = self._s.execute(
            owned(E, actor).order_by(col(E.id).desc()).limit(limit)
        ).scalars()
        return [BaselineEvent(r.kind, dict(r.detail), r.created_at) for r in rows][::-1]

    # derived from detailed entries ----------------------------------------------

    def count_jumps(self, actor: Actor) -> int:
        return self._count(actor, None)

    def count_before(self, actor: Actor, on: date) -> int:
        return self._count(actor, on)

    def _count(self, actor: Actor, before: date | None) -> int:
        query = (
            select(func.count())
            .select_from(J)
            .where(col(J.owner_person_id) == actor.person_id)
        )
        if before is not None:
            query = query.where(col(J.jumped_on) < before)
        return int(self._s.execute(query).scalar_one())

    # licence ----------------------------------------------------------------------

    def licence(self, actor: Actor) -> Licence:
        row = self._s.execute(owned(SkydiverJumperLicence, actor)).scalars().first()
        return Licence(row.licence) if row else Licence.NONE

    def set_licence(self, actor: Actor, licence: Licence, now: datetime) -> None:
        T = SkydiverJumperLicence
        if licence is Licence.NONE:
            self._s.execute(delete(T).where(col(T.owner_person_id) == actor.person_id))
            return
        self._s.execute(
            pg_insert(T)
            .values(
                owner_person_id=actor.person_id, licence=licence.value, updated_at=now
            )
            .on_conflict_do_update(
                index_elements=["owner_person_id"],
                set_={"licence": licence.value, "updated_at": now},
            )
        )

    # exit weight ------------------------------------------------------------------

    def exit_weight(self, actor: Actor) -> ExitWeight:
        return usual_exit_weight(self._s, actor)

    def set_exit_weight(
        self, actor: Actor, grams: int | None, unit: WeightUnit | None, now: datetime
    ) -> None:
        P, W = SkydiverPerson, SkydiverExitWeight
        if unit is not None:  # the chosen unit outlives a cleared weight
            self._s.execute(
                update(P)
                .where(col(P.id) == actor.person_id)
                .values(weight_unit=unit.value)
            )
        if grams is None:
            # A deletion, so the erasure ledger records it (owner key only).
            self._s.execute(delete(W).where(col(W.owner_person_id) == actor.person_id))
            return
        assert unit is not None
        values = {"grams": grams, "unit": unit.value, "updated_at": now}
        self._s.execute(
            pg_insert(W)
            .values(owner_person_id=actor.person_id, **values)
            .on_conflict_do_update(index_elements=["owner_person_id"], set_=values)
        )

    def entry_facts(self, actor: Actor) -> list[EntryFacts]:
        mains = main_canopies(actor)
        rows = self._s.execute(
            select(
                col(J.jumped_on),
                col(J.jump_type),
                col(J.venue_id),
                col(J.place_id),
                col(J.aircraft),
                col(J.freefall_seconds),
                col(J.exit_altitude),
                col(J.altitude_unit),
                col(J.exit_weight_grams),
                mains.c.mains,
                mains.c.size,
            )
            .outerjoin(mains, mains.c.jump_id == col(J.id))
            .where(col(J.owner_person_id) == actor.person_id)
        )
        return [
            EntryFacts(
                jumped_on=on,
                jump_type=kind,
                venue_id=venue,
                place_id=place,
                aircraft=aircraft,
                freefall_seconds=freefall,
                exit_altitude=altitude,
                altitude_unit=unit,
                inputs=loading.Inputs(weight, int(mains or 0), size),
            )
            for (
                on, kind, venue, place, aircraft, freefall, altitude, unit,
                weight, mains, size,
            ) in rows.all()
        ]  # fmt: skip

    def entries(self, actor: Actor) -> list[EntryRow]:
        rows = self._s.execute(
            select(
                col(J.id),
                col(J.jumped_on),
                col(J.jump_number),
                col(J.exit_time),
                col(J.jump_type),
                col(J.freefall_seconds),
                col(J.venue_id),
                col(J.place_id),
            ).where(col(J.owner_person_id) == actor.person_id)
        )
        return [EntryRow(*row) for row in rows.all()]

    def freefall(self, actor: Actor) -> tuple[int, int, int]:
        """(seconds, entries with a freefall time, entries without one)."""
        seconds, with_time, total = self._s.execute(
            select(
                func.coalesce(func.sum(col(J.freefall_seconds)), 0),
                func.count(col(J.freefall_seconds)),
                func.count(),
            ).where(col(J.owner_person_id) == actor.person_id)
        ).one()
        return int(seconds), int(with_time), int(total) - int(with_time)

    def date_range(self, actor: Actor) -> tuple[date | None, date | None]:
        first, last = self._s.execute(
            select(func.min(col(J.jumped_on)), func.max(col(J.jumped_on))).where(
                col(J.owner_person_id) == actor.person_id
            )
        ).one()
        return first, last

    def per_day_since(self, actor: Actor, start: date) -> dict[date, int]:
        rows = self._s.execute(
            select(col(J.jumped_on), func.count())
            .where(col(J.owner_person_id) == actor.person_id)
            .where(col(J.jumped_on) >= start)
            .group_by(col(J.jumped_on))
        )
        return {on: int(n) for on, n in rows.all()}

    def by_type(self, actor: Actor) -> list[tuple[str, int]]:
        rows = self._s.execute(
            select(col(J.jump_type), func.count())
            .where(col(J.owner_person_id) == actor.person_id)
            .group_by(col(J.jump_type))
        )
        return [(kind, int(n)) for kind, n in rows.all()]

    def by_location(
        self, actor: Actor
    ) -> list[tuple[uuid.UUID | None, uuid.UUID | None, int]]:
        rows = self._s.execute(
            select(col(J.venue_id), col(J.place_id), func.count())
            .where(col(J.owner_person_id) == actor.person_id)
            .group_by(col(J.venue_id), col(J.place_id))
        )
        return [(v, p, int(n)) for v, p, n in rows.all()]

    def by_component(self, actor: Actor) -> list[tuple[ComponentRef, int, date]]:
        rows = self._s.execute(
            select(C, func.count(), func.max(col(J.jumped_on)))
            .join(L, col(L.component_id) == col(C.id))
            .join(J, col(J.id) == col(L.jump_id))
            .where(col(C.owner_person_id) == actor.person_id)
            .where(col(J.owner_person_id) == actor.person_id)
            .group_by(col(C.id))
        )
        return [
            (ComponentRef(c.id, c.kind, c.label, c.archived_at is not None), int(n), on)
            for c, n, on in rows.all()
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


def sql_history_store_factory(engine: Engine) -> StoreFactory:
    """Unit of work: commit on success, roll back on any exception."""

    @contextmanager
    def stores() -> Iterator[HistoryStore]:
        with Session(engine) as session:
            try:
                yield SqlHistoryStore(session)
            except BaseException:
                session.rollback()
                raise
            session.commit()

    return stores
