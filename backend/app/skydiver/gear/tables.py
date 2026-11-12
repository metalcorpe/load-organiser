"""Owner-scoped gear tables (#152). Adapters only; policy never imports this module.

Every table carries `owner_person_id` and is read and written only through
`app.skydiver.access.sql`. Nothing here is public, shared or verified.
"""

import uuid
from datetime import date, datetime

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
    UniqueConstraint,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.types import JSON
from sqlmodel import Field, SQLModel


def _instant() -> Column:  # type: ignore[type-arg]
    return Column(DateTime(timezone=True), nullable=False)


def _owner() -> Column:  # type: ignore[type-arg]
    return Column(
        ForeignKey("skydiver_person.id", ondelete="CASCADE"), nullable=False, index=True
    )


def _version() -> Column:  # type: ignore[type-arg]
    return Column(Integer, nullable=False, server_default="1")


# Portable shape check (YYYY, YYYY-MM or YYYY-MM-DD); policy validates the format.
_PARTIAL = "IS NULL OR length({0}) IN (4, 7, 10)"


class SkydiverComponent(SQLModel, table=True):
    """One physical item (container, main, reserve, AAD, other) as the owner declares it."""

    __tablename__ = "skydiver_component"
    __table_args__ = (
        CheckConstraint(
            "kind IN ('container', 'main', 'reserve', 'aad', 'other')",
            name="ck_skydiver_component_kind",
        ),
        CheckConstraint(
            "relation IN ('owned', 'borrowed', 'rented')",
            name="ck_skydiver_component_relation",
        ),
        CheckConstraint(
            "acquisition_method IS NULL OR acquisition_method IN "
            "('purchase', 'gift', 'inheritance', 'other')",
            name="ck_skydiver_component_acquisition_method",
        ),
        CheckConstraint(
            "relation = 'owned' OR (acquisition_method IS NULL AND acquired IS NULL)",
            name="ck_skydiver_component_acquisition_owned",
        ),
        CheckConstraint(
            "manufactured " + _PARTIAL.format("manufactured"),
            name="ck_skydiver_component_manufactured",
        ),
        CheckConstraint(
            "acquired " + _PARTIAL.format("acquired"),
            name="ck_skydiver_component_acquired",
        ),
        CheckConstraint(
            "repack_interval_days IS NULL OR repack_interval_days BETWEEN 1 AND 730",
            name="ck_skydiver_component_repack_interval",
        ),
        CheckConstraint(
            "(jump_limit IS NULL AND jump_limit_label IS NULL"
            " AND jump_limit_service_kind IS NULL)"
            " OR (jump_limit BETWEEN 1 AND 100000 AND jump_limit_label IS NOT NULL"
            " AND jump_limit_service_kind IN"
            " ('repack', 'inspection', 'maintenance', 'aad_service', 'other'))",
            name="ck_skydiver_component_jump_limit",
        ),
        UniqueConstraint(
            "owner_person_id", "client_key", name="uq_skydiver_component_key"
        ),
    )

    id: uuid.UUID = Field(default_factory=uuid.uuid7, primary_key=True)
    owner_person_id: uuid.UUID = Field(sa_column=_owner())
    client_key: uuid.UUID
    fingerprint: str = Field(max_length=64)
    kind: str = Field(max_length=16)
    label: str = Field(max_length=80)
    manufacturer: str | None = Field(default=None, max_length=80)
    model: str | None = Field(default=None, max_length=80)
    # Exactly as entered; private; never a lookup key across accounts.
    serial: str | None = Field(default=None, max_length=120)
    serial_key: str | None = Field(default=None, max_length=120)
    manufactured: str | None = Field(default=None, max_length=10)
    relation: str = Field(max_length=16)
    acquisition_method: str | None = Field(default=None, max_length=16)
    acquired: str | None = Field(default=None, max_length=10)
    notes: str | None = Field(default=None, sa_column=Column(Text, nullable=True))
    # The owner's own repack interval for a reserve; NULL: the default (policy).
    repack_interval_days: int | None = Field(
        default=None, sa_column=Column(Integer, nullable=True)
    )
    # Only a date the owner entered (e.g. from an AAD's label); never estimated.
    end_of_life_on: date | None = Field(
        default=None, sa_column=Column(Date, nullable=True)
    )
    # One jump-count limit the owner sets (e.g. "Reline" after 500 jumps), counted
    # from the jumps using it since the latest service entry of the kind named.
    # All three empty, or all set; never a manufacturer number filled in for them.
    jump_limit: int | None = Field(
        default=None, sa_column=Column(Integer, nullable=True)
    )
    jump_limit_label: str | None = Field(default=None, max_length=80)
    jump_limit_service_kind: str | None = Field(default=None, max_length=16)
    archived_at: datetime | None = Field(
        default=None, sa_column=Column(DateTime(timezone=True), nullable=True)
    )
    version: int = Field(default=1, sa_column=_version())
    created_at: datetime = Field(sa_column=_instant())
    updated_at: datetime = Field(sa_column=_instant())


class SkydiverRig(SQLModel, table=True):
    """A named assembly. Membership is dated; it never changes a component's history."""

    __tablename__ = "skydiver_rig"
    __table_args__ = (
        UniqueConstraint("owner_person_id", "client_key", name="uq_skydiver_rig_key"),
    )

    id: uuid.UUID = Field(default_factory=uuid.uuid7, primary_key=True)
    owner_person_id: uuid.UUID = Field(sa_column=_owner())
    client_key: uuid.UUID
    label: str = Field(max_length=80)
    archived_at: datetime | None = Field(
        default=None, sa_column=Column(DateTime(timezone=True), nullable=True)
    )
    version: int = Field(default=1, sa_column=_version())
    created_at: datetime = Field(sa_column=_instant())
    updated_at: datetime = Field(sa_column=_instant())


class SkydiverRigMembership(SQLModel, table=True):
    """A component in a rig from `from_on` until `until_on` (exclusive; NULL = current)."""

    __tablename__ = "skydiver_rig_membership"
    __table_args__ = (
        CheckConstraint(
            "until_on IS NULL OR until_on >= from_on",
            name="ck_skydiver_membership_dates",
        ),
        Index("ix_skydiver_membership_component", "component_id", "from_on"),
        Index("ix_skydiver_membership_rig", "rig_id", "from_on"),
    )

    id: uuid.UUID = Field(default_factory=uuid.uuid7, primary_key=True)
    owner_person_id: uuid.UUID = Field(sa_column=_owner())
    rig_id: uuid.UUID = Field(
        sa_column=Column(
            ForeignKey("skydiver_rig.id", ondelete="CASCADE"), nullable=False
        )
    )
    component_id: uuid.UUID = Field(
        sa_column=Column(
            ForeignKey("skydiver_component.id", ondelete="CASCADE"), nullable=False
        )
    )
    from_on: date = Field(sa_column=Column(Date, nullable=False))
    until_on: date | None = Field(default=None, sa_column=Column(Date, nullable=True))


class SkydiverServiceEntry(SQLModel, table=True):
    """Servicing the owner says happened. Not a certification or airworthiness record."""

    __tablename__ = "skydiver_service_entry"
    __table_args__ = (
        CheckConstraint(
            "kind IN ('repack', 'inspection', 'maintenance', 'aad_service', 'other')",
            name="ck_skydiver_service_kind",
        ),
        CheckConstraint(
            "due_on IS NULL OR due_on >= done_on", name="ck_skydiver_service_due"
        ),
        UniqueConstraint(
            "owner_person_id", "client_key", name="uq_skydiver_service_key"
        ),
        Index("ix_skydiver_service_component", "component_id", "done_on"),
    )

    id: uuid.UUID = Field(default_factory=uuid.uuid7, primary_key=True)
    owner_person_id: uuid.UUID = Field(sa_column=_owner())
    client_key: uuid.UUID
    fingerprint: str = Field(max_length=64)
    component_id: uuid.UUID = Field(
        sa_column=Column(
            ForeignKey("skydiver_component.id", ondelete="CASCADE"), nullable=False
        )
    )
    kind: str = Field(max_length=16)
    done_on: date = Field(sa_column=Column(Date, nullable=False))
    due_on: date | None = Field(default=None, sa_column=Column(Date, nullable=True))
    performed_by: str | None = Field(default=None, max_length=120)
    notes: str | None = Field(default=None, sa_column=Column(Text, nullable=True))
    created_at: datetime = Field(sa_column=_instant())


class SkydiverGearEvent(SQLModel, table=True):
    """Owner-only correction history. Keeps earlier identifiers, not old notes."""

    __tablename__ = "skydiver_gear_event"
    __table_args__ = (Index("ix_skydiver_gear_event_component", "component_id", "id"),)

    id: uuid.UUID = Field(default_factory=uuid.uuid7, primary_key=True)
    owner_person_id: uuid.UUID = Field(sa_column=_owner())
    component_id: uuid.UUID = Field(
        sa_column=Column(
            ForeignKey("skydiver_component.id", ondelete="CASCADE"), nullable=False
        )
    )
    kind: str = Field(sa_column=Column(String(32), nullable=False))
    detail: dict = Field(  # type: ignore[type-arg]
        default_factory=dict,
        sa_column=Column(JSONB().with_variant(JSON(), "sqlite"), nullable=False),
    )
    created_at: datetime = Field(sa_column=_instant())
