"""Erasure ledger: export it, prune it, and replay it after a restore (architecture A9).

A backup is the database at one moment. Restoring it brings back what was deleted
or revoked afterwards. Triggers record those changes in `skydiver_erasure_ledger`
in the same transaction (migration d4f9b6a2e8c1). The ledger is part of the
database, so a restore also rolls it back: operators export it regularly to storage
outside the backup set and replay the exported copies against the restored database
before it serves anyone.

    python -m app.skydiver.recovery.ledger export FILE
    python -m app.skydiver.recovery.ledger prune DAYS
    python -m app.skydiver.recovery.ledger apply [FILE ...]

`apply` runs in one transaction. It applies the entries of the given files and of
the restored database in recording order, adds the missing entries back to the
restored ledger, then revokes every session and deletes every unused email or
reset token, so that nothing issued before the restore is accepted again.
The database comes from the usual POSTGRES_* environment.
"""

import json
import os
import secrets
import sys
import uuid
from collections.abc import Iterable, Sequence
from dataclasses import dataclass, field
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any

from sqlalchemy import Connection, Engine, text
from sqlalchemy.exc import IntegrityError

from app.core.security import get_password_hash

LEDGER = "skydiver_erasure_ledger"
ACTIONS = frozenset({"delete", "insert", "update", "password"})


@dataclass(frozen=True)
class Replay:
    """How entries for one table are applied. Only these tables and columns are."""

    keys: tuple[str, ...]
    watched: tuple[str, ...] = ()
    # Columns of a recorded insert (only blocks), named so the replay never relies
    # on the table's current column order.
    inserts: tuple[str, ...] = ()
    # Rows referencing a deleted row that the deletion proves were gone: (table, column).
    detach: tuple[tuple[str, str], ...] = ()


# Must match the triggers of migration d4f9b6a2e8c1 (checked by the tests).
REPLAY: dict[str, Replay] = {
    "user": Replay(("id",), ("is_active",)),
    "skydiver_jump": Replay(("id",)),
    "skydiver_jump_post": Replay(("id",), ("audience",)),
    "skydiver_follow": Replay(("follower_person_id", "followee_person_id")),
    "skydiver_block": Replay(
        ("blocker_person_id", "blocked_person_id"),
        inserts=("blocker_person_id", "blocked_person_id", "created_at"),
    ),
    "skydiver_profile": Replay(
        ("person_id",), ("discoverable", "hidden_at", "publishing_restricted_at")
    ),
    # A component can only be deleted once no jump uses it, so links that the
    # restored copy still has were removed after the backup too.
    "skydiver_component": Replay(
        ("id",), detach=(("skydiver_jump_component", "component_id"),)
    ),
    "skydiver_service_entry": Replay(("id",)),
    # Not detached: a jump needs its place, and its later location is unknown here.
    # A restored jump still at a place deleted afterwards leaves that entry skipped.
    "skydiver_provisional_place": Replay(("id",)),
    "skydiver_visit_plan": Replay(("id",)),
    "skydiver_saved_opportunity": Replay(("id",)),
    "skydiver_jump_baseline": Replay(("owner_person_id",)),
    "skydiver_role_grant": Replay(("id",)),
}


class LedgerError(ValueError):
    """An entry that is not one this version can apply."""


@dataclass(frozen=True)
class Entry:
    id: uuid.UUID
    recorded_at: datetime
    action: str
    table: str
    key: dict[str, Any]
    values: dict[str, Any] | None

    @classmethod
    def parse(cls, raw: dict[str, Any]) -> Entry:
        try:
            entry = cls(
                id=uuid.UUID(str(raw["id"])),
                recorded_at=datetime.fromisoformat(str(raw["recorded_at"])),
                action=str(raw["action"]),
                table=str(raw["table"]),
                key=dict(raw["key"]),
                values=None if raw.get("values") is None else dict(raw["values"]),
            )
        except (KeyError, TypeError, ValueError) as error:
            raise LedgerError(f"malformed entry: {raw!r}") from error
        entry.check()
        return entry

    def check(self) -> None:
        """Refuse anything outside REPLAY: file contents never name SQL."""
        spec = REPLAY.get(self.table)
        if self.action not in ACTIONS or spec is None:
            raise LedgerError(f"unknown entry {self.action} {self.table} ({self.id})")
        if self.recorded_at.tzinfo is None:
            raise LedgerError(f"entry without a time zone ({self.id})")
        if set(self.key) != set(spec.keys):
            raise LedgerError(f"wrong key for {self.table} ({self.id})")
        if self.action == "update" and (
            not self.values or not set(self.values) <= set(spec.watched)
        ):
            raise LedgerError(f"unexpected update of {self.table} ({self.id})")
        if self.action == "insert" and (
            not spec.inserts or set(self.values or {}) != set(spec.inserts)
        ):
            raise LedgerError(f"unexpected insert into {self.table} ({self.id})")
        if self.action == "password" and self.table != "user":
            raise LedgerError(f"unexpected password entry ({self.id})")

    def as_json(self) -> dict[str, Any]:
        return {
            "id": str(self.id),
            "recorded_at": self.recorded_at.isoformat(),
            "action": self.action,
            "table": self.table,
            "key": self.key,
            "values": self.values,
        }


def _quote(name: str) -> str:
    return '"' + name.replace('"', '""') + '"'


def stored(conn: Connection) -> list[Entry]:
    rows = conn.execute(
        text(
            f"SELECT id, recorded_at, action, table_name, row_key, row_values "  # noqa: S608
            f"FROM {LEDGER} ORDER BY recorded_at, id"
        )
    ).all()
    return [
        Entry.parse(
            {
                "id": r[0],
                "recorded_at": r[1].isoformat(),
                "action": r[2],
                "table": r[3],
                "key": r[4],
                "values": r[5],
            }
        )
        for r in rows
    ]


def read(path: Path) -> list[Entry]:
    entries = []
    for number, line in enumerate(path.read_text().splitlines(), start=1):
        if not line.strip():
            continue
        try:
            raw = json.loads(line)
        except json.JSONDecodeError as error:
            raise LedgerError(f"{path}:{number}: not JSON") from error
        entries.append(Entry.parse(raw))
    return entries


def export(engine: Engine, path: Path) -> int:
    """Write every entry, one JSON object per line, replacing `path` atomically."""
    with engine.connect() as conn:
        entries = stored(conn)
    partial = path.with_name(path.name + ".partial")
    with partial.open("w") as out:
        for entry in entries:
            out.write(json.dumps(entry.as_json(), sort_keys=True) + "\n")
        out.flush()
        os.fsync(out.fileno())
    partial.replace(path)
    return len(entries)


def prune(engine: Engine, days: int, now: datetime | None = None) -> int:
    """Drop entries older than `days`; keep them longer than the oldest backup."""
    if days < 1:
        raise LedgerError("keep at least one day")
    cutoff = (now or datetime.now(UTC)) - timedelta(days=days)
    with engine.begin() as conn:
        result = conn.execute(
            text(f"DELETE FROM {LEDGER} WHERE recorded_at < :cutoff"),  # noqa: S608
            {"cutoff": cutoff},
        )
    return int(result.rowcount)


@dataclass
class Outcome:
    entries: int = 0
    in_backup: int = 0
    before_backup: int = 0
    restored_ledger_empty: bool = False
    changed: int = 0
    # Already as recorded, e.g. rows a cascade removed with an earlier entry.
    unchanged: int = 0
    by_kind: dict[str, list[int]] = field(default_factory=dict)  # [changed, unchanged]
    skipped: list[str] = field(default_factory=list)
    restored_entries: int = 0
    sessions_revoked: int = 0
    tokens_deleted: int = 0

    def as_json(self) -> dict[str, Any]:
        return self.__dict__.copy()


def _where(spec: Replay, alias: str) -> str:
    return " AND ".join(f"{alias}.{_quote(k)} = r.{_quote(k)}" for k in spec.keys)


def _apply_one(conn: Connection, entry: Entry) -> int:
    spec = REPLAY[entry.table]
    table = _quote(entry.table)
    record = f"jsonb_populate_record(NULL::{table}, CAST(:row AS jsonb)) AS r"
    if entry.action == "delete":
        row = json.dumps(entry.key)
        for child, column in spec.detach:
            conn.execute(
                text(
                    f"DELETE FROM {_quote(child)} c WHERE c.{_quote(column)} = "  # noqa: S608
                    f"(SELECT r.id FROM {record})"
                ),
                {"row": row},
            )
        result = conn.execute(
            text(f"DELETE FROM {table} t USING {record} WHERE {_where(spec, 't')}"),  # noqa: S608
            {"row": row},
        )
    elif entry.action == "update":
        assert entry.values is not None
        row = json.dumps({**entry.values, **entry.key})
        columns = ", ".join(f"{_quote(c)} = r.{_quote(c)}" for c in entry.values)
        differs = " OR ".join(
            f"t.{_quote(c)} IS DISTINCT FROM r.{_quote(c)}" for c in entry.values
        )
        result = conn.execute(
            text(
                f"UPDATE {table} t SET {columns} FROM {record} "  # noqa: S608
                f"WHERE {_where(spec, 't')} AND ({differs})"
            ),
            {"row": row},
        )
    elif entry.action == "insert":
        columns = ", ".join(_quote(c) for c in spec.inserts)
        picked = ", ".join(f"r.{_quote(c)}" for c in spec.inserts)
        result = conn.execute(
            text(
                f"INSERT INTO {table} ({columns}) SELECT {picked} FROM {record} "  # noqa: S608
                "ON CONFLICT DO NOTHING"
            ),
            {"row": json.dumps(entry.values)},
        )
    else:  # password: the password set after the backup is unknown here.
        result = conn.execute(
            text('UPDATE "user" SET hashed_password = :hash WHERE id = :id'),
            {
                "hash": get_password_hash(secrets.token_urlsafe(32)),
                "id": entry.key["id"],
            },
        )
    return int(result.rowcount)


def apply(
    engine: Engine, files: Sequence[Path], now: datetime | None = None
) -> Outcome:
    """Replay the ledger onto a restored database in one transaction."""
    outcome = Outcome()
    loaded: list[Entry] = [e for path in files for e in read(path)]
    with engine.begin() as conn:
        conn.execute(text("SET LOCAL skydiver.ledger_replay = 'on'"))
        restored = stored(conn)
        held = {e.id for e in restored}
        # Entries older than the oldest one the backup holds were pruned before it
        # was taken; their changes are in it already.
        horizon = restored[0].recorded_at if restored else None
        outcome.restored_ledger_empty = horizon is None
        entries = _merge([*restored, *loaded])
        outcome.entries = len(entries)
        for entry in entries:
            if entry.id in held:
                # Written in the same transaction as its change, so the backup holds
                # the result already. Re-applying could undo a later change that
                # reuses the key (a new follow) or lock out a password set since.
                outcome.in_backup += 1
                continue
            if horizon is not None and entry.recorded_at < horizon:
                outcome.before_backup += 1
                continue
            conn.execute(
                text(
                    f"INSERT INTO {LEDGER} (id, recorded_at, action, table_name, "  # noqa: S608
                    "row_key, row_values) VALUES (:id, :at, :action, :table, "
                    "CAST(:key AS jsonb), CAST(:values AS jsonb))"
                ),
                {
                    "id": entry.id,
                    "at": entry.recorded_at,
                    "action": entry.action,
                    "table": entry.table,
                    "key": json.dumps(entry.key),
                    "values": None
                    if entry.values is None
                    else json.dumps(entry.values),
                },
            )
            outcome.restored_entries += 1
            savepoint = conn.begin_nested()
            try:
                changed = _apply_one(conn, entry)
            except IntegrityError as error:
                # A block between people who no longer both exist, for example.
                savepoint.rollback()
                code = getattr(error.orig, "sqlstate", "?")
                outcome.skipped.append(
                    f"{entry.id} {entry.action} {entry.table}: {code}"
                )
                continue
            savepoint.commit()
            tally = outcome.by_kind.setdefault(f"{entry.action} {entry.table}", [0, 0])
            if changed:
                outcome.changed += 1
                tally[0] += 1
            else:
                outcome.unchanged += 1
                tally[1] += 1
        stamp = now or datetime.now(UTC)
        outcome.sessions_revoked = int(
            conn.execute(
                text(
                    "UPDATE skydiver_session SET revoked_at = :now, "
                    "revoke_reason = 'restore' WHERE revoked_at IS NULL"
                ),
                {"now": stamp},
            ).rowcount
        )
        outcome.tokens_deleted = int(
            conn.execute(text("DELETE FROM skydiver_account_token")).rowcount
        )
    return outcome


def _merge(entries: Iterable[Entry]) -> list[Entry]:
    unique: dict[uuid.UUID, Entry] = {}
    for entry in entries:
        known = unique.get(entry.id)
        if known is not None and known != entry:
            raise LedgerError(f"entry {entry.id} differs between copies")
        unique[entry.id] = entry
    return sorted(unique.values(), key=lambda e: (e.recorded_at, str(e.id)))


def main(argv: list[str]) -> None:
    from app.core.db import engine

    command, args = (argv[1], argv[2:]) if len(argv) > 1 else ("", [])
    if command == "export" and len(args) == 1:
        print(json.dumps({"exported": export(engine, Path(args[0]))}))
    elif command == "prune" and len(args) == 1:
        print(json.dumps({"pruned": prune(engine, int(args[0]))}))
    elif command == "apply":
        outcome = apply(engine, [Path(a) for a in args])
        print(json.dumps(outcome.as_json(), indent=1))
        if outcome.skipped:
            # Committed, but someone has to look at what could not be applied.
            raise SystemExit(1)
    else:
        raise SystemExit(__doc__)


if __name__ == "__main__":
    main(sys.argv)
