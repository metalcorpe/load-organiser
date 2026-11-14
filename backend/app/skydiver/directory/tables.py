"""Persistence rows for the directory (#148). Adapters only; policy never imports this."""

import uuid
from datetime import date, datetime
from decimal import Decimal
from typing import Any

from sqlalchemy import (
    JSON,
    CheckConstraint,
    Column,
    Date,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    Numeric,
    Text,
    UniqueConstraint,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlmodel import Field, SQLModel


def _instant() -> Column:  # type: ignore[type-arg]
    return Column(DateTime(timezone=True), nullable=False)


class SkydiverVenue(SQLModel, table=True):
    """Public directory identity. No claim, endorsement or verification fields.

    `operators`, `season` and `aircraft` are what the source states (owner decision
    2026-11-14): they name who runs the place, not that it takes part in anything.
    """

    __tablename__ = "skydiver_venue"
    __table_args__ = (
        CheckConstraint(
            "status IN ('draft', 'listed', 'closed', 'merged')",
            name="skydiver_venue_status",
        ),
        CheckConstraint(
            "(status = 'merged') = (merged_into_id IS NOT NULL)",
            name="skydiver_venue_merge_target",
        ),
        CheckConstraint(
            "status = 'draft' OR (source_url IS NOT NULL AND checked_on IS NOT NULL)",
            name="skydiver_venue_source_backed",
        ),
        CheckConstraint(
            "(latitude IS NULL) = (longitude IS NULL)",
            name="skydiver_venue_coordinates_pair",
        ),
        CheckConstraint("merged_into_id <> id", name="skydiver_venue_not_self"),
        # skydiver_venue_operators_list (an array of at most 4) is created by migration
        # e8bcedce6f4a only: its JSONB functions are PostgreSQL-specific.
        Index("ix_skydiver_venue_search", "status", "name_key", "id"),
    )

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    name: str = Field(max_length=120)
    name_key: str = Field(sa_column=Column(Text, nullable=False))
    country: str = Field(max_length=2)
    locality: str | None = Field(default=None, max_length=120)
    latitude: Decimal | None = Field(
        default=None, sa_column=Column(Numeric(9, 6), nullable=True)
    )
    longitude: Decimal | None = Field(
        default=None, sa_column=Column(Numeric(9, 6), nullable=True)
    )
    status: str = Field(max_length=16)
    # Compare-and-swap version: every write sets version = version + 1 WHERE version = read.
    version: int = Field(
        default=1, sa_column=Column(Integer, nullable=False, server_default="1")
    )
    merged_into_id: uuid.UUID | None = Field(
        default=None,
        sa_column=Column(ForeignKey("skydiver_venue.id"), nullable=True),
    )
    source_url: str | None = Field(default=None, max_length=2048)
    source_note: str | None = Field(default=None, max_length=280)
    checked_on: date | None = Field(default=None, sa_column=Column(Date, nullable=True))
    # [{"name": str, "url": str | None}, ...], at most 4 (policy.operators).
    operators: list[dict[str, Any]] = Field(
        default_factory=list,
        sa_column=Column(
            JSONB().with_variant(JSON(), "sqlite"),
            nullable=False,
            server_default=text("'[]'"),
        ),
    )
    season: str | None = Field(default=None, max_length=160)
    aircraft: str | None = Field(default=None, max_length=160)
    created_at: datetime = Field(sa_column=_instant())
    updated_at: datetime = Field(sa_column=_instant())


class SkydiverVenueAlias(SQLModel, table=True):
    __tablename__ = "skydiver_venue_alias"
    __table_args__ = (
        CheckConstraint(
            "kind IN ('alternate', 'former', 'merged')",
            name="skydiver_venue_alias_kind",
        ),
        UniqueConstraint("venue_id", "alias_key", name="uq_skydiver_venue_alias"),
        Index("ix_skydiver_venue_alias_key", "alias_key"),
    )

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    venue_id: uuid.UUID = Field(
        sa_column=Column(
            ForeignKey("skydiver_venue.id", ondelete="CASCADE"), nullable=False
        )
    )
    alias: str = Field(max_length=120)
    alias_key: str = Field(sa_column=Column(Text, nullable=False))
    kind: str = Field(max_length=16)
    created_at: datetime = Field(sa_column=_instant())


class SkydiverVenueEvent(SQLModel, table=True):
    """Change history: distinguishes renames, relocations, closures and merges."""

    __tablename__ = "skydiver_venue_event"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    venue_id: uuid.UUID = Field(
        sa_column=Column(
            ForeignKey("skydiver_venue.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        )
    )
    kind: str = Field(max_length=24)
    detail: dict[str, Any] = Field(
        default_factory=dict, sa_column=Column(JSONB, nullable=False)
    )
    actor_account_id: uuid.UUID | None = Field(
        default=None,
        sa_column=Column(ForeignKey("user.id", ondelete="SET NULL"), nullable=True),
    )
    created_at: datetime = Field(sa_column=_instant())


class SkydiverProvisionalPlace(SQLModel, table=True):
    """A person's private place name. Never public; never creates a venue."""

    __tablename__ = "skydiver_provisional_place"

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    owner_person_id: uuid.UUID = Field(
        sa_column=Column(
            ForeignKey("skydiver_person.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        )
    )
    name: str = Field(max_length=120)
    country: str = Field(max_length=2)
    # The owner's own link to a listed venue; read through merge redirects.
    venue_id: uuid.UUID | None = Field(
        default=None,
        sa_column=Column(ForeignKey("skydiver_venue.id"), nullable=True),
    )
    created_at: datetime = Field(sa_column=_instant())
    updated_at: datetime = Field(sa_column=_instant())
