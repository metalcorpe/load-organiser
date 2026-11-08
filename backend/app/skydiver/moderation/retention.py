"""Retention of submissions kept after their author's account was deleted (#162).

Account deletion keeps suggestions, corrections and feedback without their author
(architecture: minimal case evidence with a 30-day retention target). This deletes
them once that period has passed, reviewed or not. Run it from the same scheduler
as the backups:

    python -m app.skydiver.moderation.retention purge [DAYS]

DAYS defaults to 30 and must be at least 1. Prints {"purged": N}.
"""

import json
import sys
from datetime import UTC, datetime, timedelta

from sqlalchemy import Engine, text

DEFAULT_DAYS = 30


class RetentionError(ValueError):
    pass


def purge(engine: Engine, days: int = DEFAULT_DAYS, now: datetime | None = None) -> int:
    """Delete submissions whose author was removed more than `days` ago."""
    if days < 1:
        raise RetentionError("keep at least one day")
    cutoff = (now or datetime.now(UTC)) - timedelta(days=days)
    with engine.begin() as conn:
        result = conn.execute(
            text(
                "DELETE FROM skydiver_submission "
                "WHERE author_removed_at IS NOT NULL AND author_removed_at < :cutoff"
            ),
            {"cutoff": cutoff},
        )
    return int(result.rowcount)


def main(argv: list[str]) -> None:
    from app.core.db import engine

    args = argv[1:]
    if args[:1] == ["purge"] and len(args) <= 2:
        try:
            days = int(args[1]) if len(args) == 2 else DEFAULT_DAYS
            print(json.dumps({"purged": purge(engine, days)}))
        except (ValueError, RetentionError) as error:
            raise SystemExit(f"purge: {error}") from None
    else:
        raise SystemExit(__doc__)


if __name__ == "__main__":
    main(sys.argv)
