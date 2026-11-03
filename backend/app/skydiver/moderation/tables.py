"""Submission rows (#151). Adapters only; policy never imports this module."""

import uuid
from datetime import datetime

from sqlalchemy import (
    CheckConstraint,
    Column,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    Text,
    UniqueConstraint,
)
from sqlmodel import Field, SQLModel


def _instant(*, nullable: bool = False) -> Column:  # type: ignore[type-arg]
    return Column(DateTime(timezone=True), nullable=nullable)


class SkydiverSubmission(SQLModel, table=True):
    """A signed-in person's suggestion, correction or report.

    Reviewers see the content, never who sent it. The submitter sees status and the
    resolution note. Deleting the account keeps the case without its author.
    """

    __tablename__ = "skydiver_submission"
    __table_args__ = (
        CheckConstraint(
            "kind IN ('suggest_venue', 'suggest_listing', 'correction', 'report')",
            name="ck_skydiver_submission_kind",
        ),
        CheckConstraint(
            "status IN ('open', 'accepted', 'declined')",
            name="ck_skydiver_submission_status",
        ),
        CheckConstraint(
            "target_kind IS NULL OR target_kind IN ('venue', 'provider', 'opportunity')",
            name="ck_skydiver_submission_target_kind",
        ),
        CheckConstraint(
            "(target_kind IS NULL) = (target_id IS NULL)",
            name="ck_skydiver_submission_target_pair",
        ),
        CheckConstraint(
            "kind NOT IN ('correction', 'report') OR target_id IS NOT NULL",
            name="ck_skydiver_submission_target_required",
        ),
        CheckConstraint(
            "(status = 'open') = (resolved_at IS NULL)",
            name="ck_skydiver_submission_resolved",
        ),
        UniqueConstraint(
            "submitter_person_id", "client_key", name="uq_skydiver_submission_key"
        ),
        Index("ix_skydiver_submission_queue", "status", "created_at", "id"),
        Index("ix_skydiver_submission_submitter", "submitter_person_id", "created_at"),
    )

    id: uuid.UUID = Field(default_factory=uuid.uuid7, primary_key=True)
    submitter_person_id: uuid.UUID | None = Field(
        default=None,
        sa_column=Column(
            ForeignKey("skydiver_person.id", ondelete="SET NULL"), nullable=True
        ),
    )
    # Client-generated identity of this submission, so a retry is not a duplicate.
    client_key: uuid.UUID
    # Digest of the validated content, so reusing a key for other content is refused.
    fingerprint: str = Field(max_length=64)
    kind: str = Field(max_length=24)
    target_kind: str | None = Field(default=None, max_length=16)
    target_id: uuid.UUID | None = None
    message: str = Field(sa_column=Column(Text, nullable=False))
    source_url: str | None = Field(default=None, max_length=2048)
    status: str = Field(max_length=16)
    resolution_note: str | None = Field(default=None, max_length=280)
    resolved_at: datetime | None = Field(
        default=None, sa_column=_instant(nullable=True)
    )
    resolved_by_account_id: uuid.UUID | None = Field(
        default=None,
        sa_column=Column(ForeignKey("user.id", ondelete="SET NULL"), nullable=True),
    )
    version: int = Field(
        default=1, sa_column=Column(Integer, nullable=False, server_default="1")
    )
    created_at: datetime = Field(sa_column=_instant())
