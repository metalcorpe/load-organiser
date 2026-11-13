"""Owner-scoped personal jump tables (#153). Adapters only.

Every table carries `owner_person_id` and is read and written only through
`app.skydiver.access.sql`. This is not the prototype's operational load/jump
model and nothing here is public, shared or verified.
"""

import uuid
from datetime import date, datetime, time

from sqlalchemy import (
    CheckConstraint,
    Column,
    Date,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    Time,
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.types import JSON
from sqlmodel import Field, SQLModel

_JSON = JSONB().with_variant(JSON(), "sqlite")


def _instant() -> Column:  # type: ignore[type-arg]
    return Column(DateTime(timezone=True), nullable=False)


def _owner() -> Column:  # type: ignore[type-arg]
    return Column(
        ForeignKey("skydiver_person.id", ondelete="CASCADE"), nullable=False, index=True
    )


class SkydiverJumpImport(SQLModel, table=True):
    """One spreadsheet import of the owner's own logbook, and whether it was undone.

    The unique (owner, fingerprint) pair makes a repeated import answer "already
    imported"; the unique (owner, sequence) pair lets only one of two simultaneous
    imports commit, so together they cannot pass the jump limit (compare-and-swap).
    """

    __tablename__ = "skydiver_jump_import"
    __table_args__ = (
        UniqueConstraint(
            "owner_person_id", "fingerprint", name="uq_skydiver_jump_import"
        ),
        UniqueConstraint(
            "owner_person_id", "sequence", name="uq_skydiver_jump_import_sequence"
        ),
    )

    id: uuid.UUID = Field(default_factory=uuid.uuid7, primary_key=True)
    owner_person_id: uuid.UUID = Field(sa_column=_owner())
    fingerprint: str = Field(sa_column=Column(String(64), nullable=False))
    sequence: int = Field(sa_column=Column(Integer, nullable=False))
    counts: dict = Field(  # type: ignore[type-arg]
        default_factory=dict, sa_column=Column(_JSON, nullable=False)
    )
    # Private places this import created; undo removes those no longer used.
    place_ids: list = Field(  # type: ignore[type-arg]
        default_factory=list, sa_column=Column(_JSON, nullable=False)
    )
    created_at: datetime = Field(sa_column=_instant())
    undone_at: datetime | None = Field(
        default=None, sa_column=Column(DateTime(timezone=True), nullable=True)
    )


class SkydiverJump(SQLModel, table=True):
    """One completed jump as the jumper records it. Activity date is a DATE."""

    __tablename__ = "skydiver_jump"
    __table_args__ = (
        CheckConstraint(
            "(CASE WHEN venue_id IS NULL THEN 0 ELSE 1 END"
            " + CASE WHEN place_id IS NULL THEN 0 ELSE 1 END) = 1",
            name="ck_skydiver_jump_one_location",
        ),
        CheckConstraint(
            "jump_type IN ('unspecified', 'belly', 'freefly', 'angle', 'wingsuit',"
            " 'canopy', 'crw', 'accuracy', 'hop_and_pop', 'tandem', 'training',"
            " 'other')",
            name="ck_skydiver_jump_type",
        ),
        CheckConstraint(
            "jump_number IS NULL OR jump_number > 0", name="ck_skydiver_jump_number"
        ),
        CheckConstraint(
            "(exit_time IS NULL) = (time_zone IS NULL)",
            name="ck_skydiver_jump_time_zone",
        ),
        CheckConstraint(
            "altitude_unit IS NULL OR altitude_unit IN ('ft', 'm')",
            name="ck_skydiver_jump_altitude_unit",
        ),
        CheckConstraint(
            "(exit_altitude IS NULL AND deployment_altitude IS NULL)"
            " = (altitude_unit IS NULL)",
            name="ck_skydiver_jump_altitude_has_unit",
        ),
        CheckConstraint(
            "altitude_datum IN ('unspecified', 'agl', 'msl')",
            name="ck_skydiver_jump_altitude_datum",
        ),
        CheckConstraint(
            "freefall_seconds IS NULL OR freefall_seconds >= 0",
            name="ck_skydiver_jump_freefall",
        ),
        CheckConstraint(
            "source IN ('manual', 'restored', 'imported')",
            name="ck_skydiver_jump_source",
        ),
        CheckConstraint(
            "exit_weight_grams IS NULL OR exit_weight_grams BETWEEN 30000 AND 250000",
            name="ck_skydiver_jump_exit_weight",
        ),
        Index("ix_skydiver_jump_owner_date", "owner_person_id", "jumped_on", "id"),
        Index("ix_skydiver_jump_owner_number", "owner_person_id", "jump_number"),
    )

    id: uuid.UUID = Field(default_factory=uuid.uuid7, primary_key=True)
    owner_person_id: uuid.UUID = Field(sa_column=_owner())
    jumped_on: date = Field(sa_column=Column(Date, nullable=False))
    # A listed venue (read through merge redirects) or the owner's private place.
    # Deleting a referenced place is refused; the jump keeps its location.
    venue_id: uuid.UUID | None = Field(
        default=None,
        sa_column=Column(ForeignKey("skydiver_venue.id"), nullable=True, index=True),
    )
    place_id: uuid.UUID | None = Field(
        default=None,
        sa_column=Column(
            ForeignKey("skydiver_provisional_place.id"), nullable=True, index=True
        ),
    )
    jump_type: str = Field(max_length=16)
    jump_number: int | None = Field(default=None, sa_column=Column(Integer))
    exit_time: time | None = Field(default=None, sa_column=Column(Time, nullable=True))
    time_zone: str | None = Field(default=None, max_length=64)
    exit_altitude: int | None = Field(default=None, sa_column=Column(Integer))
    deployment_altitude: int | None = Field(default=None, sa_column=Column(Integer))
    altitude_unit: str | None = Field(default=None, max_length=2)
    altitude_datum: str = Field(default="unspecified", max_length=12)
    freefall_seconds: int | None = Field(default=None, sa_column=Column(Integer))
    other_gear: str | None = Field(default=None, max_length=200)
    # Free text as the jumper writes it, e.g. "Cessna 208 SX-ABC". Private.
    aircraft: str | None = Field(default=None, max_length=60)
    # The exit weight on this jump (body and gear) in grams, when it differs from
    # the jumper's usual one; for wing loading. Private.
    exit_weight_grams: int | None = Field(
        default=None, sa_column=Column(Integer, nullable=True)
    )
    notes: str | None = Field(default=None, sa_column=Column(Text, nullable=True))
    links: list = Field(  # type: ignore[type-arg]
        default_factory=list, sa_column=Column(_JSON, nullable=False)
    )
    source: str = Field(default="manual", max_length=16)
    # The spreadsheet import that created this jump; kept while the jump exists.
    import_id: uuid.UUID | None = Field(
        default=None,
        sa_column=Column(
            ForeignKey("skydiver_jump_import.id", ondelete="SET NULL"),
            nullable=True,
            index=True,
        ),
    )
    version: int = Field(
        default=1, sa_column=Column(Integer, nullable=False, server_default="1")
    )
    created_at: datetime = Field(sa_column=_instant())
    updated_at: datetime = Field(sa_column=_instant())


class SkydiverJumpComponent(SQLModel, table=True):
    """Equipment actually used on a jump. A used component cannot be deleted."""

    __tablename__ = "skydiver_jump_component"
    __table_args__ = (Index("ix_skydiver_jump_component_component", "component_id"),)

    jump_id: uuid.UUID = Field(
        sa_column=Column(
            ForeignKey("skydiver_jump.id", ondelete="CASCADE"), primary_key=True
        )
    )
    component_id: uuid.UUID = Field(
        sa_column=Column(ForeignKey("skydiver_component.id"), primary_key=True)
    )
    owner_person_id: uuid.UUID = Field(sa_column=_owner())


class SkydiverJumpReceipt(SQLModel, table=True):
    """Create receipt: a retried submission returns its jump, or that it was deleted."""

    __tablename__ = "skydiver_jump_receipt"
    __table_args__ = (
        UniqueConstraint(
            "owner_person_id", "client_key", name="uq_skydiver_jump_receipt_key"
        ),
    )

    id: uuid.UUID = Field(default_factory=uuid.uuid7, primary_key=True)
    owner_person_id: uuid.UUID = Field(sa_column=_owner())
    client_key: uuid.UUID
    fingerprint: str = Field(max_length=64)
    # Cleared when the jump is deleted, so a replay cannot resurrect it.
    jump_id: uuid.UUID | None = Field(
        default=None,
        sa_column=Column(
            ForeignKey("skydiver_jump.id", ondelete="SET NULL"), nullable=True
        ),
    )
    created_at: datetime = Field(sa_column=_instant())


class SkydiverJumpEvent(SQLModel, table=True):
    """Owner-only source and correction history. Keeps earlier facts, not old notes."""

    __tablename__ = "skydiver_jump_event"
    __table_args__ = (Index("ix_skydiver_jump_event_jump", "jump_id", "id"),)

    id: uuid.UUID = Field(default_factory=uuid.uuid7, primary_key=True)
    owner_person_id: uuid.UUID = Field(sa_column=_owner())
    jump_id: uuid.UUID = Field(
        sa_column=Column(
            ForeignKey("skydiver_jump.id", ondelete="CASCADE"), nullable=False
        )
    )
    kind: str = Field(sa_column=Column(String(32), nullable=False))
    detail: dict = Field(  # type: ignore[type-arg]
        default_factory=dict, sa_column=Column(_JSON, nullable=False)
    )
    created_at: datetime = Field(sa_column=_instant())
