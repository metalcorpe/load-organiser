"""Skydiver published jump summaries and post reports (#157)

Additive: a new table with no data, and a report column defaulting to '' (a
profile report) so existing reports keep their meaning.

Revision ID: b7d1f4a2c9e5
Revises: a6c9e3f1d2b8
Create Date: 2026-11-06
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "b7d1f4a2c9e5"
down_revision = "a6c9e3f1d2b8"
branch_labels = None
depends_on = None

UUID = postgresql.UUID(as_uuid=True)
TZ = sa.DateTime(timezone=True)
REPORT = "skydiver_social_report"


def upgrade() -> None:
    op.create_table(
        "skydiver_jump_post",
        sa.Column("id", UUID, primary_key=True),
        sa.Column(
            "owner_person_id",
            UUID,
            sa.ForeignKey("skydiver_person.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column(
            "jump_id",
            UUID,
            sa.ForeignKey("skydiver_jump.id", ondelete="CASCADE"),
            nullable=False,
            unique=True,
        ),
        sa.Column("source_version", sa.Integer(), nullable=False),
        sa.Column("audience", sa.String(16), nullable=False),
        sa.Column("jumped_on", sa.Date(), nullable=False),
        sa.Column("jump_type", sa.String(16), nullable=True),
        sa.Column("venue_id", UUID, sa.ForeignKey("skydiver_venue.id"), nullable=True),
        sa.Column("exit_altitude", sa.Integer(), nullable=True),
        sa.Column("altitude_unit", sa.String(2), nullable=True),
        sa.Column("altitude_datum", sa.String(12), nullable=True),
        sa.Column("freefall_seconds", sa.Integer(), nullable=True),
        sa.Column("caption", sa.Text(), nullable=True),
        sa.Column("link", sa.String(2048), nullable=True),
        sa.Column("version", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("published_at", TZ, nullable=False),
        sa.Column("updated_at", TZ, nullable=False),
        sa.CheckConstraint(
            "audience IN ('followers', 'public')", name="ck_skydiver_jump_post_audience"
        ),
        sa.CheckConstraint(
            "(exit_altitude IS NULL) = (altitude_unit IS NULL)"
            " AND (exit_altitude IS NULL) = (altitude_datum IS NULL)",
            name="ck_skydiver_jump_post_altitude",
        ),
        sa.CheckConstraint(
            "caption IS NULL OR length(caption) <= 280",
            name="ck_skydiver_jump_post_caption",
        ),
        sa.CheckConstraint("version >= 1", name="ck_skydiver_jump_post_version"),
    )
    op.create_index(
        "ix_skydiver_jump_post_owner", "skydiver_jump_post", ["owner_person_id", "id"]
    )

    op.add_column(
        REPORT,
        sa.Column("post_key", sa.String(36), nullable=False, server_default=""),
    )
    op.drop_index("uq_skydiver_social_report_open", table_name=REPORT)
    op.create_index(
        "uq_skydiver_social_report_open",
        REPORT,
        ["reporter_person_id", "target_person_id", "post_key"],
        unique=True,
        postgresql_where=sa.text("status = 'open'"),
    )
    op.drop_constraint("ck_skydiver_social_report_decision", REPORT, type_="check")
    op.create_check_constraint(
        "ck_skydiver_social_report_decision",
        REPORT,
        "decision IS NULL OR decision IN "
        "('no_action', 'hide_profile', 'restrict_publishing', 'remove_post')",
    )
    op.create_check_constraint(
        "ck_skydiver_social_report_remove_post",
        REPORT,
        "decision IS DISTINCT FROM 'remove_post' OR post_key <> ''",
    )


def downgrade() -> None:
    # Post reports cannot be expressed in the earlier schema; drop them.
    op.execute("DELETE FROM skydiver_social_report WHERE post_key <> ''")
    op.drop_constraint("ck_skydiver_social_report_remove_post", REPORT, type_="check")
    op.drop_constraint("ck_skydiver_social_report_decision", REPORT, type_="check")
    op.create_check_constraint(
        "ck_skydiver_social_report_decision",
        REPORT,
        "decision IS NULL OR decision IN "
        "('no_action', 'hide_profile', 'restrict_publishing')",
    )
    op.drop_index("uq_skydiver_social_report_open", table_name=REPORT)
    op.create_index(
        "uq_skydiver_social_report_open",
        REPORT,
        ["reporter_person_id", "target_person_id"],
        unique=True,
        postgresql_where=sa.text("status = 'open'"),
    )
    op.drop_column(REPORT, "post_key")
    op.drop_index("ix_skydiver_jump_post_owner", table_name="skydiver_jump_post")
    op.drop_table("skydiver_jump_post")
