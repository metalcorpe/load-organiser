"""Profiles, follows, blocks and profile reports (#156). Adapters only."""

import uuid
from datetime import datetime

from sqlalchemy import (
    Boolean,
    CheckConstraint,
    Column,
    DateTime,
    ForeignKey,
    Index,
    Integer,
    String,
    Text,
    text,
)
from sqlalchemy.dialects.postgresql import JSONB
from sqlalchemy.types import JSON
from sqlmodel import Field, SQLModel

_JSON = JSONB().with_variant(JSON(), "sqlite")


def _instant(nullable: bool = False) -> Column:  # type: ignore[type-arg]
    return Column(DateTime(timezone=True), nullable=nullable)


def _person(*, primary_key: bool = False) -> Column:  # type: ignore[type-arg]
    return Column(
        ForeignKey("skydiver_person.id", ondelete="CASCADE"),
        primary_key=primary_key,
        nullable=False,
    )


class SkydiverProfile(SQLModel, table=True):
    """A person's opt-in public profile. Separate from account and private records."""

    __tablename__ = "skydiver_profile"
    __table_args__ = (
        CheckConstraint(
            "length(handle) BETWEEN 3 AND 30 AND handle = lower(handle)",
            name="ck_skydiver_profile_handle",
        ),
        CheckConstraint("version >= 1", name="ck_skydiver_profile_version"),
    )

    person_id: uuid.UUID = Field(sa_column=_person(primary_key=True))
    handle: str = Field(sa_column=Column(String(30), nullable=False, unique=True))
    display_name: str = Field(sa_column=Column(String(60), nullable=False))
    bio: str | None = Field(default=None, sa_column=Column(Text, nullable=True))
    disciplines: list = Field(  # type: ignore[type-arg]
        default_factory=list, sa_column=Column(_JSON, nullable=False)
    )
    home_venue_id: uuid.UUID | None = Field(
        default=None,
        sa_column=Column(ForeignKey("skydiver_venue.id"), nullable=True),
    )
    discoverable: bool = Field(default=False, sa_column=Column(Boolean, nullable=False))
    # Reviewer actions on reports; never set by the owner.
    hidden_at: datetime | None = Field(default=None, sa_column=_instant(True))
    publishing_restricted_at: datetime | None = Field(
        default=None, sa_column=_instant(True)
    )
    moderation_reason: str | None = Field(
        default=None, sa_column=Column(String(280), nullable=True)
    )
    version: int = Field(default=1, sa_column=Column(Integer, nullable=False))
    created_at: datetime = Field(sa_column=_instant())
    updated_at: datetime = Field(sa_column=_instant())


class SkydiverFollow(SQLModel, table=True):
    """follower -> followee; `pending` until the followee approves."""

    __tablename__ = "skydiver_follow"
    __table_args__ = (
        CheckConstraint(
            "follower_person_id <> followee_person_id", name="ck_skydiver_follow_self"
        ),
        CheckConstraint(
            "status IN ('pending', 'approved')", name="ck_skydiver_follow_status"
        ),
        Index("ix_skydiver_follow_followee", "followee_person_id", "status"),
    )

    follower_person_id: uuid.UUID = Field(sa_column=_person(primary_key=True))
    followee_person_id: uuid.UUID = Field(sa_column=_person(primary_key=True))
    status: str = Field(sa_column=Column(String(16), nullable=False))
    created_at: datetime = Field(sa_column=_instant())
    approved_at: datetime | None = Field(default=None, sa_column=_instant(True))


class SkydiverBlock(SQLModel, table=True):
    __tablename__ = "skydiver_block"
    __table_args__ = (
        CheckConstraint(
            "blocker_person_id <> blocked_person_id", name="ck_skydiver_block_self"
        ),
        Index("ix_skydiver_block_blocked", "blocked_person_id"),
    )

    blocker_person_id: uuid.UUID = Field(sa_column=_person(primary_key=True))
    blocked_person_id: uuid.UUID = Field(sa_column=_person(primary_key=True))
    created_at: datetime = Field(sa_column=_instant())


class SkydiverSocialReport(SQLModel, table=True):
    """A report about a profile, for reviewers. The snapshot is what was reported."""

    __tablename__ = "skydiver_social_report"
    __table_args__ = (
        CheckConstraint(
            "reason IN ('impersonation', 'harassment', 'spam', 'inappropriate', 'other')",
            name="ck_skydiver_social_report_reason",
        ),
        CheckConstraint(
            "status IN ('open', 'closed')", name="ck_skydiver_social_report_status"
        ),
        CheckConstraint(
            "decision IS NULL OR decision IN "
            "('no_action', 'hide_profile', 'restrict_publishing', 'remove_post')",
            name="ck_skydiver_social_report_decision",
        ),
        CheckConstraint(
            "(status = 'closed') = (decision IS NOT NULL)",
            name="ck_skydiver_social_report_decided",
        ),
        CheckConstraint(
            "decision IS DISTINCT FROM 'remove_post' OR post_key <> ''",
            name="ck_skydiver_social_report_remove_post",
        ),
        # One open report per reporter, target and post (or the profile itself):
        # repeats are acknowledged, not stacked.
        Index(
            "uq_skydiver_social_report_open",
            "reporter_person_id",
            "target_person_id",
            "post_key",
            unique=True,
            postgresql_where=text("status = 'open'"),
        ),
        Index("ix_skydiver_social_report_status", "status", "id"),
    )

    id: uuid.UUID = Field(default_factory=uuid.uuid7, primary_key=True)
    reporter_person_id: uuid.UUID = Field(sa_column=_person())
    target_person_id: uuid.UUID = Field(sa_column=_person())
    # '' for a profile report; the reported post's id otherwise (#157). Not a
    # foreign key: the report outlives the post it is about.
    post_key: str = Field(
        default="",
        sa_column=Column(String(36), nullable=False, server_default=""),
    )
    reason: str = Field(sa_column=Column(String(16), nullable=False))
    note: str | None = Field(default=None, sa_column=Column(Text, nullable=True))
    snapshot: dict = Field(  # type: ignore[type-arg]
        default_factory=dict, sa_column=Column(_JSON, nullable=False)
    )
    status: str = Field(sa_column=Column(String(8), nullable=False))
    decision: str | None = Field(
        default=None, sa_column=Column(String(24), nullable=True)
    )
    decision_reason: str | None = Field(
        default=None, sa_column=Column(String(280), nullable=True)
    )
    decided_by_account_id: uuid.UUID | None = Field(
        default=None,
        sa_column=Column(ForeignKey("user.id", ondelete="SET NULL"), nullable=True),
    )
    decided_at: datetime | None = Field(default=None, sa_column=_instant(True))
    created_at: datetime = Field(sa_column=_instant())
