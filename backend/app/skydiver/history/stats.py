"""Statistics from the owner's own entries. Plain values, no I/O.

Every figure counts detailed entries only; a declared prior jump count has no
dates, types, places or measurements, so it adds to none of them (the service
reports it beside the total, and says so). Measurements count only the entries
that recorded them, with the number that did not. Altitudes keep the unit they
were entered in: feet and metres are summarised separately, never converted.
Wing loading is the jumper's own exit weight over their main canopy's size.

Linear in the number of entries, which the logbook's jump limit bounds.
"""

import uuid
from collections import Counter
from collections.abc import Callable, Hashable, Iterable
from dataclasses import dataclass
from datetime import date
from decimal import ROUND_HALF_UP, Decimal

from app.skydiver.directory.policy import DirectoryRuleError as RuleError
from app.skydiver.history.policy import recent_months
from app.skydiver.logbook.loading import Loading, LoadingRange, loading_range
from app.skydiver.logbook.policy import EARLIEST

TOP = 10  # places and aircraft listed by name; the rest are counted as others
MONTHS = 24  # jumps per month without a year filter: the last 24 calendar months

type PlaceKey = tuple[str, uuid.UUID]  # ("venue" | "place", id), merges resolved


@dataclass(frozen=True)
class Entry:
    jumped_on: date
    jump_type: str
    place: PlaceKey
    aircraft: str | None
    freefall_seconds: int | None
    exit_altitude: int | None
    altitude_unit: str | None
    loading: Loading


@dataclass(frozen=True)
class Ranked[K]:
    items: list[tuple[K, int]]  # at most TOP, most jumps first
    others: int  # jumps in the rest
    other_count: int  # how many others (places or aircraft)


@dataclass(frozen=True)
class FreefallYear:
    year: int
    seconds: int  # entries with a freefall time only
    with_time: int
    without_time: int


@dataclass(frozen=True)
class Altitude:
    unit: str  # "ft" | "m", as entered
    jumps: int  # entries with an exit altitude in this unit
    average: int  # rounded to the whole unit
    highest: int


@dataclass(frozen=True)
class Stats:
    year: int | None
    years: list[int]  # every year with an entry, newest first (for the filter)
    jumps: int  # entries in scope
    per_year: list[tuple[int, int]]  # every year from the first entry; not filtered
    per_month: list[tuple[str, int]]  # YYYY-MM, oldest first
    by_type: list[tuple[str, int]]
    by_place: Ranked[PlaceKey]
    by_aircraft: Ranked[str]
    aircraft_not_recorded: int
    freefall: list[FreefallYear]  # oldest first
    altitudes: list[Altitude]  # feet first
    altitude_not_recorded: int
    loading: LoadingRange


def check_year(year: int | None, latest: date) -> int | None:
    if year is not None and not EARLIEST.year <= year <= latest.year:
        raise RuleError("year_invalid")
    return year


def top[K: Hashable](
    counts: dict[K, int], name: Callable[[K], str], n: int = TOP
) -> Ranked[K]:
    """The `n` with most jumps (ties by name), and the rest folded into others."""
    ranked = sorted(counts.items(), key=lambda kv: (-kv[1], name(kv[0]).casefold()))
    rest = ranked[n:]
    return Ranked(ranked[:n], sum(c for _, c in rest), len(rest))


def _aircraft(entries: Iterable[Entry]) -> tuple[dict[str, int], int]:
    """Counts by aircraft, the same text however it is spaced or capitalised, named
    by its most used spelling; and the entries without one."""
    spellings: dict[str, Counter[str]] = {}
    missing = 0
    for e in entries:
        text = " ".join((e.aircraft or "").split())
        if not text:
            missing += 1
            continue
        spellings.setdefault(text.casefold(), Counter())[text] += 1
    counts = {
        max(found.items(), key=lambda kv: (kv[1], kv[0]))[0]: found.total()
        for found in spellings.values()
    }
    return counts, missing


def _freefall(entries: Iterable[Entry]) -> list[FreefallYear]:
    years: dict[int, list[int]] = {}
    for e in entries:
        row = years.setdefault(e.jumped_on.year, [0, 0, 0])
        if e.freefall_seconds is None:
            row[2] += 1
        else:
            row[0] += e.freefall_seconds
            row[1] += 1
    return [FreefallYear(y, *years[y]) for y in sorted(years)]


def _altitudes(entries: Iterable[Entry]) -> tuple[list[Altitude], int]:
    by_unit: dict[str, list[int]] = {}
    missing = 0
    for e in entries:
        if e.exit_altitude is None or e.altitude_unit is None:
            missing += 1
            continue
        by_unit.setdefault(e.altitude_unit, []).append(e.exit_altitude)
    found = [
        Altitude(
            unit,
            len(values),
            int(
                (Decimal(sum(values)) / len(values)).quantize(
                    Decimal(1), rounding=ROUND_HALF_UP
                )
            ),
            max(values),
        )
        for unit in ("ft", "m")
        if (values := by_unit.get(unit))
    ]
    return found, missing


def stats(
    entries: list[Entry],
    *,
    year: int | None,
    latest: date,
    place_name: Callable[[PlaceKey], str],
) -> Stats:
    """`latest` is the latest calendar date anywhere; `year` narrows everything but
    the jumps per year, which always show every year so another can be chosen."""
    all_years = Counter(e.jumped_on.year for e in entries)
    per_year = (
        [(y, all_years[y]) for y in range(min(all_years), max(all_years) + 1)]
        if all_years
        else []
    )
    scoped = [e for e in entries if year is None or e.jumped_on.year == year]
    months = (
        [f"{year:04d}-{m:02d}" for m in range(1, 13)]
        if year is not None
        else recent_months(latest, MONTHS)
    )
    per_month = dict.fromkeys(months, 0)
    for e in scoped:
        key = f"{e.jumped_on.year:04d}-{e.jumped_on.month:02d}"
        if key in per_month:
            per_month[key] += 1
    by_type = Counter(e.jump_type for e in scoped)
    aircraft, no_aircraft = _aircraft(scoped)
    altitudes, no_altitude = _altitudes(scoped)
    return Stats(
        year=year,
        years=sorted(all_years, reverse=True),
        jumps=len(scoped),
        per_year=per_year,
        per_month=list(per_month.items()),
        by_type=sorted(by_type.items(), key=lambda kv: (-kv[1], kv[0])),
        by_place=top(Counter(e.place for e in scoped), place_name),
        by_aircraft=top(aircraft, lambda a: a),
        aircraft_not_recorded=no_aircraft,
        freefall=_freefall(scoped),
        altitudes=altitudes,
        altitude_not_recorded=no_altitude,
        loading=loading_range(e.loading for e in scoped),
    )
