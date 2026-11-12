"""Personal jump rules as plain values (#153). No framework or persistence imports.

A jump is the owner's own declaration of a completed jump. Nothing here verifies
it, derives eligibility from it, or invents a value the jumper did not give:
unknown measurements stay null, never zero, and an altitude keeps the unit and
datum it was entered with.
"""

import re
from dataclasses import dataclass
from datetime import date, time
from enum import StrEnum
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

from app.skydiver.directory import policy as directory_policy
from app.skydiver.directory.policy import DirectoryRuleError as RuleError

# Working design limits (release brief; architecture A7), not measured capacity.
MAX_JUMPS = 2000
NOTES_MAX = 2000
LINKS_MAX = 5
LINK_MAX = 2048
OTHER_GEAR_MAX = 200
COMPONENTS_MAX = 10  # per jump
JUMP_NUMBER_MAX = 1_000_000
FREEFALL_MAX_SECONDS = 600
ALTITUDE_MAX = {"ft": 45_000, "m": 13_700}
EARLIEST = date(1919, 1, 1)


class JumpType(StrEnum):
    UNSPECIFIED = "unspecified"
    BELLY = "belly"
    FREEFLY = "freefly"
    ANGLE = "angle"
    WINGSUIT = "wingsuit"
    CANOPY = "canopy"
    CRW = "crw"
    ACCURACY = "accuracy"
    HOP_AND_POP = "hop_and_pop"
    TANDEM = "tandem"
    TRAINING = "training"
    OTHER = "other"


class AltitudeUnit(StrEnum):
    FT = "ft"
    M = "m"


class AltitudeDatum(StrEnum):
    """What the altitude is measured from. Never assumed when not stated."""

    UNSPECIFIED = "unspecified"
    AGL = "agl"
    MSL = "msl"


@dataclass(frozen=True)
class Altitudes:
    exit: int | None
    deployment: int | None
    unit: AltitudeUnit | None
    datum: AltitudeDatum


def jump_date(value: date, today: date) -> date:
    """A calendar date as the jumper gave it; never shifted by a time zone."""
    if value > today:
        raise RuleError("jump_date_in_future")
    if value < EARLIEST:
        raise RuleError("jump_date_invalid")
    return value


def jump_number(value: int | None) -> int | None:
    if value is None:
        return None
    if not 1 <= value <= JUMP_NUMBER_MAX:
        raise RuleError("jump_number_invalid")
    return value


_ZONE = re.compile(r"^[A-Za-z][A-Za-z0-9_+\-]*(/[A-Za-z0-9_+\-]+){0,2}$")


def exit_time(value: time | None, zone: str | None) -> tuple[time | None, str | None]:
    """An exact local exit time needs its IANA time zone; the zone alone means nothing."""
    if value is None:
        return None, None
    if value.tzinfo is not None:
        raise RuleError("exit_time_invalid")
    key = (zone or "").strip()
    if not key:
        raise RuleError("time_zone_required")
    if len(key) > 64 or not _ZONE.match(key):
        raise RuleError("time_zone_invalid")
    try:
        ZoneInfo(key)
    except ZoneInfoNotFoundError, ValueError:
        raise RuleError("time_zone_invalid") from None
    return value.replace(second=0, microsecond=0), key


def altitudes(
    exit_altitude: int | None,
    deployment_altitude: int | None,
    unit: AltitudeUnit | None,
    datum: AltitudeDatum | None,
) -> Altitudes:
    given = [a for a in (exit_altitude, deployment_altitude) if a is not None]
    if not given:
        # No altitude: no unit or datum is kept, so none is implied.
        return Altitudes(None, None, None, AltitudeDatum.UNSPECIFIED)
    if unit is None:
        raise RuleError("altitude_unit_required")
    if any(not 0 < a <= ALTITUDE_MAX[unit.value] for a in given):
        raise RuleError("altitude_invalid")
    if (
        exit_altitude is not None
        and deployment_altitude is not None
        and deployment_altitude > exit_altitude
    ):
        raise RuleError("deployment_above_exit")
    return Altitudes(
        exit_altitude, deployment_altitude, unit, datum or AltitudeDatum.UNSPECIFIED
    )


def freefall_seconds(value: int | None) -> int | None:
    if value is None:
        return None
    if not 0 <= value <= FREEFALL_MAX_SECONDS:
        raise RuleError("freefall_invalid")
    return value


def links(values: list[str] | None) -> list[str]:
    """Up to five external http(s) references. Never fetched or previewed."""
    kept = [v.strip() for v in values or [] if v and v.strip()]
    if len(kept) > LINKS_MAX:
        raise RuleError("too_many_links")
    out: list[str] = []
    for url in kept:
        if len(url) > LINK_MAX:
            raise RuleError("link_invalid")
        try:
            out.append(directory_policy.source_url(url))
        except RuleError:
            raise RuleError("link_invalid") from None
    return out


def notes(value: str | None) -> str | None:
    if value is None or not value.strip():
        return None
    cleaned = value.strip()
    if len(cleaned) > NOTES_MAX:
        raise RuleError("notes_too_long")
    return cleaned


def other_gear(value: str | None) -> str | None:
    """A description of borrowed, rented or otherwise unrecorded equipment."""
    return directory_policy.optional_text(
        value, field="other_gear", maximum=OTHER_GEAR_MAX
    )


def component_ids[T](values: list[T] | None) -> list[T]:
    unique = list(dict.fromkeys(values or []))
    if len(unique) > COMPONENTS_MAX:
        raise RuleError("too_many_components")
    return unique


# Numbering notes stay brief: the first few of each kind, plus how many there are.
NUMBERING_ISSUES_MAX = 5
REPEAT_JUMPS_MAX = 5


@dataclass(frozen=True)
class Numbered[T]:
    number: int
    ref: T  # the jump, opaque here


@dataclass(frozen=True)
class Gap[T]:
    first: int  # the first missing number
    last: int  # the last missing number
    before: T  # a jump numbered first - 1
    after: T  # a jump numbered last + 1


@dataclass(frozen=True)
class Repeat[T]:
    number: int
    uses: int
    refs: list[T]  # at most REPEAT_JUMPS_MAX


@dataclass(frozen=True)
class Numbering[T]:
    highest: int | None
    gaps: list[Gap[T]]
    gap_count: int
    repeats: list[Repeat[T]]
    repeat_count: int


def numbering[T](jumps: list[Numbered[T]]) -> Numbering[T]:
    """Highest number, gaps between the lowest and highest, and repeated numbers.

    `jumps` are the owner's numbered jumps sorted by number (then a stable order).
    One pass, linear in their count, which the jump limit bounds. Numbers below the
    lowest are not gaps: a logbook may start mid-career.
    """
    gaps: list[Gap[T]] = []
    repeats: list[Repeat[T]] = []
    gap_count = repeat_count = 0
    previous: Numbered[T] | None = None
    i = 0
    while i < len(jumps):
        end = i + 1
        while end < len(jumps) and jumps[end].number == jumps[i].number:
            end += 1
        current = jumps[i]
        if previous is not None and current.number > previous.number + 1:
            gap_count += 1
            if len(gaps) < NUMBERING_ISSUES_MAX:
                gaps.append(
                    Gap(
                        previous.number + 1,
                        current.number - 1,
                        previous.ref,
                        current.ref,
                    )
                )
        if end - i > 1:
            repeat_count += 1
            if len(repeats) < NUMBERING_ISSUES_MAX:
                refs = [j.ref for j in jumps[i : min(end, i + REPEAT_JUMPS_MAX)]]
                repeats.append(Repeat(current.number, end - i, refs))
        previous = current
        i = end
    return Numbering(
        highest=jumps[-1].number if jumps else None,
        gaps=gaps,
        gap_count=gap_count,
        repeats=repeats,
        repeat_count=repeat_count,
    )
