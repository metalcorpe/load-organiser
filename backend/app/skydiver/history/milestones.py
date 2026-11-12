"""Private milestones derived from the owner's own entries. Plain values, no I/O.

Computed on read from the owner's detailed entries (at most 2,000; one pass), never
stored, shared or shown as badges. Entries are taken in logbook order: by date, then
on the same day by the jumper's own jump number (numbered entries first), then exit
time (timed entries first), and last by entry id. Entry ids are uuid7, so the last
tie-break is the order the entries were inserted (an import inserts in file order).

- Jump counts 1, 25, 50, 100, 200, 250, 500, 1000, then every 1000: the Nth jump
  counts the declared prior jumps first (personal history policy: entries before
  the baseline date are already within it), then the entries since. A count within
  the prior jumps has no date: it happened before this logbook.
- The first entry of each jump type ("unspecified" is not a type).
- Recorded freefall time crossing 1, 5, 10, 25, 50 and 100 hours: the entry that
  crossed it. Entries without a freefall time and prior jumps add none.
- The first entry at each place; only the most recent PLACES_SHOWN of these.
"""

import uuid
from collections.abc import Iterable, Iterator
from dataclasses import dataclass
from datetime import date, time
from enum import StrEnum

JUMP_COUNTS = (1, 25, 50, 100, 200, 250, 500, 1000)
JUMP_COUNT_STEP = 1000  # after the last fixed count
FREEFALL_HOURS = (1, 5, 10, 25, 50, 100)
PLACES_SHOWN = 5
UNSPECIFIED = "unspecified"


class MilestoneKind(StrEnum):
    JUMP_COUNT = "jump_count"
    FREEFALL = "freefall"
    JUMP_TYPE = "jump_type"
    PLACE = "place"


# Several milestones of one entry read in this order.
_KIND_ORDER = {kind: i for i, kind in enumerate(MilestoneKind)}


@dataclass(frozen=True)
class Entry:
    id: uuid.UUID
    jumped_on: date
    jump_number: int | None
    exit_time: time | None
    jump_type: str
    freefall_seconds: int | None
    place: tuple[str, uuid.UUID]  # ("venue" | "place", id), merges already resolved


@dataclass(frozen=True)
class Prior:
    """A consistent baseline: `jumps` completed before `before_on`."""

    jumps: int
    before_on: date


@dataclass(frozen=True)
class Milestone:
    kind: MilestoneKind
    on: date | None  # None: a jump count within the prior jumps
    jump_id: uuid.UUID | None
    number: int | None = None  # JUMP_COUNT
    hours: int | None = None  # FREEFALL
    jump_type: str | None = None  # JUMP_TYPE
    place: tuple[str, uuid.UUID] | None = None  # PLACE


def _order(e: Entry) -> tuple[date, bool, int, bool, time, uuid.UUID]:
    return (
        e.jumped_on,
        e.jump_number is None,
        e.jump_number or 0,
        e.exit_time is None,
        e.exit_time or time.min,
        e.id,
    )


def ordered(entries: Iterable[Entry]) -> list[Entry]:
    return sorted(entries, key=_order)


def jump_counts(upto: int) -> Iterator[int]:
    """The counted milestones up to and including `upto`."""
    yield from (n for n in JUMP_COUNTS if n <= upto)
    n = JUMP_COUNTS[-1] + JUMP_COUNT_STEP
    while n <= upto:
        yield n
        n += JUMP_COUNT_STEP


def milestones(
    entries: Iterable[Entry], *, prior: Prior | None, count_jumps: bool = True
) -> list[Milestone]:
    """Newest first; jump counts before this logbook (undated) last, highest first.

    `count_jumps` is False while the baseline is inconsistent: no Nth jump is
    dated until the prior jump count and the entries agree.
    """
    seq = ordered(entries)
    rank = {e.id: i for i, e in enumerate(seq)}
    found: list[Milestone] = []

    if count_jumps:
        offset = prior.jumps if prior else 0
        counted = [e for e in seq if prior is None or e.jumped_on >= prior.before_on]
        for n in jump_counts(offset + len(counted)):
            if n <= offset:
                found.append(Milestone(MilestoneKind.JUMP_COUNT, None, None, number=n))
            else:
                e = counted[n - offset - 1]
                found.append(
                    Milestone(MilestoneKind.JUMP_COUNT, e.jumped_on, e.id, number=n)
                )

    types: set[str] = set()
    places: list[Milestone] = []
    seen_places: set[tuple[str, uuid.UUID]] = set()
    hours = iter(FREEFALL_HOURS)
    next_hours = next(hours, None)
    freefall = 0
    for e in seq:
        if e.jump_type != UNSPECIFIED and e.jump_type not in types:
            types.add(e.jump_type)
            found.append(
                Milestone(
                    MilestoneKind.JUMP_TYPE, e.jumped_on, e.id, jump_type=e.jump_type
                )
            )
        if e.place not in seen_places:
            seen_places.add(e.place)
            places.append(
                Milestone(MilestoneKind.PLACE, e.jumped_on, e.id, place=e.place)
            )
        freefall += e.freefall_seconds or 0
        while next_hours is not None and freefall >= next_hours * 3600:
            found.append(
                Milestone(MilestoneKind.FREEFALL, e.jumped_on, e.id, hours=next_hours)
            )
            next_hours = next(hours, None)
    found.extend(places[-PLACES_SHOWN:])

    dated = [m for m in found if m.jump_id is not None]
    undated = [m for m in found if m.jump_id is None]
    dated.sort(
        key=lambda m: (-rank[m.jump_id], _KIND_ORDER[m.kind])  # type: ignore[index]
    )
    undated.sort(key=lambda m: -(m.number or 0))
    return dated + undated
