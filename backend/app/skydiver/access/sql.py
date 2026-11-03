"""Owner-scoped persistence convention for personal records (#146).

A personal-record table has `id` and `owner_person_id` (FK `skydiver_person.id`).
Reads and writes go through these helpers so the owner predicate is applied in SQL
together with the requested ID, never by filtering rows after loading them.
"""

import uuid
from typing import Any

from sqlalchemy import Select, select
from sqlmodel import Session, SQLModel, col

from app.skydiver.access.policy import Actor
from app.skydiver.identity.tables import SkydiverPerson


def _column(model: type[SQLModel], name: str) -> Any:
    column = getattr(model, name, None)
    if column is None:
        raise TypeError(f"{model.__name__} is not an owned table: no {name}")
    return col(column)


def owned[Row: SQLModel](model: type[Row], actor: Actor) -> Select[Row]:
    """`SELECT model WHERE owner = actor`. Extend it; never drop the predicate."""
    return select(model).where(_column(model, "owner_person_id") == actor.person_id)


def get_owned[Row: SQLModel](
    session: Session,
    model: type[Row],
    record_id: uuid.UUID,
    actor: Actor,
    *,
    for_update: bool = False,
) -> Row | None:
    """The actor's record with this ID, or None for foreign and absent alike."""
    query = owned(model, actor).where(_column(model, "id") == record_id)
    if for_update:
        query = query.with_for_update()
    return session.execute(query).scalars().first()


def lock_owner(session: Session, actor: Actor) -> None:
    """Serialize the actor's record mutations (quotas, restore) on their person row."""
    session.execute(
        select(col(SkydiverPerson.id))
        .where(col(SkydiverPerson.id) == actor.person_id)
        .with_for_update()
    ).one()
