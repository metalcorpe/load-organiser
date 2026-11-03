"""Gear rules as plain values (#152). No framework or persistence imports.

Everything here is the owner's own declaration: nothing verifies ownership,
title, servicing or airworthiness, and a serial is never a lookup key.
"""

import re
import unicodedata
from dataclasses import dataclass
from datetime import date
from enum import StrEnum

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
