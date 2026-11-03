"""Skydiver private jump logbook: jumps, equipment used, receipts, history (#153)

Additive only; owner-scoped tables with no data. Not the prototype operational
jump/load tables.

Revision ID: d2b8e6f4a1c3
Revises: c7f1a2d9e3b5
Create Date: 2026-11-03
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "d2b8e6f4a1c3"
down_revision = "c7f1a2d9e3b5"
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
        "skydiver_jump",
        sa.Column("id", UUID, primary_key=True),
        _owner(),
        sa.Column("jumped_on", sa.Date(), nullable=False),
        sa.Column(
            "venue_id",
            UUID,
            sa.ForeignKey("skydiver_venue.id"),
            nullable=True,
            index=True,
        ),
        sa.Column(
            "place_id",
            UUID,
            sa.ForeignKey("skydiver_provisional_place.id"),
            nullable=True,
            index=True,
        ),
        sa.Column("jump_type", sa.String(16), nullable=False),
        sa.Column("jump_number", sa.Integer(), nullable=True),
        sa.Column("exit_time", sa.Time(), nullable=True),
        sa.Column("time_zone", sa.String(64), nullable=True),
        sa.Column("exit_altitude", sa.Integer(), nullable=True),
        sa.Column("deployment_altitude", sa.Integer(), nullable=True),
        sa.Column("altitude_unit", sa.String(2), nullable=True),
        sa.Column("altitude_datum", sa.String(12), nullable=False),
        sa.Column("freefall_seconds", sa.Integer(), nullable=True),
        sa.Column("other_gear", sa.String(200), nullable=True),
        sa.Column("notes", sa.Text(), nullable=True),
        sa.Column("links", postgresql.JSONB(), nullable=False),
        sa.Column("source", sa.String(16), nullable=False),
        sa.Column("version", sa.Integer(), nullable=False, server_default="1"),
        sa.Column("created_at", TZ, nullable=False),
        sa.Column("updated_at", TZ, nullable=False),
        sa.CheckConstraint(
            "(CASE WHEN venue_id IS NULL THEN 0 ELSE 1 END"
            " + CASE WHEN place_id IS NULL THEN 0 ELSE 1 END) = 1",
            name="ck_skydiver_jump_one_location",
        ),
        sa.CheckConstraint(
            "jump_type IN ('unspecified', 'belly', 'freefly', 'angle', 'wingsuit',"
            " 'canopy', 'crw', 'accuracy', 'hop_and_pop', 'tandem', 'training',"
            " 'other')",
            name="ck_skydiver_jump_type",
        ),
        sa.CheckConstraint(
            "jump_number IS NULL OR jump_number > 0", name="ck_skydiver_jump_number"
        ),
        sa.CheckConstraint(
            "(exit_time IS NULL) = (time_zone IS NULL)",
            name="ck_skydiver_jump_time_zone",
        ),
        sa.CheckConstraint(
            "altitude_unit IS NULL OR altitude_unit IN ('ft', 'm')",
            name="ck_skydiver_jump_altitude_unit",
        ),
        sa.CheckConstraint(
            "(exit_altitude IS NULL AND deployment_altitude IS NULL)"
            " = (altitude_unit IS NULL)",
            name="ck_skydiver_jump_altitude_has_unit",
        ),
        sa.CheckConstraint(
            "altitude_datum IN ('unspecified', 'agl', 'msl')",
            name="ck_skydiver_jump_altitude_datum",
        ),
        sa.CheckConstraint(
            "freefall_seconds IS NULL OR freefall_seconds >= 0",
            name="ck_skydiver_jump_freefall",
        ),
        sa.CheckConstraint("source IN ('manual')", name="ck_skydiver_jump_source"),
    )
    op.create_index(
        "ix_skydiver_jump_owner_date",
        "skydiver_jump",
        ["owner_person_id", "jumped_on", "id"],
    )
    op.create_index(
        "ix_skydiver_jump_owner_number",
        "skydiver_jump",
        ["owner_person_id", "jump_number"],
    )
    op.create_table(
        "skydiver_jump_component",
        sa.Column(
            "jump_id",
            UUID,
            sa.ForeignKey("skydiver_jump.id", ondelete="CASCADE"),
            primary_key=True,
        ),
        sa.Column(
            "component_id",
            UUID,
            sa.ForeignKey("skydiver_component.id"),
            primary_key=True,
        ),
        _owner(),
    )
    op.create_index(
        "ix_skydiver_jump_component_component",
        "skydiver_jump_component",
        ["component_id"],
    )
    op.create_table(
        "skydiver_jump_receipt",
        sa.Column("id", UUID, primary_key=True),
        _owner(),
        sa.Column("client_key", UUID, nullable=False),
        sa.Column("fingerprint", sa.String(64), nullable=False),
        sa.Column(
            "jump_id",
            UUID,
            sa.ForeignKey("skydiver_jump.id", ondelete="SET NULL"),
            nullable=True,
        ),
        sa.Column("created_at", TZ, nullable=False),
        sa.UniqueConstraint(
            "owner_person_id", "client_key", name="uq_skydiver_jump_receipt_key"
        ),
    )
    op.create_table(
        "skydiver_jump_event",
        sa.Column("id", UUID, primary_key=True),
        _owner(),
        sa.Column(
            "jump_id",
            UUID,
            sa.ForeignKey("skydiver_jump.id", ondelete="CASCADE"),
            nullable=False,
        ),
        sa.Column("kind", sa.String(32), nullable=False),
        sa.Column("detail", postgresql.JSONB(), nullable=False),
        sa.Column("created_at", TZ, nullable=False),
    )
    op.create_index(
        "ix_skydiver_jump_event_jump", "skydiver_jump_event", ["jump_id", "id"]
    )


def downgrade() -> None:
    op.drop_table("skydiver_jump_event")
    op.drop_table("skydiver_jump_receipt")
    op.drop_table("skydiver_jump_component")
    op.drop_table("skydiver_jump")
