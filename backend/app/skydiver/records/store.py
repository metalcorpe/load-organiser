"""SQL adapter for personal export/restore (#155). Every query is owner-scoped."""

import uuid
from collections.abc import Iterator
from contextlib import contextmanager
from datetime import UTC, date, datetime
from typing import Any

from sqlalchemy import Engine, func, insert, select
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.exc import IntegrityError
from sqlmodel import Session, SQLModel, col

from app.skydiver.access.policy import Actor
from app.skydiver.access.sql import owned
from app.skydiver.directory.tables import SkydiverProvisionalPlace, SkydiverVenue
from app.skydiver.gear.tables import (
    SkydiverComponent,
    SkydiverGearEvent,
    SkydiverRig,
    SkydiverRigMembership,
    SkydiverServiceEntry,
)
from app.skydiver.history.tables import (
    SkydiverJumpBaseline,
    SkydiverJumpBaselineEvent,
    SkydiverJumperLicence,
)
from app.skydiver.logbook.tables import (
    SkydiverJump,
    SkydiverJumpComponent,
    SkydiverJumpEvent,
)
from app.skydiver.opportunities.tables import SkydiverOpportunity
from app.skydiver.records import format as v1
from app.skydiver.records.policy import ArchiveInvalid
from app.skydiver.records.service import (
    Receipt,
    RecordsStore,
    SheetJump,
    StoreFactory,
)
from app.skydiver.records.tables import SkydiverRestoreReceipt
from app.skydiver.saves.tables import SkydiverSavedOpportunity, SkydiverVisitPlan

# Collections a restore manages; any row here makes the records non-empty.
# History/provenance rows and create receipts are not records on their own.
MANAGED: dict[str, type[SQLModel]] = {
    "places": SkydiverProvisionalPlace,
    "components": SkydiverComponent,
    "rigs": SkydiverRig,
    "jumps": SkydiverJump,
    "baseline": SkydiverJumpBaseline,
    "saved_listings": SkydiverSavedOpportunity,
    "plans": SkydiverVisitPlan,
}

TABLES: dict[str, type[SQLModel]] = {
    **MANAGED,
    "rig_stints": SkydiverRigMembership,
    "service_entries": SkydiverServiceEntry,
    "gear_events": SkydiverGearEvent,
    "jump_components": SkydiverJumpComponent,
    "jump_events": SkydiverJumpEvent,
    "baseline_events": SkydiverJumpBaselineEvent,
    # A setting, not a record: restored only where none is set (see insert_rows).
    "licence": SkydiverJumperLicence,
}


def _utc(value: Any) -> Any:
    """Instants leave in UTC whatever the database session's time zone is."""
    return value.astimezone(UTC) if isinstance(value, datetime) else value


class SqlRecordsStore:
    def __init__(self, session: Session) -> None:
        self._s = session

    def snapshot(self) -> None:
        # Must precede every query in the transaction: one consistent export.
        self._s.connection(execution_options={"isolation_level": "REPEATABLE READ"})

    def _rows[T: SQLModel](self, model: type[T], actor: Actor, *order: Any) -> list[T]:
        return list(self._s.execute(owned(model, actor).order_by(*order)).scalars())

    # export -------------------------------------------------------------------------

    def export_records(self, actor: Actor) -> v1.RecordsV1:
        P, C, R = SkydiverProvisionalPlace, SkydiverComponent, SkydiverRig
        M, S, GE = SkydiverRigMembership, SkydiverServiceEntry, SkydiverGearEvent
        J, JC, JE = SkydiverJump, SkydiverJumpComponent, SkydiverJumpEvent
        B, BE = SkydiverJumpBaseline, SkydiverJumpBaselineEvent
        SO, VP = SkydiverSavedOpportunity, SkydiverVisitPlan

        def pick(row: SQLModel, *names: str) -> dict[str, Any]:
            return {name: _utc(getattr(row, name)) for name in names}

        used: dict[uuid.UUID, list[uuid.UUID]] = {}
        for link in self._rows(JC, actor, col(JC.jump_id), col(JC.component_id)):
            used.setdefault(link.jump_id, []).append(link.component_id)
        baseline = self._s.execute(owned(B, actor)).scalars().first()
        licence = self._s.execute(owned(SkydiverJumperLicence, actor)).scalars().first()
        stamps = ("created_at", "updated_at")
        event = ("kind", "created_at")
        records = {
            "places": [
                pick(p, "id", "name", "country", "venue_id", *stamps)
                for p in self._rows(P, actor, col(P.created_at), col(P.id))
            ],
            "components": [
                pick(
                    c,
                    "id",
                    "kind",
                    "label",
                    "manufacturer",
                    "model",
                    "serial",
                    "manufactured",
                    "relation",
                    "acquisition_method",
                    "acquired",
                    "notes",
                    "repack_interval_days",
                    "end_of_life_on",
                    "archived_at",
                    *stamps,
                )  # fmt: skip
                for c in self._rows(C, actor, col(C.id))
            ],
            "rigs": [
                pick(g, "id", "label", "archived_at", *stamps)
                for g in self._rows(R, actor, col(R.id))
            ],
            "rig_stints": [
                pick(m, "rig_id", "component_id", "from_on", "until_on")
                for m in self._rows(M, actor, col(M.component_id), col(M.from_on))
            ],
            "service_entries": [
                pick(
                    s,
                    "id",
                    "component_id",
                    "kind",
                    "done_on",
                    "due_on",
                    "performed_by",
                    "notes",
                    "created_at",
                )  # fmt: skip
                for s in self._rows(S, actor, col(S.id))
            ],
            "gear_events": [
                pick(e, "component_id", *event) | {"detail": dict(e.detail)}
                for e in self._rows(GE, actor, col(GE.id))
            ],
            "jumps": [
                pick(
                    j,
                    "id",
                    "jumped_on",
                    "venue_id",
                    "place_id",
                    "jump_type",
                    "jump_number",
                    "exit_time",
                    "time_zone",
                    "exit_altitude",
                    "deployment_altitude",
                    "altitude_unit",
                    "altitude_datum",
                    "freefall_seconds",
                    "other_gear",
                    "aircraft",
                    "notes",
                    "source",
                    *stamps,
                )  # fmt: skip
                | {"links": list(j.links or []), "component_ids": used.get(j.id, [])}
                for j in self._rows(J, actor, col(J.jumped_on), col(J.id))
            ],
            "jump_events": [
                pick(e, "jump_id", *event) | {"detail": dict(e.detail)}
                for e in self._rows(JE, actor, col(JE.id))
            ],
            "baseline": pick(baseline, "prior_jumps", "before_on", "source", *stamps)
            if baseline
            else None,
            "baseline_events": [
                pick(e, *event) | {"detail": dict(e.detail)}
                for e in self._rows(BE, actor, col(BE.id))
            ],
            "saved_listings": [
                pick(s, "opportunity_id", "title", "created_at")
                for s in self._rows(SO, actor, col(SO.created_at), col(SO.id))
            ],
            "plans": [
                pick(
                    p,
                    "title",
                    "starts_on",
                    "ends_on",
                    "note",
                    "opportunity_id",
                    "venue_id",
                    "place_id",
                    *stamps,
                )  # fmt: skip
                for p in self._rows(VP, actor, col(VP.starts_on), col(VP.id))
            ],
            "licence": licence.licence if licence else None,
        }
        return v1.RecordsV1.model_validate(records)

    def sheet_jumps(
        self, actor: Actor, from_on: date | None, until_on: date | None
    ) -> list[SheetJump]:
        J, JC, C = SkydiverJump, SkydiverJumpComponent, SkydiverComponent
        query = owned(J, actor)
        if from_on is not None:
            query = query.where(col(J.jumped_on) >= from_on)
        if until_on is not None:
            query = query.where(col(J.jumped_on) <= until_on)
        jumps = list(
            self._s.execute(query.order_by(col(J.jumped_on), col(J.id))).scalars()
        )
        labels: dict[uuid.UUID, list[str]] = {}
        if jumps:
            used = self._s.execute(
                select(col(JC.jump_id), col(C.label))
                .join(C, col(C.id) == col(JC.component_id))
                .where(col(JC.owner_person_id) == actor.person_id)
                .where(col(JC.jump_id).in_([j.id for j in jumps]))
                .order_by(col(JC.jump_id), col(C.label), col(C.id))
            )
            for jump_id, label in used.all():
                labels.setdefault(jump_id, []).append(label)
        return [
            SheetJump(
                jumped_on=j.jumped_on,
                venue_id=j.venue_id,
                place_id=j.place_id,
                jump_type=j.jump_type,
                jump_number=j.jump_number,
                aircraft=j.aircraft,
                exit_altitude=j.exit_altitude,
                deployment_altitude=j.deployment_altitude,
                altitude_unit=j.altitude_unit,
                freefall_seconds=j.freefall_seconds,
                notes=j.notes,
                other_gear=j.other_gear,
                gear=labels.get(j.id, []),
            )
            for j in jumps
        ]

    def place_names(self, actor: Actor) -> dict[uuid.UUID, tuple[str, str]]:
        P = SkydiverProvisionalPlace
        rows = self._s.execute(owned(P, actor)).scalars()
        return {p.id: (p.name, p.country) for p in rows}

    def venue_refs(self, venue_ids: list[uuid.UUID]) -> list[v1.VenueRefV1]:
        """Name and country of public venues as stored; public data, no owner."""
        if not venue_ids:
            return []
        V = SkydiverVenue
        rows = self._s.execute(
            select(col(V.id), col(V.name), col(V.country))
            .where(col(V.id).in_(venue_ids))
            .order_by(col(V.id))
        )
        return [v1.VenueRefV1(id=i, name=n, country=c) for i, n, c in rows.all()]

    def listing_refs(self, listing_ids: list[uuid.UUID]) -> list[v1.ListingRefV1]:
        if not listing_ids:
            return []
        O = SkydiverOpportunity  # noqa: E741
        rows = self._s.execute(
            select(col(O.id), col(O.title))
            .where(col(O.id).in_(listing_ids))
            .order_by(col(O.id))
        )
        return [v1.ListingRefV1(id=i, title=t) for i, t in rows.all()]

    # restore ------------------------------------------------------------------------

    def managed_counts(self, actor: Actor) -> dict[str, int]:
        return {
            name: int(
                self._s.execute(
                    select(func.count())
                    .select_from(model)
                    .where(col(getattr(model, "owner_person_id")) == actor.person_id)  # noqa: B009
                ).scalar_one()
            )
            for name, model in MANAGED.items()
        }

    def receipt(self, actor: Actor, fingerprint: str) -> Receipt | None:
        T = SkydiverRestoreReceipt
        row = (
            self._s.execute(owned(T, actor).where(col(T.fingerprint) == fingerprint))
            .scalars()
            .first()
        )
        return (
            Receipt(row.fingerprint, dict(row.counts), _utc(row.created_at))
            if row
            else None
        )

    def latest_receipt(self, actor: Actor) -> Receipt | None:
        T = SkydiverRestoreReceipt
        row = (
            self._s.execute(owned(T, actor).order_by(col(T.id).desc()).limit(1))
            .scalars()
            .first()
        )
        return (
            Receipt(row.fingerprint, dict(row.counts), _utc(row.created_at))
            if row
            else None
        )

    def insert_rows(self, table: str, rows: list[dict[str, Any]]) -> None:
        if not rows:
            return
        if table == "licence":
            # The account's own current setting wins over the archive's.
            self._s.execute(
                pg_insert(SkydiverJumperLicence).values(rows).on_conflict_do_nothing()
            )
            return
        try:
            self._s.execute(insert(TABLES[table]), rows)
        except IntegrityError:
            # A rule the archive check did not catch; the whole restore rolls back.
            raise ArchiveInvalid(f"{table}.constraint") from None

    def next_receipt_sequence(self, actor: Actor) -> int:
        T = SkydiverRestoreReceipt
        latest = self._s.execute(
            select(func.max(col(T.sequence))).where(
                col(T.owner_person_id) == actor.person_id
            )
        ).scalar_one()
        return int(latest or 0) + 1

    def insert_receipt(
        self, actor: Actor, receipt: Receipt, version: int, sequence: int
    ) -> bool:
        """False when a concurrent restore already took this file or this sequence."""
        T = SkydiverRestoreReceipt
        result = self._s.execute(
            pg_insert(T)
            .values(
                id=uuid.uuid7(),
                owner_person_id=actor.person_id,
                fingerprint=receipt.fingerprint,
                sequence=sequence,
                format_version=version,
                counts=receipt.counts,
                created_at=receipt.restored_at,
            )
            .on_conflict_do_nothing()
            .returning(col(T.id))
        )
        return result.first() is not None


def sql_records_store_factory(engine: Engine) -> StoreFactory:
    """Unit of work: commit on success, roll back on any exception."""

    @contextmanager
    def stores() -> Iterator[RecordsStore]:
        with Session(engine) as session:
            try:
                yield SqlRecordsStore(session)
            except BaseException:
                session.rollback()
                raise
            session.commit()

    return stores
