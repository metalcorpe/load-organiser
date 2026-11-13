"""Wing loading from the jumper's own entries. Plain values, no I/O.

Wing loading is the exit weight in pounds divided by the main canopy's size in
square feet. Exit weight (body and gear) is the jumper's own figure: a per-jump
value when the jump has one, else their usual exit weight. The canopy is the main
canopy recorded on the jump, with the size entered for it under Gear.

Nothing here is advice: no limit, recommendation or manufacturer or association
figure is applied. When a value is missing the loading is unknown, never guessed,
and the reasons say what is missing.
"""

from collections import Counter
from collections.abc import Iterable
from dataclasses import dataclass
from datetime import date
from decimal import ROUND_HALF_UP, Decimal
from enum import StrEnum

from app.skydiver.directory.policy import DirectoryRuleError as RuleError

GRAMS_PER_POUND = Decimal("453.59237")  # exact, by definition
GRAMS_PER_KILOGRAM = Decimal(1000)
WEIGHT_MIN_GRAMS = 30_000
WEIGHT_MAX_GRAMS = 250_000
LOADING_MONTHS = 24  # History's chart: the latest months with a known loading
_CENTS = Decimal("0.01")
_TENTHS = Decimal("0.1")


class WeightUnit(StrEnum):
    KG = "kg"
    LB = "lb"


class Missing(StrEnum):
    """What a jump lacks for a wing loading, in the order it is reported."""

    EXIT_WEIGHT = "exit_weight"  # neither the jump's nor the usual exit weight
    MAIN_CANOPY = "main_canopy"  # no main canopy recorded on the jump
    CANOPY_SIZE = "canopy_size"  # the recorded main has no size entered
    SEVERAL_MAINS = "several_mains"  # more than one main recorded: which is unclear


@dataclass(frozen=True)
class Loading:
    value: Decimal | None  # pounds per square foot, two decimals; None: unknown
    weight_grams: int | None  # the exit weight used
    weight_from_jump: bool  # the jump's own exit weight, not the usual one
    canopy_size: int | None  # square feet of the main used
    missing: tuple[Missing, ...]


def grams(value: Decimal, unit: WeightUnit) -> int:
    """An entered weight in grams, rounded to the gram, within the working range."""
    if not value.is_finite() or value <= 0:
        raise RuleError("exit_weight_invalid")
    per = GRAMS_PER_KILOGRAM if unit is WeightUnit.KG else GRAMS_PER_POUND
    result = int((value * per).quantize(Decimal(1), rounding=ROUND_HALF_UP))
    if not WEIGHT_MIN_GRAMS <= result <= WEIGHT_MAX_GRAMS:
        raise RuleError("exit_weight_invalid")
    return result


def exit_weight_grams(value: int | None) -> int | None:
    """A stored exit weight: whole grams from 30 kg to 250 kg, or none."""
    if value is None:
        return None
    if not WEIGHT_MIN_GRAMS <= value <= WEIGHT_MAX_GRAMS:
        raise RuleError("exit_weight_invalid")
    return value


def in_unit(weight_grams: int, unit: WeightUnit) -> Decimal:
    """A stored weight in the jumper's unit, to one decimal (as entered)."""
    per = GRAMS_PER_KILOGRAM if unit is WeightUnit.KG else GRAMS_PER_POUND
    return (Decimal(weight_grams) / per).quantize(_TENTHS, rounding=ROUND_HALF_UP)


def wing_loading(
    jump_weight: int | None, usual_weight: int | None, main_sizes: list[int | None]
) -> Loading:
    """The loading of one jump. `main_sizes` holds the size (or None) of each main
    canopy recorded on it."""
    weight = jump_weight if jump_weight is not None else usual_weight
    missing: list[Missing] = []
    if weight is None:
        missing.append(Missing.EXIT_WEIGHT)
    size: int | None = None
    if not main_sizes:
        missing.append(Missing.MAIN_CANOPY)
    elif len(main_sizes) > 1:
        missing.append(Missing.SEVERAL_MAINS)
    elif main_sizes[0] is None:
        missing.append(Missing.CANOPY_SIZE)
    else:
        size = main_sizes[0]
    value = None
    if weight is not None and size is not None:
        value = (Decimal(weight) / GRAMS_PER_POUND / size).quantize(
            _CENTS, rounding=ROUND_HALF_UP
        )
    return Loading(value, weight, jump_weight is not None, size, tuple(missing))


@dataclass(frozen=True)
class Inputs:
    """What one jump holds for its loading, as the store reads it."""

    weight_grams: int | None  # the jump's own exit weight
    mains: int  # main canopies recorded on it
    main_size: int | None  # the size of the main when exactly one is recorded


def of(row: Inputs, usual_weight: int | None) -> Loading:
    sizes: list[int | None] = [row.main_size] if row.mains == 1 else [None] * row.mains
    return wing_loading(row.weight_grams, usual_weight, sizes)


def highest(loadings: Iterable[Loading]) -> Decimal | None:
    known = [x.value for x in loadings if x.value is not None]
    return max(known) if known else None


@dataclass(frozen=True)
class LoadingRange:
    lowest: Decimal | None
    highest: Decimal | None
    known: int
    unknown: int
    missing: list[tuple[Missing, int]]  # entries lacking each, in Missing order


def loading_range(loadings: Iterable[Loading]) -> LoadingRange:
    known: list[Decimal] = []
    unknown = 0
    reasons: Counter[Missing] = Counter()
    for item in loadings:
        if item.value is not None:
            known.append(item.value)
        else:
            unknown += 1
            reasons.update(item.missing)
    return LoadingRange(
        lowest=min(known) if known else None,
        highest=max(known) if known else None,
        known=len(known),
        unknown=unknown,
        missing=[(m, reasons[m]) for m in Missing if reasons[m]],
    )


def loading_by_month(
    entries: Iterable[tuple[date, Loading]], count: int = LOADING_MONTHS
) -> list[tuple[str, Decimal, int]]:
    """(YYYY-MM, highest loading jumped, entries with a loading) for the latest
    `count` months that have one, oldest first. Months without one are left out."""
    months: dict[str, list[Decimal]] = {}
    for on, item in entries:
        if item.value is not None:
            months.setdefault(f"{on.year:04d}-{on.month:02d}", []).append(item.value)
    latest = sorted(months)[-count:] if count else []
    return [(m, max(months[m]), len(months[m])) for m in latest]
