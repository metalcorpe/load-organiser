"""Provider and opportunity rules (#149). Plain values only; no FastAPI, SQL or settings.

- A provider (person or organisation offering an activity) is distinct from a venue.
  Management authority, qualifications and affiliations are not modelled here.
- An opportunity is a dated event, boogie, camp or course: one provider (organiser),
  an optional public venue, and a sourced schedule in an IANA time zone. Ongoing
  coach/school offers are later scope (beta decisions), so every public opportunity
  is dated or explicitly postponed with dates not yet known.
- Registration and contact happen through the original external link. Nothing here
  records capacity, availability, acceptance or bookings.
- Date-only end dates are inclusive in the schedule's zone. An opportunity leaves
  upcoming results when its end date has passed there; unknown dates never expire.
"""

from dataclasses import dataclass
from datetime import UTC, date, datetime, time, timedelta
from decimal import Decimal, InvalidOperation
from enum import StrEnum
from functools import cache
from typing import Any
from zoneinfo import ZoneInfo, available_timezones

from app.skydiver.directory.policy import DirectoryRuleError as RuleError
from app.skydiver.directory.policy import clean_text
from app.skydiver.opportunities.languages import ISO_LANGUAGES

TITLE_MAX = 160
SUMMARY_MAX = 500
PREREQUISITES_MAX = 1000
LOCATION_NOTE_MAX = 200
PRICE_NOTE_MAX = 280
PRICE_MAX = Decimal("100000")
PRICE_TIERS_MAX = 6
PRICE_TIER_LABEL_MAX = 60
SPAN_MAX_DAYS = 366
LANGUAGES_MAX = 8
UNKNOWN_SORT_DATE = date(9999, 12, 31)  # postponed with no dates: listed last

# Review cadence (release brief, operating defaults, not measured workload):
# public listings starting within SOON_DAYS are due a check after
# SOON_RECHECK_DAYS; postponed ones after POSTPONED_RECHECK_DAYS; published
# organizer profiles after PROFILE_RECHECK_DAYS.
SOON_DAYS = 30
SOON_RECHECK_DAYS = 7
POSTPONED_RECHECK_DAYS = 7
PROFILE_RECHECK_DAYS = 60


class ProviderKind(StrEnum):
    ORGANIZATION = "organization"
    PERSON = "person"


class ProviderStatus(StrEnum):
    DRAFT = "draft"
    PUBLISHED = "published"
    ARCHIVED = "archived"
    MERGED = "merged"


class Category(StrEnum):
    EVENT = "event"
    BOOGIE = "boogie"
    CAMP = "camp"
    COURSE = "course"


class Discipline(StrEnum):
    BELLY = "belly"
    FREEFLY = "freefly"
    ANGLE = "angle"
    WINGSUIT = "wingsuit"
    CANOPY = "canopy"
    CRW = "crw"
    ACCURACY = "accuracy"


class Audience(StrEnum):
    STUDENTS = "students"  # not yet licensed
    LICENSED = "licensed"
    EXPERIENCED = "experienced"  # stated experience requirements beyond a licence


class PriceBasis(StrEnum):
    PER_PERSON = "per_person"  # the whole offering
    PER_JUMP = "per_jump"
    PER_DAY = "per_day"


class OpportunityStatus(StrEnum):
    DRAFT = "draft"
    REVIEW = "review"  # awaiting the maintainer's review
    PUBLISHED = "published"
    POSTPONED = "postponed"
    CANCELLED = "cancelled"
    ARCHIVED = "archived"  # withdrawn from public view
    DUPLICATE = "duplicate"  # consolidated into `duplicate_of`


PUBLIC_PROVIDER_STATUSES = frozenset({ProviderStatus.PUBLISHED})
PUBLIC_STATUSES = frozenset(
    {
        OpportunityStatus.PUBLISHED,
        OpportunityStatus.POSTPONED,
        OpportunityStatus.CANCELLED,
    }
)
# Cancellation and publication keep their dates; postponement may not know new ones.
DATED_STATUSES = frozenset({OpportunityStatus.PUBLISHED, OpportunityStatus.CANCELLED})

_TRANSITIONS: dict[OpportunityStatus, frozenset[OpportunityStatus]] = {
    OpportunityStatus.DRAFT: frozenset(
        {OpportunityStatus.REVIEW, OpportunityStatus.ARCHIVED}
    ),
    OpportunityStatus.REVIEW: frozenset(
        {
            OpportunityStatus.DRAFT,
            OpportunityStatus.PUBLISHED,
            OpportunityStatus.ARCHIVED,
        }
    ),
    OpportunityStatus.PUBLISHED: frozenset(
        {
            OpportunityStatus.POSTPONED,
            OpportunityStatus.CANCELLED,
            OpportunityStatus.ARCHIVED,
        }
    ),
    OpportunityStatus.POSTPONED: frozenset(
        {
            OpportunityStatus.PUBLISHED,
            OpportunityStatus.CANCELLED,
            OpportunityStatus.ARCHIVED,
        }
    ),
    OpportunityStatus.CANCELLED: frozenset({OpportunityStatus.ARCHIVED}),
    OpportunityStatus.ARCHIVED: frozenset({OpportunityStatus.DRAFT}),
    OpportunityStatus.DUPLICATE: frozenset(),
}

_PROVIDER_TRANSITIONS: dict[ProviderStatus, frozenset[ProviderStatus]] = {
    ProviderStatus.DRAFT: frozenset(
        {ProviderStatus.PUBLISHED, ProviderStatus.ARCHIVED}
    ),
    ProviderStatus.PUBLISHED: frozenset({ProviderStatus.ARCHIVED}),
    ProviderStatus.ARCHIVED: frozenset(
        {ProviderStatus.DRAFT, ProviderStatus.PUBLISHED}
    ),
    ProviderStatus.MERGED: frozenset(),
}

# Currencies accepted for a stated price: European currencies plus USD. Display only;
# no conversion, payment or comparison is implied.
CURRENCIES = frozenset(
    "EUR GBP CHF NOK SEK DKK ISK PLN CZK HUF RON BGN RSD BAM MKD ALL MDL UAH TRY GEL USD".split()
)


def check_transition(current: OpportunityStatus, new: OpportunityStatus) -> None:
    """Duplicates are consolidated through their own action and are final."""
    if new is OpportunityStatus.DUPLICATE or new not in _TRANSITIONS[current]:
        raise RuleError("status_change_invalid")


def check_provider_transition(current: ProviderStatus, new: ProviderStatus) -> None:
    if new is ProviderStatus.MERGED or new not in _PROVIDER_TRANSITIONS[current]:
        raise RuleError("status_change_invalid")


def tags[T: StrEnum](values: list[str], kind: type[T], *, field: str) -> list[str]:
    """Distinct known values in a stable order; an empty list means 'not stated'."""
    try:
        chosen = {kind(v) for v in values}
    except ValueError as error:
        raise RuleError(f"{field}_invalid") from error
    return [member.value for member in kind if member in chosen]


def languages(values: list[str]) -> list[str]:
    codes = sorted({v.strip().lower() for v in values})
    if any(code not in ISO_LANGUAGES for code in codes):
        raise RuleError("languages_invalid")
    if len(codes) > LANGUAGES_MAX:
        raise RuleError("languages_too_many")
    return codes


@cache
def _zones() -> frozenset[str]:
    return frozenset(available_timezones())


def time_zone(value: str) -> str:
    zone = value.strip()
    if zone not in _zones() or zone.startswith(("Etc/", "SystemV/")) or "/" not in zone:
        # Require a location zone (Europe/Madrid), not an offset alias or 'UTC'.
        raise RuleError("time_zone_invalid")
    return zone


@dataclass(frozen=True)
class Schedule:
    starts_on: date | None
    ends_on: date | None
    time_zone: str | None


def schedule(
    starts_on: date | None, ends_on: date | None, zone: str | None
) -> Schedule:
    """Both dates or neither; known dates need the zone that interprets them."""
    if (starts_on is None) != (ends_on is None):
        raise RuleError("dates_incomplete")
    clean_zone = time_zone(zone) if zone else None
    if starts_on is None or ends_on is None:
        return Schedule(None, None, clean_zone)
    if ends_on < starts_on:
        raise RuleError("dates_out_of_order")
    if (ends_on - starts_on).days >= SPAN_MAX_DAYS:
        raise RuleError("dates_span_too_long")
    if clean_zone is None:
        raise RuleError("time_zone_required")
    return Schedule(starts_on, ends_on, clean_zone)


def expires_at(ends_on: date | None, zone: str | None) -> datetime | None:
    """The instant the inclusive end date is over in the schedule's zone."""
    if ends_on is None or zone is None:
        return None
    local = datetime.combine(ends_on + timedelta(days=1), time(0), ZoneInfo(zone))
    return local.astimezone(UTC)


def sort_on(starts_on: date | None) -> date:
    return starts_on or UNKNOWN_SORT_DATE


@dataclass(frozen=True)
class Price:
    amount: Decimal | None
    currency: str | None
    basis: PriceBasis | None


def price(
    amount: Decimal | float | str | None, currency: str | None, basis: str | None
) -> Price:
    """A stated price needs its currency and basis. Unknown price is all None."""
    if amount is None:
        if currency or basis:
            raise RuleError("price_incomplete")
        return Price(None, None, None)
    if not currency or not basis:
        raise RuleError("price_incomplete")
    return _stated_price(amount, currency, basis)


def _stated_price(amount: Decimal | float | str, currency: str, basis: str) -> Price:
    try:
        value = Decimal(str(amount)).quantize(Decimal("0.01"))
    except (InvalidOperation, ValueError) as error:
        raise RuleError("price_invalid") from error
    if not (Decimal(0) <= value <= PRICE_MAX):
        raise RuleError("price_invalid")
    code = currency.strip().upper()
    if code not in CURRENCIES:
        raise RuleError("currency_invalid")
    try:
        return Price(value, code, PriceBasis(basis))
    except ValueError as error:
        raise RuleError("price_basis_invalid") from error


@dataclass(frozen=True)
class PriceTier:
    """One stated charge: what it pays for, how much, and the dates it applies.

    `from_on`/`until_on` are inclusive calendar dates in the opportunity's time zone;
    None means open-ended. `optional` marks an extra the jumper may skip.
    """

    label: str
    amount: Decimal
    currency: str
    basis: PriceBasis
    from_on: date | None
    until_on: date | None
    optional: bool

    def as_json(self) -> dict[str, Any]:
        return {
            "label": self.label,
            "amount": f"{self.amount:.2f}",
            "currency": self.currency,
            "basis": self.basis.value,
            "from_on": self.from_on.isoformat() if self.from_on else None,
            "until_on": self.until_on.isoformat() if self.until_on else None,
            "optional": self.optional,
        }


_TIER_KEYS = frozenset(
    {"label", "amount", "currency", "basis", "from_on", "until_on", "optional"}
)


def _tier_date(value: object) -> date | None:
    if value is None:
        return None
    if isinstance(value, datetime):
        raise RuleError("price_tiers_invalid")
    if isinstance(value, date):
        return value
    if isinstance(value, str):
        try:
            return date.fromisoformat(value)
        except ValueError as error:
            raise RuleError("price_tiers_invalid") from error
    raise RuleError("price_tiers_invalid")


def _price_tier(raw: object) -> PriceTier:
    if not isinstance(raw, dict) or not set(raw) <= _TIER_KEYS:
        raise RuleError("price_tiers_invalid")
    label, amount = raw.get("label"), raw.get("amount")
    currency, basis = raw.get("currency"), raw.get("basis")
    optional = raw.get("optional", False)
    if not isinstance(label, str) or not isinstance(optional, bool):
        raise RuleError("price_tiers_invalid")
    if not isinstance(currency, str) or not isinstance(basis, str):
        raise RuleError("price_tiers_invalid")
    if amount is None or isinstance(amount, bool):
        raise RuleError("price_invalid")
    if not isinstance(amount, Decimal | int | float | str):
        raise RuleError("price_invalid")
    clean_label = clean_text(
        label, field="price_tier_label", maximum=PRICE_TIER_LABEL_MAX
    )
    stated = _stated_price(amount, currency, basis)
    assert stated.amount is not None and stated.currency and stated.basis
    from_on, until_on = _tier_date(raw.get("from_on")), _tier_date(raw.get("until_on"))
    if from_on and until_on and from_on > until_on:
        raise RuleError("price_tier_dates_out_of_order")
    return PriceTier(
        clean_label, stated.amount, stated.currency, stated.basis, from_on, until_on,
        optional,
    )  # fmt: skip


def price_tiers(
    raw: object,
    *,
    time_zone: str | None = None,
    price_amount: Decimal | float | str | None = None,
) -> list[PriceTier]:
    """Dated or separate charges that replace the single stated price.

    A listing states one price, a list of tiers, or neither. Tier dates are read in
    the opportunity's zone, so any dated tier needs one. Order is kept as given.
    """
    if raw is None:
        return []
    if not isinstance(raw, list | tuple):
        raise RuleError("price_tiers_invalid")
    if len(raw) > PRICE_TIERS_MAX:
        raise RuleError("price_tiers_too_many")
    tiers = [_price_tier(item) for item in raw]
    if tiers and price_amount is not None:
        raise RuleError("price_tiers_with_amount")
    if time_zone is None and any(t.from_on or t.until_on for t in tiers):
        raise RuleError("price_tier_zone_required")
    return tiers


@dataclass(frozen=True)
class PublicationFacts:
    status: OpportunityStatus
    has_source: bool
    has_registration: bool
    has_dates: bool
    has_location: bool  # a public venue or an explicit location note
    provider_public: bool


def check_publishable(facts: PublicationFacts) -> None:
    """Public opportunities are sourced, organised, located and externally reachable."""
    if facts.status not in PUBLIC_STATUSES:
        return
    if not facts.has_source:
        raise RuleError("source_required")
    if not facts.has_registration:
        raise RuleError("registration_url_required")
    if not facts.provider_public:
        raise RuleError("provider_not_published")
    if not facts.has_location:
        raise RuleError("location_required")
    if facts.status in DATED_STATUSES and not facts.has_dates:
        raise RuleError("schedule_required")


@dataclass(frozen=True)
class DuplicateCheck:
    source_status: OpportunityStatus
    target_status: OpportunityStatus
    same: bool


def check_duplicate(check: DuplicateCheck) -> None:
    """Consolidate one listing into another; a public listing must stay resolvable."""
    if check.same:
        raise RuleError("duplicate_of_self")
    if OpportunityStatus.DUPLICATE in (check.source_status, check.target_status):
        raise RuleError("duplicate_already_consolidated")
    if (
        check.source_status in PUBLIC_STATUSES
        and check.target_status not in PUBLIC_STATUSES
    ):
        raise RuleError("duplicate_target_not_public")


@dataclass(frozen=True)
class ProviderMergeCheck:
    source_status: ProviderStatus
    target_status: ProviderStatus
    same: bool


def check_provider_merge(check: ProviderMergeCheck) -> None:
    if check.same:
        raise RuleError("merge_into_self")
    if ProviderStatus.MERGED in (check.source_status, check.target_status):
        raise RuleError("merge_already_merged")
    if (
        check.source_status in PUBLIC_PROVIDER_STATUSES
        and check.target_status not in PUBLIC_PROVIDER_STATUSES
    ):
        raise RuleError("merge_target_not_public")
