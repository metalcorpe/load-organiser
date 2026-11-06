"""Skydiver profiles, follows, blocks and profile reports (#156)

Additive only; new tables with no data.

Revision ID: a6c9e3f1d2b8
Revises: f5b8d2e1c4a7
Create Date: 2026-11-04
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "a6c9e3f1d2b8"
down_revision = "f5b8d2e1c4a7"
branch_labels = None
depends_on = None

UUID = postgresql.UUID(as_uuid=True)
TZ = sa.DateTime(timezone=True)


def _person(name: str, *, primary_key: bool = False) -> sa.Column:  # type: ignore[type-arg]
    return sa.Column(
        name,
        UUID,
        sa.ForeignKey("skydiver_person.id", ondelete="CASCADE"),
        primary_key=primary_key,
        nullable=False,
    )


def upgrade() -> None:
    op.create_table(
        "skydiver_profile",
        _person("person_id", primary_key=True),
        sa.Column("handle", sa.String(30), nullable=False, unique=True),
        sa.Column("display_name", sa.String(60), nullable=False),
        sa.Column("bio", sa.Text(), nullable=True),
        sa.Column("disciplines", postgresql.JSONB(), nullable=False),
        sa.Column(
            "home_venue_id", UUID, sa.ForeignKey("skydiver_venue.id"), nullable=True
        ),
        sa.Column("discoverable", sa.Boolean(), nullable=False),
        sa.Column("hidden_at", TZ, nullable=True),
        sa.Column("publishing_restricted_at", TZ, nullable=True),
        sa.Column("moderation_reason", sa.String(280), nullable=True),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("created_at", TZ, nullable=False),
        sa.Column("updated_at", TZ, nullable=False),
        sa.CheckConstraint(
            "length(handle) BETWEEN 3 AND 30 AND handle = lower(handle)",
            name="ck_skydiver_profile_handle",
        ),
        sa.CheckConstraint("version >= 1", name="ck_skydiver_profile_version"),
    )
    op.create_table(
        "skydiver_follow",
        _person("follower_person_id", primary_key=True),
        _person("followee_person_id", primary_key=True),
        sa.Column("status", sa.String(16), nullable=False),
        sa.Column("created_at", TZ, nullable=False),
        sa.Column("approved_at", TZ, nullable=True),
        sa.CheckConstraint(
            "follower_person_id <> followee_person_id", name="ck_skydiver_follow_self"
        ),
        sa.CheckConstraint(
            "status IN ('pending', 'approved')", name="ck_skydiver_follow_status"
        ),
    )
    op.create_index(
        "ix_skydiver_follow_followee",
        "skydiver_follow",
        ["followee_person_id", "status"],
    )
    op.create_table(
        "skydiver_block",
        _person("blocker_person_id", primary_key=True),
        _person("blocked_person_id", primary_key=True),
        sa.Column("created_at", TZ, nullable=False),
        sa.CheckConstraint(
            "blocker_person_id <> blocked_person_id", name="ck_skydiver_block_self"
        ),
    )
    op.create_index(
        "ix_skydiver_block_blocked", "skydiver_block", ["blocked_person_id"]
    )
    op.create_table(
        "skydiver_social_report",
        sa.Column("id", UUID, primary_key=True),
        _person("reporter_person_id"),
        _person("target_person_id"),
        sa.Column("reason", sa.String(16), nullable=False),
        sa.Column("note", sa.Text(), nullable=True),
        sa.Column("snapshot", postgresql.JSONB(), nullable=False),
        sa.Column("status", sa.String(8), nullable=False),
        sa.Column("decision", sa.String(24), nullable=True),
        sa.Column("decision_reason", sa.String(280), nullable=True),
        sa.Column("decided_by_account_id", UUID, nullable=True),
        sa.Column("decided_at", TZ, nullable=True),
        sa.Column("created_at", TZ, nullable=False),
        sa.CheckConstraint(
            "reason IN ('impersonation', 'harassment', 'spam', 'inappropriate', 'other')",
            name="ck_skydiver_social_report_reason",
        ),
        sa.CheckConstraint(
            "status IN ('open', 'closed')", name="ck_skydiver_social_report_status"
        ),
        sa.CheckConstraint(
            "decision IS NULL OR decision IN "
            "('no_action', 'hide_profile', 'restrict_publishing')",
            name="ck_skydiver_social_report_decision",
        ),
        sa.CheckConstraint(
            "(status = 'closed') = (decision IS NOT NULL)",
            name="ck_skydiver_social_report_decided",
        ),
    )
    op.create_index(
        "uq_skydiver_social_report_open",
        "skydiver_social_report",
        ["reporter_person_id", "target_person_id"],
        unique=True,
        postgresql_where=sa.text("status = 'open'"),
    )
    op.create_index(
        "ix_skydiver_social_report_status", "skydiver_social_report", ["status", "id"]
    )


def downgrade() -> None:
    op.drop_table("skydiver_social_report")
    op.drop_table("skydiver_block")
    op.drop_table("skydiver_follow")
    op.drop_table("skydiver_profile")
