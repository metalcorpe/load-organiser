"""Skydiver private saved opportunities and visit plans (#150)

Additive only; owner-scoped tables with no data.

Revision ID: 7e4c2b9d1a53
Revises: 2d5befa4f070
Create Date: 2026-11-03
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "7e4c2b9d1a53"
down_revision = "2d5befa4f070"
branch_labels = None
depends_on = None

UUID = postgresql.UUID(as_uuid=True)
TZ = sa.DateTime(timezone=True)


def _owner() -> sa.Column:  # type: ignore[type-arg]
    return sa.Column(
        "owner_person_id",
        UUID,
        sa.ForeignKey("skydiver_person.id", ondelete="CASCADE"),
        nullable=False,
        index=True,
    )


def upgrade() -> None:
    op.create_table(
        "skydiver_saved_opportunity",
        sa.Column("id", UUID, primary_key=True),
        _owner(),
        sa.Column(
            "opportunity_id",
            UUID,
            sa.ForeignKey("skydiver_opportunity.id"),
            nullable=False,
        ),
        sa.Column("title", sa.String(200), nullable=False),
        sa.Column("created_at", TZ, nullable=False),
        sa.UniqueConstraint(
            "owner_person_id", "opportunity_id", name="uq_skydiver_saved_opportunity"
        ),
    )
    op.create_table(
        "skydiver_visit_plan",
        sa.Column("id", UUID, primary_key=True),
        _owner(),
        sa.Column("title", sa.String(120), nullable=False),
        sa.Column("starts_on", sa.Date(), nullable=False),
        sa.Column("ends_on", sa.Date(), nullable=False),
        sa.Column("note", sa.String(500), nullable=True),
        sa.Column(
            "opportunity_id",
            UUID,
            sa.ForeignKey("skydiver_opportunity.id"),
            nullable=True,
        ),
        sa.Column("venue_id", UUID, sa.ForeignKey("skydiver_venue.id"), nullable=True),
        sa.Column(
            "place_id",
            UUID,
            sa.ForeignKey("skydiver_provisional_place.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("created_at", TZ, nullable=False),
        sa.Column("updated_at", TZ, nullable=False),
        sa.CheckConstraint("ends_on >= starts_on", name="ck_skydiver_visit_plan_dates"),
        sa.CheckConstraint(
            "(CASE WHEN opportunity_id IS NULL THEN 0 ELSE 1 END"
            " + CASE WHEN venue_id IS NULL THEN 0 ELSE 1 END"
            " + CASE WHEN place_id IS NULL THEN 0 ELSE 1 END) <= 1",
            name="ck_skydiver_visit_plan_one_link",
        ),
    )


def downgrade() -> None:
    op.drop_table("skydiver_visit_plan")
    op.drop_table("skydiver_saved_opportunity")
