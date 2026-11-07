"""Skydiver erasure ledger (architecture A9)

Records, in the same transaction as the change, the deletions and revocations a
restore from an older backup must re-apply: deleted rows, blocks, and changes to
visibility and account state. Triggers write it, so no application path can skip
it. Entries hold row keys and the changed values only, never notes or other free
text. Operators export it outside the backup set and replay it after a restore
(`python -m app.skydiver.recovery.ledger`). Password replacements are recorded by
the identity store, because a login rehash changes the same column.

The trigger list is fixed here and must match `app.skydiver.recovery.ledger.REPLAY`
(checked by the test suite).

Revision ID: d4f9b6a2e8c1
Revises: c3e8a5f7d1b9
Create Date: 2026-11-07
"""

import sqlalchemy as sa
from alembic import op
from sqlalchemy.dialects import postgresql

revision = "d4f9b6a2e8c1"
down_revision = "c3e8a5f7d1b9"
branch_labels = None
depends_on = None

LEDGER = "skydiver_erasure_ledger"
FUNCTION = "skydiver_erasure_record"

# table: (key columns, columns whose changes are recorded, record inserts)
TRIGGERS: dict[str, tuple[tuple[str, ...], tuple[str, ...], bool]] = {
    "user": (("id",), ("is_active",), False),
    "skydiver_jump": (("id",), (), False),
    "skydiver_jump_post": (("id",), ("audience",), False),
    "skydiver_follow": (("follower_person_id", "followee_person_id"), (), False),
    "skydiver_block": (("blocker_person_id", "blocked_person_id"), (), True),
    "skydiver_profile": (
        ("person_id",),
        ("discoverable", "hidden_at", "publishing_restricted_at"),
        False,
    ),
    "skydiver_component": (("id",), (), False),
    "skydiver_service_entry": (("id",), (), False),
    "skydiver_provisional_place": (("id",), (), False),
    "skydiver_visit_plan": (("id",), (), False),
    "skydiver_saved_opportunity": (("id",), (), False),
    "skydiver_jump_baseline": (("owner_person_id",), (), False),
    "skydiver_role_grant": (("id",), (), False),
}

RECORD = f"""
CREATE FUNCTION {FUNCTION}() RETURNS trigger LANGUAGE plpgsql AS $$
DECLARE
    keys text[] := string_to_array(TG_ARGV[0], ',');
    watched text[] := string_to_array(coalesce(TG_ARGV[1], ''), ',');
    rec jsonb;
    before jsonb;
    row_key jsonb;
    row_values jsonb;
BEGIN
    -- A replay applies entries it already holds; it records nothing new.
    IF current_setting('skydiver.ledger_replay', true) = 'on' THEN
        RETURN NULL;
    END IF;
    IF TG_OP = 'DELETE' THEN
        rec := to_jsonb(OLD);
    ELSE
        rec := to_jsonb(NEW);
    END IF;
    SELECT jsonb_object_agg(k, rec -> k) INTO row_key FROM unnest(keys) AS k;
    IF TG_OP = 'UPDATE' THEN
        before := to_jsonb(OLD);
        SELECT jsonb_object_agg(k, rec -> k) INTO row_values
        FROM unnest(watched) AS k
        WHERE (rec -> k) IS DISTINCT FROM (before -> k);
        IF row_values IS NULL THEN
            RETURN NULL;
        END IF;
    ELSIF TG_OP = 'INSERT' THEN
        row_values := rec;
    END IF;
    INSERT INTO {LEDGER} (action, table_name, row_key, row_values)
    VALUES (lower(TG_OP), TG_TABLE_NAME, row_key, row_values);
    RETURN NULL;
END
$$
"""


def _name(table: str, action: str) -> str:
    return f"skydiver_erasure_{action}_{table}"[:63]


def upgrade() -> None:
    op.create_table(
        LEDGER,
        sa.Column(
            "id",
            postgresql.UUID(as_uuid=True),
            primary_key=True,
            server_default=sa.text("gen_random_uuid()"),
        ),
        sa.Column(
            "recorded_at",
            sa.DateTime(timezone=True),
            nullable=False,
            server_default=sa.text("clock_timestamp()"),
        ),
        sa.Column("action", sa.String(8), nullable=False),
        sa.Column("table_name", sa.String(63), nullable=False),
        sa.Column("row_key", postgresql.JSONB(), nullable=False),
        sa.Column("row_values", postgresql.JSONB(), nullable=True),
        sa.CheckConstraint(
            "action IN ('delete', 'insert', 'update', 'password')",
            name="ck_skydiver_erasure_ledger_action",
        ),
    )
    op.create_index(
        "ix_skydiver_erasure_ledger_recorded", LEDGER, ["recorded_at", "id"]
    )
    op.execute(RECORD)
    for table, (keys, watched, inserts) in TRIGGERS.items():
        args = f"'{','.join(keys)}'"
        op.execute(
            f'CREATE TRIGGER {_name(table, "delete")} AFTER DELETE ON "{table}" '
            f"FOR EACH ROW EXECUTE FUNCTION {FUNCTION}({args})"
        )
        if watched:
            columns = ", ".join(f'"{c}"' for c in watched)
            op.execute(
                f"CREATE TRIGGER {_name(table, 'update')} AFTER UPDATE OF {columns} "
                f'ON "{table}" FOR EACH ROW '
                f"EXECUTE FUNCTION {FUNCTION}({args}, '{','.join(watched)}')"
            )
        if inserts:
            op.execute(
                f'CREATE TRIGGER {_name(table, "insert")} AFTER INSERT ON "{table}" '
                f"FOR EACH ROW EXECUTE FUNCTION {FUNCTION}({args})"
            )


def downgrade() -> None:
    for table, (_, watched, inserts) in TRIGGERS.items():
        actions = ["delete"] + (["update"] if watched else []) + (["insert"] if inserts else [])  # fmt: skip
        for action in actions:
            op.execute(f'DROP TRIGGER {_name(table, action)} ON "{table}"')
    op.execute(f"DROP FUNCTION {FUNCTION}()")
    op.drop_index("ix_skydiver_erasure_ledger_recorded", table_name=LEDGER)
    op.drop_table("skydiver_erasure_ledger")
