"""Gear rules as plain values (#152). No framework or persistence imports.

Everything here is the owner's own declaration: nothing verifies ownership,
title, servicing or airworthiness, and a serial is never a lookup key.
"""

import re
import unicodedata
from collections.abc import Iterable
from dataclasses import dataclass
from datetime import date, timedelta
from enum import StrEnum
from typing import Literal

from app.skydiver.directory.policy import DirectoryRuleError as RuleError

LABEL_MAX = 80
TEXT_MAX = 80
SERIAL_MAX = 120
NOTES_MAX = 1000
PERFORMED_BY_MAX = 120
# Working caps per account (architecture A7 gear limit; not measured capacity).
MAX_COMPONENTS = 50
MAX_RIGS = 20
MAX_SERVICE_ENTRIES = 100  # per component

# The one interval table. Source: FAA 14 CFR 105.43(a), which USPA follows: a
# reserve parachute must have been packed within the preceding 180 days. Checked
# 2026-11-12. Other countries set their own rule, so the owner can set a different
# interval per reserve. No AAD interval is listed: manufacturers set those, and only
# dates the owner entered are used for an AAD.
REPACK_SOURCE: Literal["USPA / FAA 14 CFR 105.43"] = "USPA / FAA 14 CFR 105.43"
REPACK_INTERVAL_DAYS = 180
REPACK_INTERVAL_MAX = 730
# "Due soon": due within this many days, or overdue.
DUE_SOON_DAYS = 30
# A jump-count limit is the owner's own number; none is ever suggested.
JUMP_LIMIT_MAX = 100_000
JUMP_LIMIT_LABEL_MAX = 80
# "Due soon" for a jump limit: within 10% of it, or within 25 jumps, whichever is
# fewer jumps (or over it).
JUMP_LIMIT_SOON_SHARE = 10  # percent
JUMP_LIMIT_SOON_MAX = 25
# A canopy's size in square feet as the owner enters it (main or reserve only).
CANOPY_SIZE_MIN = 20
CANOPY_SIZE_MAX = 400


class ComponentKind(StrEnum):
    CONTAINER = "container"
    MAIN = "main"
    RESERVE = "reserve"
    AAD = "aad"
    OTHER = "other"


class Relation(StrEnum):
    """How the person holds the item. Self-declared; never verified title."""

    OWNED = "owned"
    BORROWED = "borrowed"
    RENTED = "rented"


class AcquisitionMethod(StrEnum):
    PURCHASE = "purchase"
    GIFT = "gift"
    INHERITANCE = "inheritance"
    OTHER = "other"


class ServiceKind(StrEnum):
    REPACK = "repack"
    INSPECTION = "inspection"
    MAINTENANCE = "maintenance"
    AAD_SERVICE = "aad_service"
    OTHER = "other"


_PARTIAL = re.compile(r"^(\d{4})(?:-(\d{2})(?:-(\d{2}))?)?$")


@dataclass(frozen=True)
class PartialDate:
    """A label date at the precision it was given: YYYY, YYYY-MM or YYYY-MM-DD."""

    text: str

    @property
    def precision(self) -> str:
        return {4: "year", 7: "month", 10: "day"}[len(self.text)]


def partial_date(value: str | None, *, field: str, today: date) -> PartialDate | None:
    if value is None or not value.strip():
        return None
    match = _PARTIAL.match(value.strip())
    if not match:
        raise RuleError(f"{field}_invalid")
    year, month, day = match.groups()
    try:
        first = date(int(year), int(month or 1), int(day or 1))
    except ValueError:
        raise RuleError(f"{field}_invalid") from None
    if first > today or first.year < 1900:
        raise RuleError(f"{field}_invalid")
    return PartialDate(match.group(0))


def serial(value: str | None) -> str | None:
    """Kept exactly as entered (case, leading zeros, punctuation), minus edge spaces."""
    if value is None:
        return None
    if any(unicodedata.category(c) == "Cc" for c in value):
        raise RuleError("serial_invalid")
    kept = value.strip()
    if not kept:
        return None
    if len(kept) > SERIAL_MAX:
        raise RuleError("serial_too_long")
    return kept


def serial_key(value: str | None) -> str | None:
    """Comparison form for the owner's own duplicate warning (never across accounts)."""
    if not value:
        return None
    key = re.sub(r"[^0-9A-Z]", "", unicodedata.normalize("NFKC", value).upper())
    return key or None


def check_acquisition(
    relation: Relation, method: AcquisitionMethod | None, acquired: PartialDate | None
) -> None:
    if relation is not Relation.OWNED and (method is not None or acquired is not None):
        raise RuleError("acquisition_requires_owned")


def check_service_dates(done_on: date, due_on: date | None, today: date) -> None:
    if done_on > today:
        raise RuleError("service_date_in_future")
    if due_on is not None and due_on < done_on:
        raise RuleError("due_before_service")


def check_membership(starts_on: date, not_before: date | None, today: date) -> None:
    """Rig changes are dated and never overlap: not before the latest stint's start
    (or its end, once it has ended), and not in the future."""
    if starts_on > today:
        raise RuleError("rig_date_in_future")
    if not_before is not None and starts_on < not_before:
        raise RuleError("rig_date_before_current")


def repack_interval(value: int | None) -> int | None:
    """The owner's own reserve repack interval in days; None: the default."""
    if value is None:
        return None
    if not 1 <= value <= REPACK_INTERVAL_MAX:
        raise RuleError("repack_interval_invalid")
    return value


@dataclass(frozen=True)
class JumpLimit:
    limit: int
    label: str
    service_kind: ServiceKind  # its latest entry restarts the count


def jump_limit(
    limit: int | None, label: str | None, service_kind: str | None
) -> JumpLimit | None:
    """The owner's one jump-count limit, or None when it is cleared (all empty)."""
    text = (label or "").strip()
    if limit is None and not text:
        return None
    if limit is None:
        raise RuleError("jump_limit_required")
    if not 1 <= limit <= JUMP_LIMIT_MAX:
        raise RuleError("jump_limit_invalid")
    if not text:
        raise RuleError("jump_limit_label_required")
    cleaned = " ".join(text.split())
    if len(cleaned) > JUMP_LIMIT_LABEL_MAX:
        raise RuleError("jump_limit_label_too_long")
    try:
        kind = ServiceKind(service_kind or ServiceKind.MAINTENANCE.value)
    except ValueError:
        raise RuleError("jump_limit_service_kind_invalid") from None
    return JumpLimit(limit, cleaned, kind)


def latest_service_on(service: Iterable[ServiceFact], kind: ServiceKind) -> date | None:
    """The day of the latest service entry of this kind; None when there is none."""
    days = [fact.done_on for fact in service if fact.kind is kind]
    return max(days) if days else None


def jump_limit_status(limit: int, used: int) -> DueStatus:
    """Over the limit is overdue; at it, or within 10% or 25 jumps of it, is soon."""
    left = limit - used
    if left < 0:
        return DueStatus.OVERDUE
    if left <= JUMP_LIMIT_SOON_MAX and left * 100 <= limit * JUMP_LIMIT_SOON_SHARE:
        return DueStatus.SOON
    return DueStatus.LATER


def canopy_size(value: int | None, kind: ComponentKind) -> int | None:
    """A main or reserve canopy's size in whole square feet; None when not entered."""
    if value is None:
        return None
    if kind not in (ComponentKind.MAIN, ComponentKind.RESERVE):
        raise RuleError("canopy_size_not_a_canopy")
    if not CANOPY_SIZE_MIN <= value <= CANOPY_SIZE_MAX:
        raise RuleError("canopy_size_invalid")
    return value


def end_of_life(value: date | None) -> date | None:
    """A date the owner entered (e.g. from the label); never estimated here."""
    if value is None:
        return None
    if not 1900 <= value.year <= 2100:
        raise RuleError("end_of_life_invalid")
    return value


# -- due dates ------------------------------------------------------------------------


class DueKind(StrEnum):
    RESERVE_REPACK = "reserve_repack"  # a reserve's latest repack
    SERVICE = "service"  # any other service entry's own due date
    END_OF_LIFE = "end_of_life"  # the date the owner entered
    JUMP_LIMIT = "jump_limit"  # the owner's jump-count limit


class DueStatus(StrEnum):
    OVERDUE = "overdue"  # the due date has passed
    SOON = "soon"  # due today or within DUE_SOON_DAYS
    LATER = "later"


@dataclass(frozen=True)
class ServiceFact:
    kind: ServiceKind
    done_on: date
    due_on: date | None
    order: int  # higher: recorded later (breaks ties on the same day)


@dataclass(frozen=True)
class Due:
    kind: DueKind
    due_on: date
    service_kind: ServiceKind | None = None
    # "entered": the owner's own date; "interval": the latest repack plus an interval.
    basis: Literal["entered", "interval"] = "entered"
    interval_days: int | None = None
    interval_is_default: bool = False


def due_dates(
    kind: ComponentKind,
    service: Iterable[ServiceFact],
    *,
    repack_interval_days: int | None,
    end_of_life_on: date | None,
) -> list[Due]:
    """What one component has coming due, from its own records only.

    Only the latest entry of each service kind counts: a newer repack replaces the
    due date of an older one. A reserve's latest repack without an entered due date
    is due its interval later (the owner's, else REPACK_INTERVAL_DAYS). Nothing is
    estimated for any other kind, and an end of life is only ever the owner's date.
    """
    latest: dict[ServiceKind, ServiceFact] = {}
    for fact in service:
        held = latest.get(fact.kind)
        if held is None or (fact.done_on, fact.order) > (held.done_on, held.order):
            latest[fact.kind] = fact
    found: list[Due] = []
    for service_kind, fact in latest.items():
        if kind is ComponentKind.RESERVE and service_kind is ServiceKind.REPACK:
            if fact.due_on is not None:
                found.append(Due(DueKind.RESERVE_REPACK, fact.due_on, service_kind))
            else:
                days = repack_interval_days or REPACK_INTERVAL_DAYS
                found.append(
                    Due(
                        DueKind.RESERVE_REPACK,
                        fact.done_on + timedelta(days=days),
                        service_kind,
                        basis="interval",
                        interval_days=days,
                        interval_is_default=repack_interval_days is None,
                    )
                )
        elif fact.due_on is not None:
            found.append(Due(DueKind.SERVICE, fact.due_on, service_kind))
    if end_of_life_on is not None:
        found.append(Due(DueKind.END_OF_LIFE, end_of_life_on))
    return sorted(found, key=lambda d: (d.due_on, d.kind.value))


def due_status(due_on: date, today: date) -> DueStatus:
    """Due on `due_on` means still in time that day; overdue from the day after."""
    if due_on < today:
        return DueStatus.OVERDUE
    if due_on <= today + timedelta(days=DUE_SOON_DAYS):
        return DueStatus.SOON
    return DueStatus.LATER
