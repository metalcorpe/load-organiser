"""Completed-restore receipts (#155). Owner-scoped; one per exact archive file.

`sequence` numbers a person's restores; the unique (owner, sequence) pair is the
compare-and-swap that lets only one of two simultaneous restores commit (#160).
"""

import uuid
from datetime import datetime

from sqlalchemy import Column, DateTime, ForeignKey, Integer, String, UniqueConstraint
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.types import JSON
from sqlmodel import Field, SQLModel

_JSON = JSONB().with_variant(JSON(), "sqlite")


class SkydiverRestoreReceipt(SQLModel, table=True):
    """The SHA-256 of the raw archive bytes and what was restored from them."""

    __tablename__ = "skydiver_restore_receipt"
    __table_args__ = (
        UniqueConstraint(
            "owner_person_id", "fingerprint", name="uq_skydiver_restore_receipt"
        ),
        UniqueConstraint(
            "owner_person_id", "sequence", name="uq_skydiver_restore_receipt_sequence"
        ),
    )

    id: uuid.UUID = Field(default_factory=uuid.uuid7, primary_key=True)
    owner_person_id: uuid.UUID = Field(
        sa_column=Column(
            ForeignKey("skydiver_person.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        )
    )
    fingerprint: str = Field(sa_column=Column(String(64), nullable=False))
    sequence: int = Field(sa_column=Column(Integer, nullable=False))
    format_version: int = Field(sa_column=Column(Integer, nullable=False))
    counts: dict = Field(  # type: ignore[type-arg]
        default_factory=dict, sa_column=Column(_JSON, nullable=False)
    )
    created_at: datetime = Field(
        sa_column=Column(DateTime(timezone=True), nullable=False)
    )
