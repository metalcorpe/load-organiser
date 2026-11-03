"""SQL adapter for private gear (#152). Every query is owner-scoped."""

import uuid
from collections.abc import Iterator
from contextlib import contextmanager
from datetime import date, datetime
from typing import Any

from sqlalchemy import Engine, delete, func, select, update
from sqlalchemy.exc import IntegrityError
from sqlmodel import Session, col

from app.skydiver.access.policy import Actor
from app.skydiver.access.sql import get_owned, owned
from app.skydiver.directory.policy import DirectoryRuleError as RuleError
from app.skydiver.directory.service import EditConflict
from app.skydiver.gear.policy import (
    AcquisitionMethod,
    ComponentKind,
    Relation,
    ServiceKind,
)
from app.skydiver.gear.service import (
    Component,
    GearEvent,
    GearStore,
    Membership,
    Rig,
    ServiceEntry,
    StoreFactory,
    fingerprint,
)
from app.skydiver.gear.tables import (
    SkydiverComponent,
    SkydiverGearEvent,
    SkydiverRig,
    SkydiverRigMembership,
    SkydiverServiceEntry,
)

_UNIQUE_VIOLATION = "23505"
_FOREIGN_KEY_VIOLATION = "23503"

C, R, M, S, E = (
    SkydiverComponent,
    SkydiverRig,
    SkydiverRigMembership,
    SkydiverServiceEntry,
    SkydiverGearEvent,
)


def _component(row: SkydiverComponent) -> Component:
    return Component(
        id=row.id,
        kind=ComponentKind(row.kind),
        label=row.label,
        manufacturer=row.manufacturer,
        model=row.model,
        serial=row.serial,
        serial_key=row.serial_key,
        manufactured=row.manufactured,
        relation=Relation(row.relation),
        acquisition_method=AcquisitionMethod(row.acquisition_method)
        if row.acquisition_method
        else None,
        acquired=row.acquired,
        notes=row.notes,
        archived_at=row.archived_at,
        version=row.version,
        updated_at=row.updated_at,
        fingerprint=row.fingerprint,
    )


def _service(row: SkydiverServiceEntry) -> ServiceEntry:
    return ServiceEntry(
        id=row.id,
        component_id=row.component_id,
        kind=ServiceKind(row.kind),
        done_on=row.done_on,
        due_on=row.due_on,
        performed_by=row.performed_by,
        notes=row.notes,
        created_at=row.created_at,
        fingerprint=row.fingerprint,
    )


class SqlGearStore:
    def __init__(self, session: Session) -> None:
        self._s = session

    def _insert(self, row: Any) -> uuid.UUID | None:
        """Insert in a savepoint; None if the owner's client key is already taken."""
        attempt = self._s.begin_nested()
        try:
            self._s.add(row)
            self._s.flush()
        except IntegrityError as error:
            attempt.rollback()
            # Only a concurrent same-key insert is a lost race; anything else is a bug.
            if getattr(error.orig, "sqlstate", None) != _UNIQUE_VIOLATION:
                raise
            return None
        attempt.commit()
        return row.id  # type: ignore[no-any-return]

    def _count(self, query: Any) -> int:
        return int(
            self._s.execute(
                select(func.count()).select_from(query.subquery())
            ).scalar_one()
        )

    def _cas(self, model: Any, actor: Actor, row_id: uuid.UUID, version: int) -> Any:
        return (
            update(model)
            .where(col(model.id) == row_id)
            .where(col(model.owner_person_id) == actor.person_id)
            .where(col(model.version) == version)
        )

    # components ---------------------------------------------------------------------

    def count_components(self, actor: Actor) -> int:
        return self._count(owned(C, actor))

    def component_by_key(self, actor: Actor, client_key: uuid.UUID) -> Component | None:
        row = (
            self._s.execute(owned(C, actor).where(col(C.client_key) == client_key))
            .scalars()
            .first()
        )
        return _component(row) if row else None

    def get_component(self, actor: Actor, component_id: uuid.UUID) -> Component | None:
        row = get_owned(self._s, C, component_id, actor)
        return _component(row) if row else None

    def list_components(self, actor: Actor, *, archived: bool) -> list[Component]:
        query = owned(C, actor).where(
            col(C.archived_at).is_not(None)
            if archived
            else col(C.archived_at).is_(None)
        )
        rows = self._s.execute(query.order_by(col(C.kind), col(C.label), col(C.id)))
        return [_component(row) for row in rows.scalars()]

    def insert_component(
        self, actor: Actor, client_key: uuid.UUID, values: dict[str, Any], now: datetime
    ) -> uuid.UUID | None:
        row = C(
            owner_person_id=actor.person_id,
            client_key=client_key,
            created_at=now,
            updated_at=now,
            **values,
        )
        return self._insert(row)

    def update_component(
        self,
        actor: Actor,
        component_id: uuid.UUID,
        values: dict[str, Any],
        now: datetime,
        *,
        expected_version: int,
    ) -> None:
        result = self._s.execute(
            self._cas(C, actor, component_id, expected_version).values(
                **values, version=expected_version + 1, updated_at=now
            )
        )
        if result.rowcount != 1:  # type: ignore[attr-defined]
            raise EditConflict()

    def delete_component(
        self, actor: Actor, component_id: uuid.UUID, *, expected_version: int
    ) -> None:
        try:
            result = self._s.execute(
                delete(C)
                .where(col(C.id) == component_id)
                .where(col(C.owner_person_id) == actor.person_id)
                .where(col(C.version) == expected_version)
            )
        except IntegrityError as error:
            # A jump records it as used (#153): archive it instead.
            if getattr(error.orig, "sqlstate", None) == _FOREIGN_KEY_VIOLATION:
                raise RuleError("component_in_use") from None
            raise
        if result.rowcount != 1:  # type: ignore[attr-defined]
            raise EditConflict()

    def same_serial(
        self, actor: Actor, serial_key: str, exclude: uuid.UUID
    ) -> list[uuid.UUID]:
        # Owner-scoped by construction: other accounts' gear is never consulted.
        rows = self._s.execute(
            select(col(C.id))
            .where(col(C.owner_person_id) == actor.person_id)
            .where(col(C.serial_key) == serial_key)
            .where(col(C.id) != exclude)
        ).scalars()
        return list(rows)

    # rigs ---------------------------------------------------------------------------

    def count_rigs(self, actor: Actor) -> int:
        return self._count(owned(R, actor))

    def rig_by_key(self, actor: Actor, client_key: uuid.UUID) -> Rig | None:
        row = (
            self._s.execute(owned(R, actor).where(col(R.client_key) == client_key))
            .scalars()
            .first()
        )
        return _rig_with(row) if row else None

    def get_rig(self, actor: Actor, rig_id: uuid.UUID) -> Rig | None:
        row = get_owned(self._s, R, rig_id, actor)
        return _rig_with(row) if row else None

    def list_rigs(self, actor: Actor) -> list[Rig]:
        rows = self._s.execute(
            owned(R, actor).order_by(
                col(R.archived_at).is_not(None), col(R.label), col(R.id)
            )
        ).scalars()
        return [_rig_with(row) for row in rows]

    def insert_rig(
        self, actor: Actor, client_key: uuid.UUID, values: dict[str, Any], now: datetime
    ) -> uuid.UUID | None:
        values = dict(values)
        values.pop("fingerprint", None)  # a rig's content is its label
        row = R(
            owner_person_id=actor.person_id,
            client_key=client_key,
            created_at=now,
            updated_at=now,
            **values,
        )
        return self._insert(row)

    def update_rig(
        self,
        actor: Actor,
        rig_id: uuid.UUID,
        values: dict[str, Any],
        now: datetime,
        *,
        expected_version: int,
    ) -> None:
        result = self._s.execute(
            self._cas(R, actor, rig_id, expected_version).values(
                **values, version=expected_version + 1, updated_at=now
            )
        )
        if result.rowcount != 1:  # type: ignore[attr-defined]
            raise EditConflict()

    # memberships -----------------------------------------------------------------------

    def memberships(
        self, actor: Actor, *, component_id: uuid.UUID | None = None
    ) -> list[Membership]:
        query = (
            select(M, col(R.label))
            .join(R, col(R.id) == col(M.rig_id))
            .where(col(M.owner_person_id) == actor.person_id)
        )
        if component_id is not None:
            query = query.where(col(M.component_id) == component_id)
        rows = self._s.execute(query.order_by(col(M.from_on).desc(), col(M.id).desc()))
        return [
            Membership(
                id=m.id,
                rig_id=m.rig_id,
                rig_label=label,
                component_id=m.component_id,
                from_on=m.from_on,
                until_on=m.until_on,
            )
            for m, label in rows.all()
        ]

    def close_membership(
        self, actor: Actor, membership_id: uuid.UUID, on: date
    ) -> None:
        self._s.execute(
            update(M)
            .where(col(M.id) == membership_id)
            .where(col(M.owner_person_id) == actor.person_id)
            .values(until_on=on)
        )

    def open_membership(
        self, actor: Actor, rig_id: uuid.UUID, component_id: uuid.UUID, on: date
    ) -> None:
        self._s.add(
            M(
                owner_person_id=actor.person_id,
                rig_id=rig_id,
                component_id=component_id,
                from_on=on,
            )
        )
        self._s.flush()

    # service ------------------------------------------------------------------------

    def count_service(self, actor: Actor, component_id: uuid.UUID) -> int:
        return self._count(owned(S, actor).where(col(S.component_id) == component_id))

    def service_by_key(
        self, actor: Actor, client_key: uuid.UUID
    ) -> ServiceEntry | None:
        row = (
            self._s.execute(owned(S, actor).where(col(S.client_key) == client_key))
            .scalars()
            .first()
        )
        return _service(row) if row else None

    def list_service(
        self, actor: Actor, component_ids: list[uuid.UUID]
    ) -> list[ServiceEntry]:
        if not component_ids:
            return []
        rows = self._s.execute(
            owned(S, actor)
            .where(col(S.component_id).in_(component_ids))
            .order_by(col(S.done_on).desc(), col(S.id).desc())
        ).scalars()
        return [_service(row) for row in rows]

    def insert_service(
        self, actor: Actor, client_key: uuid.UUID, values: dict[str, Any], now: datetime
    ) -> uuid.UUID | None:
        row = S(
            owner_person_id=actor.person_id,
            client_key=client_key,
            created_at=now,
            **values,
        )
        return self._insert(row)

    def delete_service(
        self, actor: Actor, component_id: uuid.UUID, entry_id: uuid.UUID
    ) -> bool:
        result = self._s.execute(
            delete(S)
            .where(col(S.id) == entry_id)
            .where(col(S.component_id) == component_id)
            .where(col(S.owner_person_id) == actor.person_id)
        )
        return bool(result.rowcount)  # type: ignore[attr-defined]

    # history ------------------------------------------------------------------------

    def record(
        self,
        actor: Actor,
        component_id: uuid.UUID,
        kind: str,
        detail: dict[str, Any],
        now: datetime,
    ) -> None:
        self._s.add(
            E(
                owner_person_id=actor.person_id,
                component_id=component_id,
                kind=kind,
                detail=detail,
                created_at=now,
            )
        )
        self._s.flush()

    def events(self, actor: Actor, component_id: uuid.UUID) -> list[GearEvent]:
        rows = self._s.execute(
            owned(E, actor)
            .where(col(E.component_id) == component_id)
            .order_by(col(E.id))
        ).scalars()
        return [GearEvent(r.kind, dict(r.detail), r.created_at) for r in rows]


def _rig_with(row: SkydiverRig) -> Rig:
    # A rig's create content is its label; a retry with the same key and label
    # returns the original.
    return Rig(
        id=row.id,
        label=row.label,
        archived_at=row.archived_at,
        version=row.version,
        fingerprint=fingerprint({"label": row.label}),
    )


def sql_gear_store_factory(engine: Engine) -> StoreFactory:
    """Unit of work: commit on success, roll back on any exception."""

    @contextmanager
    def stores() -> Iterator[GearStore]:
        with Session(engine) as session:
            try:
                yield SqlGearStore(session)
            except BaseException:
                session.rollback()
                raise
            session.commit()

    return stores
