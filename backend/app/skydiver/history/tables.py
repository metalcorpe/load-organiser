"""Owner-scoped prior-history baseline tables (#154). Adapters only.

One current baseline per person, plus private correction provenance that outlives
a removal. Nothing here is a jump, a gear use or shared with anyone.
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
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.types import JSON
from sqlmodel import Field, SQLModel

_JSON = JSONB().with_variant(JSON(), "sqlite")


def _instant() -> Column:  # type: ignore[type-arg]
    return Column(DateTime(timezone=True), nullable=False)


class SkydiverJumpBaseline(SQLModel, table=True):
    """B jumps completed before D, as the owner declared it."""

    __tablename__ = "skydiver_jump_baseline"
    __table_args__ = (
        CheckConstraint(
            "prior_jumps BETWEEN 0 AND 100000", name="ck_skydiver_baseline_prior"
        ),
        CheckConstraint(
            "source IN ('manual', 'restored')", name="ck_skydiver_baseline_source"
        ),
        CheckConstraint("version >= 1", name="ck_skydiver_baseline_version"),
    )

    owner_person_id: uuid.UUID = Field(
        sa_column=Column(
            ForeignKey("skydiver_person.id", ondelete="CASCADE"), primary_key=True
        )
    )
    prior_jumps: int = Field(sa_column=Column(Integer, nullable=False))
    before_on: date = Field(sa_column=Column(Date, nullable=False))
    source: str = Field(default="manual", sa_column=Column(String(16), nullable=False))
    version: int = Field(default=1, sa_column=Column(Integer, nullable=False))
    created_at: datetime = Field(sa_column=_instant())
    updated_at: datetime = Field(sa_column=_instant())


class SkydiverJumpBaselineEvent(SQLModel, table=True):
    """Declared, corrected and removed values, newest last. Owner-only."""

    __tablename__ = "skydiver_jump_baseline_event"
    __table_args__ = (
        Index("ix_skydiver_baseline_event_owner", "owner_person_id", "id"),
    )

    id: uuid.UUID = Field(default_factory=uuid.uuid7, primary_key=True)
    owner_person_id: uuid.UUID = Field(
        sa_column=Column(
            ForeignKey("skydiver_person.id", ondelete="CASCADE"), nullable=False
        )
    )
    kind: str = Field(sa_column=Column(String(16), nullable=False))
    detail: dict = Field(  # type: ignore[type-arg]
        default_factory=dict, sa_column=Column(_JSON, nullable=False)
    )
    created_at: datetime = Field(sa_column=_instant())
