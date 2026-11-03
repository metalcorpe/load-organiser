"""SQL adapter for saved opportunities and visit plans (#150).

Every query goes through the owner-scoped helpers in `app.skydiver.access.sql`.
"""

import uuid
from collections.abc import Iterator
from contextlib import contextmanager
from datetime import datetime
from typing import Any

from sqlalchemy import Engine, delete, func, select, update
from sqlmodel import Session, col

from app.skydiver.access.policy import Actor
from app.skydiver.access.sql import get_owned, lock_owner, owned
from app.skydiver.directory.tables import SkydiverProvisionalPlace
from app.skydiver.saves.service import PlanRow, SavedRow, SavesStore, StoreFactory
from app.skydiver.saves.tables import SkydiverSavedOpportunity, SkydiverVisitPlan


class SqlSavesStore:
    def __init__(self, session: Session) -> None:
        self._s = session

    def lock_owner(self, actor: Actor) -> None:
        lock_owner(self._s, actor)

    # saved ---------------------------------------------------------------------

    def list_saved(self, actor: Actor) -> list[SavedRow]:
        rows = self._s.execute(
            owned(SkydiverSavedOpportunity, actor).order_by(
                col(SkydiverSavedOpportunity.created_at).desc(),
                col(SkydiverSavedOpportunity.id).desc(),
            )
        ).scalars()
        return [_saved(row) for row in rows]

    def get_saved(self, actor: Actor, opportunity_id: uuid.UUID) -> SavedRow | None:
        row = (
            self._s.execute(
                owned(SkydiverSavedOpportunity, actor).where(
                    col(SkydiverSavedOpportunity.opportunity_id) == opportunity_id
                )
            )
            .scalars()
            .first()
        )
        return _saved(row) if row else None

    def count_saved(self, actor: Actor) -> int:
        return _count(self._s, owned(SkydiverSavedOpportunity, actor))

    def insert_saved(
        self, actor: Actor, opportunity_id: uuid.UUID, title: str, now: datetime
    ) -> None:
        self._s.add(
            SkydiverSavedOpportunity(
                owner_person_id=actor.person_id,
                opportunity_id=opportunity_id,
                title=title,
                created_at=now,
            )
        )
        self._s.flush()

    def delete_saved(self, actor: Actor, opportunity_id: uuid.UUID) -> None:
        self._s.execute(
            delete(SkydiverSavedOpportunity).where(
                col(SkydiverSavedOpportunity.owner_person_id) == actor.person_id,
                col(SkydiverSavedOpportunity.opportunity_id) == opportunity_id,
            )
        )

    # plans ---------------------------------------------------------------------

    def owns_place(self, actor: Actor, place_id: uuid.UUID) -> bool:
        return get_owned(self._s, SkydiverProvisionalPlace, place_id, actor) is not None

    def list_plans(self, actor: Actor) -> list[PlanRow]:
        rows = self._s.execute(
            owned(SkydiverVisitPlan, actor).order_by(
                col(SkydiverVisitPlan.starts_on), col(SkydiverVisitPlan.id)
            )
        ).scalars()
        return [_plan(row) for row in rows]

    def get_plan(
        self, actor: Actor, plan_id: uuid.UUID, *, lock: bool = False
    ) -> PlanRow | None:
        row = get_owned(self._s, SkydiverVisitPlan, plan_id, actor, for_update=lock)
        return _plan(row) if row else None

    def count_plans(self, actor: Actor) -> int:
        return _count(self._s, owned(SkydiverVisitPlan, actor))

    def insert_plan(
        self, actor: Actor, values: dict[str, Any], now: datetime
    ) -> uuid.UUID:
        row = SkydiverVisitPlan(
            owner_person_id=actor.person_id, created_at=now, updated_at=now, **values
        )
        self._s.add(row)
        self._s.flush()
        return row.id

    def update_plan(
        self, actor: Actor, plan_id: uuid.UUID, values: dict[str, Any], now: datetime
    ) -> None:
        self._s.execute(
            update(SkydiverVisitPlan)
            .where(
                col(SkydiverVisitPlan.id) == plan_id,
                col(SkydiverVisitPlan.owner_person_id) == actor.person_id,
            )
            .values(**values, updated_at=now)
        )

    def delete_plan(self, actor: Actor, plan_id: uuid.UUID) -> None:
        self._s.execute(
            delete(SkydiverVisitPlan).where(
                col(SkydiverVisitPlan.id) == plan_id,
                col(SkydiverVisitPlan.owner_person_id) == actor.person_id,
            )
        )


def _count(session: Session, query: Any) -> int:
    return int(
        session.execute(select(func.count()).select_from(query.subquery())).scalar_one()
    )


def _saved(row: SkydiverSavedOpportunity) -> SavedRow:
    return SavedRow(
        opportunity_id=row.opportunity_id, title=row.title, saved_at=row.created_at
    )


def _plan(row: SkydiverVisitPlan) -> PlanRow:
    return PlanRow(
        id=row.id,
        title=row.title,
        starts_on=row.starts_on,
        ends_on=row.ends_on,
        note=row.note,
        opportunity_id=row.opportunity_id,
        venue_id=row.venue_id,
        place_id=row.place_id,
        updated_at=row.updated_at,
    )


def sql_saves_store_factory(engine: Engine) -> StoreFactory:
    """Unit of work: commit on success, roll back on any exception."""

    @contextmanager
    def stores() -> Iterator[SavesStore]:
        with Session(engine) as session:
            try:
                yield SqlSavesStore(session)
            except BaseException:
                session.rollback()
                raise
            session.commit()

    return stores
