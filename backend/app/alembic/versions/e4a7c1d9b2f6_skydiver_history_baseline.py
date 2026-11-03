"""Skydiver prior-history baseline and its private provenance (#154)

Additive only; owner-scoped tables with no data.

Revision ID: e4a7c1d9b2f6
Revises: d2b8e6f4a1c3
Create Date: 2026-11-03
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "e4a7c1d9b2f6"
down_revision = "d2b8e6f4a1c3"
branch_labels = None
depends_on = None

UUID = postgresql.UUID(as_uuid=True)
TZ = sa.DateTime(timezone=True)


def upgrade() -> None:
    op.create_table(
        "skydiver_jump_baseline",
        sa.Column(
            "owner_person_id",
            UUID,
            sa.ForeignKey("skydiver_person.id", ondelete="CASCADE"),
            primary_key=True,
        ),
        sa.Column("prior_jumps", sa.Integer(), nullable=False),
        sa.Column("before_on", sa.Date(), nullable=False),
        sa.Column("source", sa.String(16), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False),
        sa.Column("created_at", TZ, nullable=False),
        sa.Column("updated_at", TZ, nullable=False),
        sa.CheckConstraint(
            "prior_jumps BETWEEN 0 AND 100000", name="ck_skydiver_baseline_prior"
        ),
        sa.CheckConstraint("source IN ('manual')", name="ck_skydiver_baseline_source"),
        sa.CheckConstraint("version >= 1", name="ck_skydiver_baseline_version"),
    )
    op.create_table(
        "skydiver_jump_baseline_event",
        sa.Column("id", UUID, primary_key=True),
        sa.Column(
            "owner_person_id",
            UUID,
            sa.ForeignKey("skydiver_person.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("kind", sa.String(16), nullable=False),
        sa.Column("detail", postgresql.JSONB(), nullable=False),
        sa.Column("created_at", TZ, nullable=False),
    )
    op.create_index(
        "ix_skydiver_baseline_event_owner",
        "skydiver_jump_baseline_event",
        ["owner_person_id", "id"],
    )


def downgrade() -> None:
    op.drop_index(
        "ix_skydiver_baseline_event_owner", table_name="skydiver_jump_baseline_event"
    )
    op.drop_table("skydiver_jump_baseline_event")
    op.drop_table("skydiver_jump_baseline")
