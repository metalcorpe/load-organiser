"""Persistence rows for providers and opportunities (#149). Adapters only."""

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
    Numeric,
    Text,
)
from sqlalchemy.dialects.postgresql import ARRAY, JSONB
from sqlmodel import Field, SQLModel


def _instant(nullable: bool = False) -> Column:  # type: ignore[type-arg]
    return Column(DateTime(timezone=True), nullable=nullable)


def _tags() -> Column:  # type: ignore[type-arg]
    # JSON variant only so the legacy SQLite metadata test can create every table.
    return Column(
        ARRAY(Text).with_variant(JSON(), "sqlite"),
        nullable=False,
        server_default="{}",
    )


class SkydiverProvider(SQLModel, table=True):
    """Public organiser identity. No account link, contact person or credentials."""

    __tablename__ = "skydiver_provider"
    __table_args__ = (
        CheckConstraint(
            "status IN ('draft', 'published', 'archived', 'merged')",
            name="skydiver_provider_status",
        ),
        CheckConstraint(
            "kind IN ('organization', 'person')", name="skydiver_provider_kind"
        ),
        CheckConstraint(
            "(status = 'merged') = (merged_into_id IS NOT NULL)",
            name="skydiver_provider_merge_target",
        ),
        CheckConstraint(
            "status <> 'published' OR (source_url IS NOT NULL AND checked_on IS NOT NULL)",
            name="skydiver_provider_source_backed",
        ),
        CheckConstraint("merged_into_id <> id", name="skydiver_provider_not_self"),
    )

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    name: str = Field(max_length=120)
    name_key: str = Field(sa_column=Column(Text, nullable=False, index=True))
    kind: str = Field(max_length=16)
    country: str | None = Field(default=None, max_length=2)
    website_url: str | None = Field(default=None, max_length=2048)
    status: str = Field(max_length=16)
    merged_into_id: uuid.UUID | None = Field(
        default=None,
        sa_column=Column(ForeignKey("skydiver_provider.id"), nullable=True),
    )
    source_url: str | None = Field(default=None, max_length=2048)
    source_note: str | None = Field(default=None, max_length=280)
    checked_on: date | None = Field(default=None, sa_column=Column(Date, nullable=True))
    created_at: datetime = Field(sa_column=_instant())
    updated_at: datetime = Field(sa_column=_instant())


class SkydiverOpportunity(SQLModel, table=True):
    """A sourced dated offering. Not inventory: no capacity, booking or attendee data."""

    __tablename__ = "skydiver_opportunity"
    __table_args__ = (
        CheckConstraint(
            "status IN ('draft', 'review', 'published', 'postponed', 'cancelled',"
            " 'archived', 'duplicate')",
            name="skydiver_opportunity_status",
        ),
        CheckConstraint(
            "category IN ('event', 'boogie', 'camp', 'course')",
            name="skydiver_opportunity_category",
        ),
        CheckConstraint(
            "(status = 'duplicate') = (duplicate_of_id IS NOT NULL)",
            name="skydiver_opportunity_duplicate_target",
        ),
        CheckConstraint("duplicate_of_id <> id", name="skydiver_opportunity_not_self"),
        CheckConstraint(
            "(starts_on IS NULL) = (ends_on IS NULL) AND starts_on <= ends_on",
            name="skydiver_opportunity_dates",
        ),
        CheckConstraint(
            "starts_on IS NULL OR time_zone IS NOT NULL",
            name="skydiver_opportunity_dates_zoned",
        ),
        CheckConstraint(
            "(expires_at IS NULL) = (ends_on IS NULL)",
            name="skydiver_opportunity_expiry",
        ),
        CheckConstraint(
            "(price_amount IS NULL) = (price_currency IS NULL)"
            " AND (price_amount IS NULL) = (price_basis IS NULL)",
            name="skydiver_opportunity_price",
        ),
        CheckConstraint(
            "status NOT IN ('published', 'postponed', 'cancelled') OR"
            " (source_url IS NOT NULL AND checked_on IS NOT NULL"
            " AND registration_url IS NOT NULL"
            " AND (venue_id IS NOT NULL OR location_note IS NOT NULL))",
            name="skydiver_opportunity_publishable",
        ),
        CheckConstraint(
            "status NOT IN ('published', 'cancelled') OR starts_on IS NOT NULL",
            name="skydiver_opportunity_dated",
        ),
        Index("ix_skydiver_opportunity_upcoming", "status", "sort_on", "id"),
    )

    id: uuid.UUID = Field(default_factory=uuid.uuid4, primary_key=True)
    title: str = Field(max_length=160)
    title_key: str = Field(sa_column=Column(Text, nullable=False))
    category: str = Field(max_length=16)
    provider_id: uuid.UUID = Field(
        sa_column=Column(ForeignKey("skydiver_provider.id"), nullable=False, index=True)
    )
    venue_id: uuid.UUID | None = Field(
        default=None,
        sa_column=Column(ForeignKey("skydiver_venue.id"), nullable=True, index=True),
    )
    country: str = Field(max_length=2)
    location_note: str | None = Field(default=None, max_length=200)
    starts_on: date | None = Field(default=None, sa_column=Column(Date, nullable=True))
    ends_on: date | None = Field(default=None, sa_column=Column(Date, nullable=True))
    time_zone: str | None = Field(default=None, max_length=64)
    expires_at: datetime | None = Field(default=None, sa_column=_instant(True))
    sort_on: date = Field(sa_column=Column(Date, nullable=False))
    disciplines: list[str] = Field(default_factory=list, sa_column=_tags())
    audience: list[str] = Field(default_factory=list, sa_column=_tags())
    languages: list[str] = Field(default_factory=list, sa_column=_tags())
    summary: str | None = Field(default=None, max_length=500)
    prerequisites: str | None = Field(default=None, max_length=1000)
    price_amount: Decimal | None = Field(
        default=None, sa_column=Column(Numeric(10, 2), nullable=True)
    )
    price_currency: str | None = Field(default=None, max_length=3)
    price_basis: str | None = Field(default=None, max_length=16)
    price_note: str | None = Field(default=None, max_length=280)
    registration_url: str | None = Field(default=None, max_length=2048)
    source_url: str | None = Field(default=None, max_length=2048)
    source_note: str | None = Field(default=None, max_length=280)
    checked_on: date | None = Field(default=None, sa_column=Column(Date, nullable=True))
    status: str = Field(max_length=16)
    duplicate_of_id: uuid.UUID | None = Field(
        default=None,
        sa_column=Column(ForeignKey("skydiver_opportunity.id"), nullable=True),
    )
    created_at: datetime = Field(sa_column=_instant())
    updated_at: datetime = Field(sa_column=_instant())


class SkydiverListingEvent(SQLModel, table=True):
    """Reviewer change history for one provider or one opportunity. Never public.

    IDs are UUIDv7 so events written in the same instant keep their order.
    """

    __tablename__ = "skydiver_listing_event"
    __table_args__ = (
        CheckConstraint(
            "(provider_id IS NULL) <> (opportunity_id IS NULL)",
            name="skydiver_listing_event_subject",
        ),
    )

    id: uuid.UUID = Field(default_factory=uuid.uuid7, primary_key=True)
    provider_id: uuid.UUID | None = Field(
        default=None,
        sa_column=Column(
            ForeignKey("skydiver_provider.id", ondelete="CASCADE"),
            nullable=True,
            index=True,
        ),
    )
    opportunity_id: uuid.UUID | None = Field(
        default=None,
        sa_column=Column(
            ForeignKey("skydiver_opportunity.id", ondelete="CASCADE"),
            nullable=True,
            index=True,
        ),
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
