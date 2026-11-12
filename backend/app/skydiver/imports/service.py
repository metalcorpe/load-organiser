"""Logbook import from a spreadsheet (owner decision 2026-11-12). Owner-only.

Check and import run the same steps; check writes nothing.

1. Read the file and choose its columns (policy). The fingerprint covers the exact
   bytes and the canonical options and columns.
2. Each row becomes a draft jump or a problem. A place name is, in order: the
   exact (case-insensitive) name or alias of one listed dropzone, the name of one
   of the person's private places, or a new private place in the chosen country.
3. A row repeating an existing jump (same number; or no number and the same core
   facts the logbook's duplicate warning uses) is skipped as `likely_duplicate`;
   a number repeated inside the file skips the later row as `repeated_in_file`.
4. Import writes in one transaction: the import row, new places, jumps (source
   `imported`) and one `created` event per jump. The import row first claims the
   person's next import sequence (read before anything is counted) and the file's
   fingerprint, both unique per person: of two simultaneous imports only one can
   commit, and the other starts again on what the first wrote, so the same file
   twice answers "already imported" without writing. The limits are counted
   behind the per-person gate (`lock_owner`) that manual place and jump creation
   take too, so neither a second import nor a hand-made place or jump can pass
   the same check at the same time.
5. Undo removes every jump still linked to the import (edited or not) and the
   places it created that nothing uses any more, once: the undo time is set only
   where it is still empty.
"""

import uuid
from collections.abc import Callable
from contextlib import AbstractContextManager
from dataclasses import dataclass
from datetime import date, datetime, timedelta
from typing import Any, Protocol

from app.skydiver.access.policy import Actor
from app.skydiver.directory.service import MAX_PLACES_PER_PERSON
from app.skydiver.imports import policy
from app.skydiver.imports.policy import Draft, ImportRefused, Options, Problem, Table
from app.skydiver.logbook.policy import MAX_JUMPS

ATTEMPTS = 3
LIST_MAX = 50


class NotFound(Exception):
    """Absent and another person's import alike."""


class LimitReached(Exception):
    code = "jump_limit_reached"


class PlaceLimitReached(Exception):
    code = "place_limit_reached"


class AlreadyUndone(Exception):
    code = "already_undone"


class ImportChanged(Exception):
    """The file, options or columns differ from the ones the person checked."""

    code = "import_changed"


class ImportBusy(Exception):
    """Lost every attempt to concurrent imports; nothing was written."""

    code = "import_busy"


@dataclass(frozen=True)
class VenueName:
    id: uuid.UUID
    country: str
    names: tuple[str, ...]  # current name and aliases


@dataclass(frozen=True)
class PlaceName:
    id: uuid.UUID
    name: str


@dataclass(frozen=True)
class Existing:
    numbers: frozenset[int]
    cores: frozenset[tuple[Any, ...]]  # facts of jumps without a number


@dataclass(frozen=True)
class ImportRecord:
    id: uuid.UUID
    created_at: datetime
    counts: dict[str, int]
    undone_at: datetime | None
    place_ids: tuple[uuid.UUID, ...] = ()


@dataclass(frozen=True)
class SampleRow:
    row: int
    jumped_on: date
    jump_number: int | None
    place: str
    place_kind: str  # venue | place | new_place
    jump_type: str
    exit_altitude: int | None
    altitude_unit: str | None
    freefall_seconds: int | None
    notes: str | None
    aircraft: str | None = None


@dataclass(frozen=True)
class Preview:
    fingerprint: str
    encoding: str
    headings: list[str]
    columns: dict[str, int | None]
    rows_total: int
    rows_ok: int
    new_places: list[str]
    problems: list[Problem]  # the first PROBLEMS_SHOWN
    problems_total: int
    sample: list[SampleRow]
    room: int  # jumps that still fit under the limit
    already_imported_at: datetime | None


@dataclass(frozen=True)
class Outcome:
    outcome: str  # imported | already_imported
    record: ImportRecord


class ImportStore(Protocol):
    def lock_owner(self, actor: Actor) -> None:
        """The per-person gate that manual place and jump creation also take."""
        ...

    def next_sequence(self, actor: Actor) -> int: ...
    def count_jumps(self, actor: Actor) -> int: ...
    def count_places(self, actor: Actor) -> int: ...
    def venues_named(self, keys: list[str]) -> list[VenueName]:
        """Listed or closed dropzones whose name or alias has one of these search keys."""
        ...

    def own_places(self, actor: Actor) -> list[PlaceName]: ...
    def existing(self, actor: Actor) -> Existing: ...
    def by_fingerprint(self, actor: Actor, fingerprint: str) -> ImportRecord | None: ...
    def get(self, actor: Actor, import_id: uuid.UUID) -> ImportRecord | None: ...
    def recent(self, actor: Actor, limit: int) -> list[ImportRecord]: ...
    def forget(self, actor: Actor, import_id: uuid.UUID) -> None:
        """Delete an undone import's row so the same file can be imported again."""
        ...

    def claim(
        self, actor: Actor, record: ImportRecord, fingerprint: str, sequence: int
    ) -> bool:
        """Insert the import row; False when a concurrent import took the sequence or file."""
        ...

    def insert_rows(self, table: str, rows: list[dict[str, Any]]) -> None: ...
    def mark_undone(
        self, actor: Actor, import_id: uuid.UUID, counts: dict[str, int], now: datetime
    ) -> bool:
        """Set the undo time where it is still empty; False when it was already set."""
        ...

    def delete_jumps(self, actor: Actor, import_id: uuid.UUID) -> int: ...
    def delete_unused_places(
        self, actor: Actor, place_ids: tuple[uuid.UUID, ...]
    ) -> int: ...


StoreFactory = Callable[[], AbstractContextManager[ImportStore]]
Clock = Callable[[], datetime]


class _LostRace(Exception):
    pass


@dataclass(frozen=True)
class _Target:
    kind: str  # venue | place | new_place
    id: uuid.UUID | None  # None for a new place until it is written
    name: str


@dataclass(frozen=True)
class _Plan:
    fingerprint: str
    table: Table
    columns: dict[str, int | None]
    rows: list[tuple[Draft, _Target]]
    problems: list[Problem]
    new_places: dict[str, str]  # place key -> name as first written
    existing_jumps: int


def _core(draft: Draft, target: _Target) -> tuple[Any, ...]:
    """The same facts, in the same order, as logbook.store.CORE."""
    return (
        draft.jumped_on,
        target.id if target.kind == "venue" else None,
        target.id if target.kind == "place" else None,
        draft.jump_type.value,
        None,  # exit time: not imported
        draft.exit_altitude,
        None,  # deployment altitude: not imported
        draft.freefall_seconds,
        draft.notes,
    )


class ImportService:
    def __init__(self, *, stores: StoreFactory, clock: Clock) -> None:
        self._stores = stores
        self._clock = clock

    def _today(self) -> date:
        # The latest calendar date anywhere (UTC+14), as for jumps entered by hand.
        return (self._clock() + timedelta(hours=14)).date()

    # -- reads ------------------------------------------------------------------------

    def imports(self, actor: Actor) -> list[ImportRecord]:
        with self._stores() as store:
            return store.recent(actor, LIST_MAX)

    def check(self, actor: Actor, raw: bytes, options: Options) -> Preview:
        """Everything an import would do, without writing. Advisory: import rechecks."""
        table, columns, digest = self._read(raw, options)
        with self._stores() as store:
            plan = self._plan(store, actor, table, columns, options, digest)
            done = store.by_fingerprint(actor, digest)
        ok = plan.rows
        return Preview(
            fingerprint=digest,
            encoding=table.encoding,
            headings=table.headings,
            columns=columns,
            rows_total=sum(1 for r in table.rows if r),
            rows_ok=len(ok),
            new_places=list(plan.new_places.values()),
            problems=plan.problems[: policy.PROBLEMS_SHOWN],
            problems_total=len(plan.problems),
            sample=[_sample(d, t) for d, t in ok[: policy.SAMPLE_ROWS]],
            room=max(MAX_JUMPS - plan.existing_jumps, 0),
            already_imported_at=done.created_at
            if done and not done.undone_at
            else None,
        )

    # -- writes -----------------------------------------------------------------------

    def run(
        self,
        actor: Actor,
        raw: bytes,
        options: Options,
        *,
        expected: str | None,
        before_write: Callable[[], None],
    ) -> Outcome:
        """`before_write` runs once, only when a write will be attempted (a quota
        reservation the caller refunds unless the outcome is "imported")."""
        table, columns, digest = self._read(raw, options)
        if expected is not None and expected != digest:
            raise ImportChanged()
        with self._stores() as store:
            done = store.by_fingerprint(actor, digest)
        if done is not None and done.undone_at is None:
            return Outcome("already_imported", done)
        before_write()
        for _ in range(ATTEMPTS):
            try:
                return self._attempt(actor, table, columns, options, digest)
            except _LostRace:
                continue
        raise ImportBusy()

    def _attempt(
        self,
        actor: Actor,
        table: Table,
        columns: dict[str, int | None],
        options: Options,
        digest: str,
    ) -> Outcome:
        now = self._clock()
        with self._stores() as store:
            # The same per-person gate as creating a place or a jump by hand, so
            # the place and jump limits below cannot be passed by a create (or an
            # import of the same file) that lands while this import is counting.
            store.lock_owner(actor)
            done = store.by_fingerprint(actor, digest)
            if done is not None and done.undone_at is None:
                return Outcome("already_imported", done)
            # Read before anything is counted: an import committing after this read
            # either shows in the counts below or holds the same sequence.
            sequence = store.next_sequence(actor)
            plan = self._plan(store, actor, table, columns, options, digest)
            if not plan.rows:
                raise ImportRefused("nothing_to_import")
            if plan.existing_jumps + len(plan.rows) > MAX_JUMPS:
                raise LimitReached()
            if done is not None:  # undone earlier: the same file may come back
                store.forget(actor, done.id)
            place_ids = {key: uuid.uuid7() for key in plan.new_places}
            record = ImportRecord(
                id=uuid.uuid7(),
                created_at=now,
                counts={
                    "rows": sum(1 for r in table.rows if r),
                    "jumps": len(plan.rows),
                    "new_places": len(place_ids),
                    "skipped": len(plan.problems),
                },
                undone_at=None,
                place_ids=tuple(place_ids.values()),
            )
            if not store.claim(actor, record, digest, sequence):
                raise _LostRace()
            owner = actor.person_id
            store.insert_rows(
                "places",
                [
                    {
                        "id": place_ids[key],
                        "owner_person_id": owner,
                        "name": name,
                        "country": options.country,
                        "venue_id": None,
                        "created_at": now,
                        "updated_at": now,
                    }  # fmt: skip
                    for key, name in plan.new_places.items()
                ],
            )
            jumps, events = [], []
            for draft, target in plan.rows:
                jump_id = uuid.uuid7()
                if target.kind == "new_place":
                    venue_id, place_id = None, place_ids[policy.place_key(target.name)]
                elif target.kind == "venue":
                    venue_id, place_id = target.id, None
                else:
                    venue_id, place_id = None, target.id
                jumps.append(
                    {
                        "id": jump_id,
                        "owner_person_id": owner,
                        "jumped_on": draft.jumped_on,
                        "venue_id": venue_id,
                        "place_id": place_id,
                        "jump_type": draft.jump_type.value,
                        "jump_number": draft.jump_number,
                        "exit_time": None,
                        "time_zone": None,
                        "exit_altitude": draft.exit_altitude,
                        "deployment_altitude": None,
                        "altitude_unit": draft.altitude_unit.value
                        if draft.altitude_unit
                        else None,
                        "altitude_datum": "unspecified",
                        "freefall_seconds": draft.freefall_seconds,
                        "other_gear": None,
                        "aircraft": draft.aircraft,
                        "notes": draft.notes,
                        "links": [],
                        "source": "imported",
                        "import_id": record.id,
                        "version": 1,
                        "created_at": now,
                        "updated_at": now,
                    }  # fmt: skip
                )
                events.append(
                    {
                        "id": uuid.uuid7(),
                        "owner_person_id": owner,
                        "jump_id": jump_id,
                        "kind": "created",
                        "detail": {"source": "imported"},
                        "created_at": now,
                    }  # fmt: skip
                )
            store.insert_rows("jumps", jumps)
            store.insert_rows("jump_events", events)
        return Outcome("imported", record)

    def undo(self, actor: Actor, import_id: uuid.UUID) -> ImportRecord:
        now = self._clock()
        with self._stores() as store:
            # The per-person gate first, as for imports and manual creates: an
            # import cannot reuse a place, or count a jump as a duplicate, that this
            # undo is deleting, and undo cannot delete a place a new jump now uses.
            store.lock_owner(actor)
            record = store.get(actor, import_id)
            if record is None:
                raise NotFound()
            if record.undone_at is not None:
                raise AlreadyUndone()
            removed = store.delete_jumps(actor, import_id)
            places = store.delete_unused_places(actor, record.place_ids)
            counts = record.counts | {
                "removed_jumps": removed,
                "removed_places": places,
            }
            # Compare-and-swap on the empty undo time: of two undos one changes it;
            # the other rolls back its deletes and answers already undone.
            if not store.mark_undone(actor, import_id, counts, now):
                raise AlreadyUndone()
        return ImportRecord(record.id, record.created_at, counts, now, record.place_ids)

    # -- helpers ----------------------------------------------------------------------

    def _read(
        self, raw: bytes, options: Options
    ) -> tuple[Table, dict[str, int | None], str]:
        table = policy.read_table(raw)
        columns = policy.mapping(table.headings, options.mapping)
        return table, columns, policy.fingerprint(raw, options, columns)

    def _plan(
        self,
        store: ImportStore,
        actor: Actor,
        table: Table,
        columns: dict[str, int | None],
        options: Options,
        digest: str,
    ) -> _Plan:
        drafts, problems = policy.drafts(table, columns, options, self._today())
        venues: dict[str, list[VenueName]] = {}
        search = sorted({policy.heading_key(d.place) for d in drafts})
        for venue in store.venues_named(search) if search else []:
            for key in {policy.place_key(n) for n in venue.names}:
                venues.setdefault(key, []).append(venue)
        places: dict[str, PlaceName] = {}
        for place in store.own_places(actor):  # oldest first: the first name wins
            places.setdefault(policy.place_key(place.name), place)

        targets: dict[str, _Target | str] = {}
        for draft in drafts:
            key = policy.place_key(draft.place)
            if key in targets:
                continue
            found = venues.get(key, [])
            if len(found) > 1 and options.country:
                found = [v for v in found if v.country == options.country]
            if len(found) == 1:
                targets[key] = _Target("venue", found[0].id, found[0].names[0])
            elif len(found) > 1:
                targets[key] = "place_ambiguous"
            elif key in places:
                targets[key] = _Target("place", places[key].id, places[key].name)
            else:
                targets[key] = _Target("new_place", None, draft.place)

        existing = store.existing(actor)
        seen: set[int] = set()
        rows: list[tuple[Draft, _Target]] = []
        for draft in drafts:
            target = targets[policy.place_key(draft.place)]
            if isinstance(target, str):
                problems.append(Problem(draft.row, target))
            elif draft.jump_number is not None:
                if draft.jump_number in existing.numbers:
                    problems.append(Problem(draft.row, "likely_duplicate"))
                elif draft.jump_number in seen:
                    problems.append(Problem(draft.row, "repeated_in_file"))
                else:
                    seen.add(draft.jump_number)
                    rows.append((draft, target))
            elif target.kind != "new_place" and _core(draft, target) in existing.cores:
                problems.append(Problem(draft.row, "likely_duplicate"))
            else:
                rows.append((draft, target))
        # Only places that a row to be saved needs; named as first written.
        new_places: dict[str, str] = {}
        for _, target in rows:
            if target.kind == "new_place":
                new_places.setdefault(policy.place_key(target.name), target.name)
        if new_places and not options.country:
            raise ImportRefused("country_required", names=list(new_places.values()))
        if new_places and (
            store.count_places(actor) + len(new_places) > MAX_PLACES_PER_PERSON
        ):
            raise PlaceLimitReached()
        return _Plan(
            fingerprint=digest,
            table=table,
            columns=columns,
            rows=rows,
            problems=sorted(problems, key=lambda p: p.row),
            new_places=new_places,
            existing_jumps=store.count_jumps(actor),
        )


def _sample(draft: Draft, target: _Target) -> SampleRow:
    return SampleRow(
        row=draft.row,
        jumped_on=draft.jumped_on,
        jump_number=draft.jump_number,
        place=target.name,
        place_kind=target.kind,
        jump_type=draft.jump_type.value,
        exit_altitude=draft.exit_altitude,
        altitude_unit=draft.altitude_unit.value if draft.altitude_unit else None,
        freefall_seconds=draft.freefall_seconds,
        notes=draft.notes,
        aircraft=draft.aircraft,
    )
