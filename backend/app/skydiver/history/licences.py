"""Progress toward the next USPA licence from the owner's own entries. Plain values.

Guidance only, never a licence check: USPA and the jumper's instructors check every
requirement. Only two are counted here, from what the logbook holds:

- jumps: the reported total, which includes a declared prior jump count when the
  baseline is consistent (personal history policy), else the recorded entries;
- freefall time: only entries with a recorded freefall time. A prior jump count
  has no freefall time, so it adds none, and entries without one add none.

Skills, proficiency cards, landing accuracy and endorsements are not counted.
"""

from dataclasses import dataclass
from typing import Literal

from app.skydiver.history.currency import Licence

SOURCE: Literal["USPA SIM 3-1"] = "USPA SIM 3-1"


@dataclass(frozen=True)
class Requirement:
    jumps: int
    freefall_seconds: int  # 0: no freefall time listed


# The one policy table. Source: USPA Skydiver's Information Manual, section 3-1
# (licence requirements): jump numbers and freefall time for each licence. Checked
# 2026-11-12. D is the highest licence: there is no next one.
NEXT_LICENCE: dict[Licence, tuple[Licence, Requirement]] = {
    Licence.STUDENT: (Licence.A, Requirement(jumps=25, freefall_seconds=0)),
    Licence.A: (Licence.B, Requirement(jumps=50, freefall_seconds=30 * 60)),
    Licence.B: (Licence.C, Requirement(jumps=200, freefall_seconds=60 * 60)),
    Licence.C: (Licence.D, Requirement(jumps=500, freefall_seconds=3 * 60 * 60)),
}


@dataclass(frozen=True)
class Progress:
    licence: Licence
    next_licence: Licence | None  # None: D, the highest licence
    requirement: Requirement | None
    jumps: int
    jumps_include_prior: bool  # the declared prior jump count is in `jumps`
    freefall_seconds: int  # recorded entries only
    entries_with_freefall: int
    entries_without_freefall: int

    @property
    def jumps_met(self) -> bool:
        return self.requirement is not None and self.jumps >= self.requirement.jumps

    @property
    def freefall_met(self) -> bool:
        return (
            self.requirement is not None
            and self.freefall_seconds >= self.requirement.freefall_seconds
        )


def progress(
    licence: Licence,
    *,
    jumps: int,
    jumps_include_prior: bool,
    freefall_seconds: int,
    entries_with_freefall: int,
    entries_without_freefall: int,
) -> Progress | None:
    """None without a licence: nothing beyond the prompt to set one."""
    if licence is Licence.NONE:
        return None
    step = NEXT_LICENCE.get(licence)
    return Progress(
        licence=licence,
        next_licence=step[0] if step else None,
        requirement=step[1] if step else None,
        jumps=jumps,
        jumps_include_prior=jumps_include_prior,
        freefall_seconds=freefall_seconds,
        entries_with_freefall=entries_with_freefall,
        entries_without_freefall=entries_without_freefall,
    )
