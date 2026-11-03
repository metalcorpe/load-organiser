"""Skydiver directory: venues, aliases, history and provisional places (#148)

Additive only. No venue data is inserted: listings come from reviewed sources.

Revision ID: 2f7a9c4e1b38
Revises: 8c3d1f6b2a70
Create Date: 2026-11-03
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "2f7a9c4e1b38"
down_revision = "8c3d1f6b2a70"
branch_labels = None
depends_on = None

UUID = postgresql.UUID(as_uuid=True)
TZ = sa.DateTime(timezone=True)


def upgrade() -> None:
    op.create_table(
        "skydiver_venue",
        sa.Column("id", UUID, primary_key=True),
        sa.Column("name", sa.String(120), nullable=False),
        sa.Column("name_key", sa.Text(), nullable=False),
        sa.Column("country", sa.String(2), nullable=False),
        sa.Column("locality", sa.String(120), nullable=True),
        sa.Column("latitude", sa.Numeric(9, 6), nullable=True),
        sa.Column("longitude", sa.Numeric(9, 6), nullable=True),
        sa.Column("status", sa.String(16), nullable=False),
        sa.Column(
            "merged_into_id", UUID, sa.ForeignKey("skydiver_venue.id"), nullable=True
        ),
        sa.Column("source_url", sa.String(2048), nullable=True),
        sa.Column("source_note", sa.String(280), nullable=True),
        sa.Column("checked_on", sa.Date(), nullable=True),
        sa.Column("created_at", TZ, nullable=False),
        sa.Column("updated_at", TZ, nullable=False),
        sa.CheckConstraint(
            "status IN ('draft', 'listed', 'closed', 'merged')",
            name="skydiver_venue_status",
        ),
        sa.CheckConstraint(
            "(status = 'merged') = (merged_into_id IS NOT NULL)",
            name="skydiver_venue_merge_target",
        ),
        sa.CheckConstraint(
            "status = 'draft' OR (source_url IS NOT NULL AND checked_on IS NOT NULL)",
            name="skydiver_venue_source_backed",
        ),
        sa.CheckConstraint(
            "(latitude IS NULL) = (longitude IS NULL)",
            name="skydiver_venue_coordinates_pair",
        ),
        sa.CheckConstraint("merged_into_id <> id", name="skydiver_venue_not_self"),
    )
    op.create_index(
        "ix_skydiver_venue_search", "skydiver_venue", ["status", "name_key", "id"]
    )
    op.create_table(
        "skydiver_venue_alias",
        sa.Column("id", UUID, primary_key=True),
        sa.Column(
            "venue_id",
            UUID,
            sa.ForeignKey("skydiver_venue.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("alias", sa.String(120), nullable=False),
        sa.Column("alias_key", sa.Text(), nullable=False),
        sa.Column("kind", sa.String(16), nullable=False),
        sa.Column("created_at", TZ, nullable=False),
        sa.CheckConstraint(
            "kind IN ('alternate', 'former', 'merged')",
            name="skydiver_venue_alias_kind",
        ),
        sa.UniqueConstraint("venue_id", "alias_key", name="uq_skydiver_venue_alias"),
    )
    op.create_index(
        "ix_skydiver_venue_alias_key", "skydiver_venue_alias", ["alias_key"]
    )
    op.create_table(
        "skydiver_venue_event",
        sa.Column("id", UUID, primary_key=True),
        sa.Column(
            "venue_id",
            UUID,
            sa.ForeignKey("skydiver_venue.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column("kind", sa.String(24), nullable=False),
        sa.Column("detail", postgresql.JSONB(), nullable=False),
        sa.Column(
            "actor_account_id",
            UUID,
            sa.ForeignKey("user.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("created_at", TZ, nullable=False),
    )
    op.create_table(
        "skydiver_provisional_place",
        sa.Column("id", UUID, primary_key=True),
        sa.Column(
            "owner_person_id",
            UUID,
            sa.ForeignKey("skydiver_person.id", ondelete="CASCADE"),
            nullable=False,
            index=True,
        ),
        sa.Column("name", sa.String(120), nullable=False),
        sa.Column("country", sa.String(2), nullable=False),
        sa.Column(
            "venue_id", UUID, sa.ForeignKey("skydiver_venue.id"), nullable=True
        ),
        sa.Column("created_at", TZ, nullable=False),
        sa.Column("updated_at", TZ, nullable=False),
    )


def downgrade() -> None:
    op.drop_table("skydiver_provisional_place")
    op.drop_table("skydiver_venue_event")
    op.drop_index("ix_skydiver_venue_alias_key", table_name="skydiver_venue_alias")
    op.drop_table("skydiver_venue_alias")
    op.drop_index("ix_skydiver_venue_search", table_name="skydiver_venue")
    op.drop_table("skydiver_venue")
