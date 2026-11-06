"""Published jump summaries (#157). Adapters only.

A post stores only the values its owner selected when publishing, copied from one
version of one of their jumps. It is not a jump: totals and gear use never read it.
Deleting the jump deletes the post (cascade); editing a shared field withdraws it
in the same transaction as the edit.
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
)
from sqlmodel import Field, SQLModel


def _instant() -> Column:  # type: ignore[type-arg]
    return Column(DateTime(timezone=True), nullable=False)


class SkydiverJumpPost(SQLModel, table=True):
    """One published summary per jump. A null value was not selected for sharing."""

    __tablename__ = "skydiver_jump_post"
    __table_args__ = (
        CheckConstraint(
            "audience IN ('followers', 'public')", name="ck_skydiver_jump_post_audience"
        ),
        CheckConstraint(
            "(exit_altitude IS NULL) = (altitude_unit IS NULL)"
            " AND (exit_altitude IS NULL) = (altitude_datum IS NULL)",
            name="ck_skydiver_jump_post_altitude",
        ),
        CheckConstraint(
            "caption IS NULL OR length(caption) <= 280",
            name="ck_skydiver_jump_post_caption",
        ),
        CheckConstraint("version >= 1", name="ck_skydiver_jump_post_version"),
        # The id is a uuid7, so id order is publication order.
        Index("ix_skydiver_jump_post_owner", "owner_person_id", "id"),
    )

    id: uuid.UUID = Field(default_factory=uuid.uuid7, primary_key=True)
    owner_person_id: uuid.UUID = Field(
        sa_column=Column(
            ForeignKey("skydiver_person.id", ondelete="CASCADE"), nullable=False
        )
    )
    jump_id: uuid.UUID = Field(
        sa_column=Column(
            ForeignKey("skydiver_jump.id", ondelete="CASCADE"),
            nullable=False,
            unique=True,
        )
    )
    source_version: int = Field(sa_column=Column(Integer, nullable=False))
    audience: str = Field(sa_column=Column(String(16), nullable=False))
    jumped_on: date = Field(sa_column=Column(Date, nullable=False))
    jump_type: str | None = Field(
        default=None, sa_column=Column(String(16), nullable=True)
    )
    venue_id: uuid.UUID | None = Field(
        default=None,
        sa_column=Column(ForeignKey("skydiver_venue.id"), nullable=True),
    )
    exit_altitude: int | None = Field(
        default=None, sa_column=Column(Integer, nullable=True)
    )
    altitude_unit: str | None = Field(
        default=None, sa_column=Column(String(2), nullable=True)
    )
    altitude_datum: str | None = Field(
        default=None, sa_column=Column(String(12), nullable=True)
    )
    freefall_seconds: int | None = Field(
        default=None, sa_column=Column(Integer, nullable=True)
    )
    caption: str | None = Field(default=None, sa_column=Column(Text, nullable=True))
    link: str | None = Field(
        default=None, sa_column=Column(String(2048), nullable=True)
    )
    version: int = Field(
        default=1, sa_column=Column(Integer, nullable=False, server_default="1")
    )
    published_at: datetime = Field(sa_column=_instant())
    updated_at: datetime = Field(sa_column=_instant())
