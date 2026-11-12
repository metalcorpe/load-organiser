"""Skydiver jumper licence for private currency guidance

Additive only: one new owner-scoped table with no data. The previous code never
reads it; a downgrade drops it (the setting is lost, nothing else).

Revision ID: a3f6c9e2d7b4
Revises: c3e7a9f1d5b2
Create Date: 2026-11-12
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "a3f6c9e2d7b4"
down_revision = "c3e7a9f1d5b2"
branch_labels = None
depends_on = None


def upgrade() -> None:
    op.create_table(
        "skydiver_jumper_licence",
        sa.Column(
            "owner_person_id",
            postgresql.UUID(as_uuid=True),
            sa.ForeignKey("skydiver_person.id", ondelete="CASCADE"),
            primary_key=True,
        ),
        sa.Column("licence", sa.String(8), nullable=False),
        sa.Column("updated_at", sa.DateTime(timezone=True), nullable=False),
        sa.CheckConstraint(
            "licence IN ('student', 'a', 'b', 'c', 'd')",
            name="ck_skydiver_jumper_licence",
        ),
    )


def downgrade() -> None:
    op.drop_table("skydiver_jumper_licence")
