"""Skydiver submission retention after account deletion (#162)

Deleting an account keeps its submissions without their author (the person FK is
ON DELETE SET NULL). `author_removed_at` records when that happened, set by a
trigger so every deletion path is covered, and
`python -m app.skydiver.moderation.retention purge` deletes such submissions after
the architecture's 30-day target. Rows already without an author get the migration
time, so none is purged earlier than 30 days from now.

Revision ID: a8d2f6c4e1b7
Revises: f1c4e8a6b3d2
Create Date: 2026-11-08
"""

import sqlalchemy as sa
from alembic import op

revision = "a8d2f6c4e1b7"
down_revision = "f1c4e8a6b3d2"
branch_labels = None
depends_on = None

TABLE = "skydiver_submission"
COLUMN = "author_removed_at"
CHECK = "ck_skydiver_submission_author_removed"
INDEX = "ix_skydiver_submission_author_removed"


def upgrade() -> None:
    op.add_column(TABLE, sa.Column(COLUMN, sa.DateTime(timezone=True), nullable=True))
    op.execute(
        "UPDATE skydiver_submission SET author_removed_at = now() "
        "WHERE submitter_person_id IS NULL"
    )
    op.create_check_constraint(
        CHECK, TABLE, "(author_removed_at IS NULL) = (submitter_person_id IS NOT NULL)"
    )
    op.create_index(
        INDEX,
        TABLE,
        [COLUMN],
        postgresql_where=sa.text("author_removed_at IS NOT NULL"),
    )
    op.execute(
        """
        CREATE FUNCTION skydiver_submission_author_removed() RETURNS trigger
        LANGUAGE plpgsql AS $$
        BEGIN
            IF NEW.submitter_person_id IS NULL AND OLD.submitter_person_id IS NOT NULL THEN
                NEW.author_removed_at := now();
            END IF;
            RETURN NEW;
        END
        $$
        """
    )
    op.execute(
        "CREATE TRIGGER skydiver_submission_author_removed "
        "BEFORE UPDATE OF submitter_person_id ON skydiver_submission "
        "FOR EACH ROW EXECUTE FUNCTION skydiver_submission_author_removed()"
    )


def downgrade() -> None:
    op.execute("DROP TRIGGER skydiver_submission_author_removed ON skydiver_submission")
    op.execute("DROP FUNCTION skydiver_submission_author_removed()")
    op.drop_index(INDEX, TABLE)
    op.drop_constraint(CHECK, TABLE, type_="check")
    op.drop_column(TABLE, COLUMN)
