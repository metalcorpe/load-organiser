"""Owner-scoped tables for saved opportunities and visit plans (#150).

Both carry `owner_person_id` and are read and written only through
`app.skydiver.access.sql`. Nothing here is public, shared or an attendance claim.
"""

import uuid
from datetime import date, datetime

from sqlalchemy import (
    CheckConstraint,
    Column,
    Date,
    DateTime,
    ForeignKey,
    UniqueConstraint,
)
from sqlmodel import Field, SQLModel


def _instant() -> Column:  # type: ignore[type-arg]
    return Column(DateTime(timezone=True), nullable=False)


def _owner() -> Column:  # type: ignore[type-arg]
    return Column(
        ForeignKey("skydiver_person.id", ondelete="CASCADE"), nullable=False, index=True
    )


class SkydiverSavedOpportunity(SQLModel, table=True):
    """A private bookmark. Not registration, attendance or interest shown to anyone."""

    __tablename__ = "skydiver_saved_opportunity"
    __table_args__ = (
        UniqueConstraint(
            "owner_person_id", "opportunity_id", name="uq_skydiver_saved_opportunity"
        ),
    )

    id: uuid.UUID = Field(default_factory=uuid.uuid7, primary_key=True)
    owner_person_id: uuid.UUID = Field(sa_column=_owner())
    opportunity_id: uuid.UUID = Field(
        sa_column=Column(ForeignKey("skydiver_opportunity.id"), nullable=False)
    )
    # The title when saved, shown if the listing is later withdrawn.
    title: str = Field(max_length=200)
    created_at: datetime = Field(sa_column=_instant())


class SkydiverVisitPlan(SQLModel, table=True):
    """A private dated plan. Never shared, never a jump or presence record."""

    __tablename__ = "skydiver_visit_plan"
    __table_args__ = (
        CheckConstraint("ends_on >= starts_on", name="ck_skydiver_visit_plan_dates"),
        CheckConstraint(
            "(CASE WHEN opportunity_id IS NULL THEN 0 ELSE 1 END"
            " + CASE WHEN venue_id IS NULL THEN 0 ELSE 1 END"
            " + CASE WHEN place_id IS NULL THEN 0 ELSE 1 END) <= 1",
            name="ck_skydiver_visit_plan_one_link",
        ),
    )

    id: uuid.UUID = Field(default_factory=uuid.uuid7, primary_key=True)
    owner_person_id: uuid.UUID = Field(sa_column=_owner())
    title: str = Field(max_length=120)
    starts_on: date = Field(sa_column=Column(Date, nullable=False))
    ends_on: date = Field(sa_column=Column(Date, nullable=False))
    note: str | None = Field(default=None, max_length=500)
    opportunity_id: uuid.UUID | None = Field(
        default=None,
        sa_column=Column(ForeignKey("skydiver_opportunity.id"), nullable=True),
    )
    venue_id: uuid.UUID | None = Field(
        default=None, sa_column=Column(ForeignKey("skydiver_venue.id"), nullable=True)
    )
    # The owner's own private place; deleting the place keeps the plan.
    place_id: uuid.UUID | None = Field(
        default=None,
        sa_column=Column(
            ForeignKey("skydiver_provisional_place.id", ondelete="SET NULL"),
            nullable=True,
        ),
    )
    created_at: datetime = Field(sa_column=_instant())
    updated_at: datetime = Field(sa_column=_instant())
