"""Skydiver suggestions, corrections and reports (#151)

Additive only; no data.

Revision ID: b5e3c8a1f204
Revises: 4a8e2f6c9d17
Create Date: 2026-11-03
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "b5e3c8a1f204"
down_revision = "4a8e2f6c9d17"
branch_labels = None
depends_on = None

UUID = postgresql.UUID(as_uuid=True)
TZ = sa.DateTime(timezone=True)


def upgrade() -> None:
    op.create_table(
        "skydiver_submission",
        sa.Column("id", UUID, primary_key=True),
        sa.Column(
            "submitter_person_id",
            UUID,
            sa.ForeignKey("skydiver_person.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("client_key", UUID, nullable=False),
        sa.Column("fingerprint", sa.String(64), nullable=False),
        sa.Column("kind", sa.String(24), nullable=False),
        sa.Column("target_kind", sa.String(16), nullable=True),
        sa.Column("target_id", UUID, nullable=True),
        sa.Column("message", sa.Text(), nullable=False),
        sa.Column("source_url", sa.String(2048), nullable=True),
        sa.Column("status", sa.String(16), nullable=False),
        sa.Column("resolution_note", sa.String(280), nullable=True),
        sa.Column("resolved_at", TZ, nullable=True),
        sa.Column(
            "resolved_by_account_id",
            UUID,
            sa.ForeignKey("user.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("version", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("created_at", TZ, nullable=False),
        sa.CheckConstraint(
            "kind IN ('suggest_venue', 'suggest_listing', 'correction', 'report')",
            name="ck_skydiver_submission_kind",
        ),
        sa.CheckConstraint(
            "status IN ('open', 'accepted', 'declined')",
            name="ck_skydiver_submission_status",
        ),
        sa.CheckConstraint(
            "target_kind IS NULL OR target_kind IN ('venue', 'provider', 'opportunity')",
            name="ck_skydiver_submission_target_kind",
        ),
        sa.CheckConstraint(
            "(target_kind IS NULL) = (target_id IS NULL)",
            name="ck_skydiver_submission_target_pair",
        ),
        sa.CheckConstraint(
            "kind NOT IN ('correction', 'report') OR target_id IS NOT NULL",
            name="ck_skydiver_submission_target_required",
        ),
        sa.CheckConstraint(
            "(status = 'open') = (resolved_at IS NULL)",
            name="ck_skydiver_submission_resolved",
        ),
        sa.UniqueConstraint(
            "submitter_person_id", "client_key", name="uq_skydiver_submission_key"
        ),
    )
    op.create_index(
        "ix_skydiver_submission_queue",
        "skydiver_submission",
        ["status", "created_at", "id"],
    )
    op.create_index(
        "ix_skydiver_submission_submitter",
        "skydiver_submission",
        ["submitter_person_id", "created_at"],
    )


def downgrade() -> None:
    op.drop_table("skydiver_submission")
