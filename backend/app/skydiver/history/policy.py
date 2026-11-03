"""Personal history totals (#154) as plain values. No framework or persistence imports.

B is the owner's self-declared number of jumps completed before calendar date D.
R is the number of distinct detailed entries; A those dated on or after D.

- Without a baseline only R is reported, labelled as recorded entries. A lifetime
  total is never inferred, not even from the highest jump number.
- With a consistent baseline the reported lifetime total is B + A. Detailed entries
  before D stay history but are already represented by B, so they are not added.
- If the detailed entries before D outnumber B, the inconsistency is flagged and no
  combined total is given until the owner corrects B, D or the entries. Nothing is
  rejected and B is never changed silently.

A baseline is a private self-report: it creates no dated activity, gear use,
currency or eligibility.
"""

from dataclasses import dataclass
from datetime import date

from app.skydiver.directory.policy import DirectoryRuleError as RuleError
from app.skydiver.logbook.policy import EARLIEST

PRIOR_MAX = 100_000  # working limit; above any plausible personal total
MONTHS = 12  # recent activity: calendar months, newest last


@dataclass(frozen=True)
class Baseline:
    prior_jumps: int
    before_on: date


@dataclass(frozen=True)
class Totals:
    recorded: int
    baseline: Baseline | None
    recorded_before: int | None  # detailed entries before D (already within B)
    recorded_since: int | None  # detailed entries on or after D
    lifetime: int | None  # None without a baseline or when inconsistent
    inconsistent: bool


def baseline(prior_jumps: int, before_on: date, today: date) -> Baseline:
    """Validate a declaration. `today` is the latest calendar date anywhere."""
    if not 0 <= prior_jumps <= PRIOR_MAX:
        raise RuleError("prior_jumps_invalid")
    if before_on > today:
        raise RuleError("baseline_date_in_future")
    if before_on < EARLIEST:
        raise RuleError("baseline_date_invalid")
    return Baseline(prior_jumps, before_on)


def totals(recorded: int, recorded_before: int, base: Baseline | None) -> Totals:
    """`recorded_before` counts detailed entries dated before the baseline date."""
    if not 0 <= recorded_before <= recorded:
        raise ValueError("recorded_before must be within 0..recorded")
    if base is None:
        return Totals(recorded, None, None, None, None, False)
    since = recorded - recorded_before
    inconsistent = recorded_before > base.prior_jumps
    return Totals(
        recorded=recorded,
        baseline=base,
        recorded_before=recorded_before,
        recorded_since=since,
        lifetime=None if inconsistent else base.prior_jumps + since,
        inconsistent=inconsistent,
    )


def recent_months(latest: date, count: int = MONTHS) -> list[str]:
    """The `count` calendar months ending with `latest`'s month, as YYYY-MM, oldest first."""
    year, month = latest.year, latest.month
    months: list[str] = []
    for _ in range(count):
        months.append(f"{year:04d}-{month:02d}")
        year, month = (year, month - 1) if month > 1 else (year - 1, 12)
    return months[::-1]
