"""Jump currency guidance from the owner's own entries. Plain values, no I/O.

Guidance only: computed from the jumps the owner recorded, never a verified status,
a licence check or a permission to jump. The licence is the owner's own statement.

Only logged jumps count. A prior jump count (baseline) has no dates, so it adds no
currency. Every jump type counts, tandem included: the logbook does not record
whether the jumper was the tandem instructor or the passenger.
"""

from dataclasses import dataclass
from datetime import date, timedelta
from enum import StrEnum
from typing import Literal

SOURCE: Literal["USPA SIM 5-2"] = "USPA SIM 5-2"


class Licence(StrEnum):
    NONE = "none"
    STUDENT = "student"
    A = "a"
    B = "b"
    C = "c"
    D = "d"


# The one policy table. Source: USPA Skydiver's Information Manual, section 5-2
# (recurrency training): a jumper whose last freefall skydive was longer ago than
# this should make a supervised jump. Checked 2026-11-12.
RECURRENCY_DAYS: dict[Licence, int] = {
    Licence.STUDENT: 30,
    Licence.A: 60,
    Licence.B: 90,
    Licence.C: 180,
    Licence.D: 180,
}


@dataclass(frozen=True)
class Currency:
    licence: Licence
    days: int | None  # None without a licence
    last_jump_on: date | None
    # The last calendar day the guidance counts as current; None without a licence or jumps.
    current_until: date | None


def currency(licence: Licence, last_jump_on: date | None) -> Currency:
    days = RECURRENCY_DAYS.get(licence)
    until = (
        last_jump_on + timedelta(days=days)
        if days is not None and last_jump_on is not None
        else None
    )
    return Currency(licence, days, last_jump_on, until)


def is_current(c: Currency, today: date) -> bool | None:
    """On the jumper's own calendar day `today`; None when there is nothing to judge."""
    if c.current_until is None:
        return None
    return today <= c.current_until
