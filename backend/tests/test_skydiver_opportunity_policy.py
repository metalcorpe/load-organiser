"""#149 provider/opportunity rules as plain values (no database)."""

import ast
import pathlib
from datetime import UTC, date, datetime
from decimal import Decimal

import pytest

from app.skydiver.directory.policy import DirectoryRuleError
from app.skydiver.opportunities import policy
from app.skydiver.opportunities.policy import (
    Discipline,
)
from app.skydiver.opportunities.policy import (
    OpportunityStatus as S,
)
from app.skydiver.opportunities.policy import (
    ProviderStatus as P,
)


def code(error: pytest.ExceptionInfo[DirectoryRuleError]) -> str:
    return error.value.code


def test_policy_imports_no_framework_or_persistence() -> None:
    source = pathlib.Path(policy.__file__).read_text()
    imported = {
        (node.module or "").split(".")[0]
        for node in ast.walk(ast.parse(source))
        if isinstance(node, ast.ImportFrom)
    } | {
        alias.name.split(".")[0]
        for node in ast.walk(ast.parse(source))
        if isinstance(node, ast.Import)
        for alias in node.names
    }
    assert not imported & {"fastapi", "sqlalchemy", "sqlmodel", "pydantic"}


@pytest.mark.parametrize(
    ("current", "new"),
    [
        (S.DRAFT, S.REVIEW),
        (S.REVIEW, S.PUBLISHED),
        (S.REVIEW, S.DRAFT),
        (S.PUBLISHED, S.POSTPONED),
        (S.PUBLISHED, S.CANCELLED),
        (S.POSTPONED, S.PUBLISHED),
        (S.POSTPONED, S.CANCELLED),
        (S.CANCELLED, S.ARCHIVED),
        (S.ARCHIVED, S.DRAFT),
    ],
)
def test_allowed_transitions(current: S, new: S) -> None:
    policy.check_transition(current, new)


@pytest.mark.parametrize(
    ("current", "new"),
    [
        (S.DRAFT, S.PUBLISHED),  # publication goes through review
        (S.PUBLISHED, S.DRAFT),
        (S.CANCELLED, S.PUBLISHED),
        (S.ARCHIVED, S.PUBLISHED),
        (S.PUBLISHED, S.DUPLICATE),  # only through the duplicate action
        (S.DUPLICATE, S.DRAFT),
    ],
)
def test_refused_transitions(current: S, new: S) -> None:
    with pytest.raises(DirectoryRuleError) as error:
        policy.check_transition(current, new)
    assert code(error) == "status_change_invalid"


def test_provider_transitions() -> None:
    policy.check_provider_transition(P.DRAFT, P.PUBLISHED)
    policy.check_provider_transition(P.ARCHIVED, P.PUBLISHED)
    for current, new in [(P.PUBLISHED, P.MERGED), (P.MERGED, P.DRAFT)]:
        with pytest.raises(DirectoryRuleError):
            policy.check_provider_transition(current, new)


def facts(**overrides: object) -> policy.PublicationFacts:
    values: dict[str, object] = {
        "status": S.PUBLISHED,
        "has_source": True,
        "has_registration": True,
        "has_dates": True,
        "has_location": True,
        "provider_public": True,
    }
    return policy.PublicationFacts(**{**values, **overrides})  # type: ignore[arg-type]


@pytest.mark.parametrize(
    ("missing", "expected"),
    [
        ("has_source", "source_required"),
        ("has_registration", "registration_url_required"),
        ("provider_public", "provider_not_published"),
        ("has_location", "location_required"),
        ("has_dates", "schedule_required"),
    ],
)
def test_publication_requires_each_fact(missing: str, expected: str) -> None:
    with pytest.raises(DirectoryRuleError) as error:
        policy.check_publishable(facts(**{missing: False}))
    assert code(error) == expected


def test_postponed_may_lack_dates_but_cancelled_may_not() -> None:
    policy.check_publishable(facts(status=S.POSTPONED, has_dates=False))
    with pytest.raises(DirectoryRuleError):
        policy.check_publishable(facts(status=S.CANCELLED, has_dates=False))
    # Drafts are not checked.
    policy.check_publishable(facts(status=S.DRAFT, has_source=False, has_dates=False))


def test_schedule_rules() -> None:
    day = date(2026, 6, 1)
    assert policy.schedule(None, None, None) == policy.Schedule(None, None, None)
    assert policy.schedule(day, day, "Europe/Madrid").time_zone == "Europe/Madrid"
    cases = [
        ((day, None, "Europe/Madrid"), "dates_incomplete"),
        ((day, date(2026, 5, 31), "Europe/Madrid"), "dates_out_of_order"),
        ((day, date(2027, 6, 2), "Europe/Madrid"), "dates_span_too_long"),
        ((day, day, None), "time_zone_required"),
        ((day, day, "Mars/Olympus"), "time_zone_invalid"),
        ((day, day, "UTC"), "time_zone_invalid"),
        ((day, day, "Etc/GMT-2"), "time_zone_invalid"),
    ]
    for args, expected in cases:
        with pytest.raises(DirectoryRuleError) as error:
            policy.schedule(*args)
        assert code(error) == expected, args


def test_expiry_uses_the_inclusive_end_in_the_schedule_zone() -> None:
    end = date(2026, 11, 3)
    # Madrid is UTC+1 in November: the day ends at 23:00 UTC.
    assert policy.expires_at(end, "Europe/Madrid") == datetime(
        2026, 11, 3, 23, 0, tzinfo=UTC
    )
    # Kiritimati (UTC+14) finishes the same calendar date 13 hours earlier.
    assert policy.expires_at(end, "Pacific/Kiritimati") == datetime(
        2026, 11, 3, 10, 0, tzinfo=UTC
    )
    # Across a DST change (Europe/Madrid leaves summer time on 2026-10-25).
    assert policy.expires_at(date(2026, 10, 24), "Europe/Madrid") == datetime(
        2026, 10, 24, 22, 0, tzinfo=UTC
    )
    assert policy.expires_at(None, None) is None


def test_unknown_dates_sort_last_and_never_expire() -> None:
    assert policy.sort_on(None) == policy.UNKNOWN_SORT_DATE
    assert policy.expires_at(None, "Europe/Madrid") is None


def test_price_rules() -> None:
    assert policy.price(None, None, None) == policy.Price(None, None, None)
    stated = policy.price("1250.5", "eur", "per_person")
    assert stated == policy.Price(
        Decimal("1250.50"), "EUR", policy.PriceBasis.PER_PERSON
    )
    cases = [
        ((None, "EUR", None), "price_incomplete"),
        (("10", "EUR", None), "price_incomplete"),
        (("10", "XYZ", "per_jump"), "currency_invalid"),
        (("-1", "EUR", "per_jump"), "price_invalid"),
        (("abc", "EUR", "per_jump"), "price_invalid"),
        (("10", "EUR", "per_hour"), "price_basis_invalid"),
    ]
    for args, expected in cases:
        with pytest.raises(DirectoryRuleError) as error:
            policy.price(*args)
        assert code(error) == expected, args


def test_tags_and_languages() -> None:
    assert policy.tags(
        ["wingsuit", "belly", "belly"], Discipline, field="disciplines"
    ) == ["belly", "wingsuit"]
    assert policy.tags([], Discipline, field="disciplines") == []
    with pytest.raises(DirectoryRuleError) as error:
        policy.tags(["swoop"], Discipline, field="disciplines")
    assert code(error) == "disciplines_invalid"
    assert policy.languages(["EN", "es", "en"]) == ["en", "es"]
    with pytest.raises(DirectoryRuleError):
        policy.languages(["xx"])
    with pytest.raises(DirectoryRuleError) as error:
        policy.languages(["en", "es", "fr", "de", "it", "pt", "nl", "pl", "cs"])
    assert code(error) == "languages_too_many"


def test_duplicate_and_merge_checks() -> None:
    policy.check_duplicate(policy.DuplicateCheck(S.REVIEW, S.DRAFT, same=False))
    for check, expected in [
        (
            policy.DuplicateCheck(S.PUBLISHED, S.PUBLISHED, same=True),
            "duplicate_of_self",
        ),
        (
            policy.DuplicateCheck(S.DUPLICATE, S.PUBLISHED, same=False),
            "duplicate_already_consolidated",
        ),
        (
            policy.DuplicateCheck(S.PUBLISHED, S.DRAFT, same=False),
            "duplicate_target_not_public",
        ),
    ]:
        with pytest.raises(DirectoryRuleError) as error:
            policy.check_duplicate(check)
        assert code(error) == expected
    with pytest.raises(DirectoryRuleError) as error:
        policy.check_provider_merge(
            policy.ProviderMergeCheck(P.PUBLISHED, P.DRAFT, same=False)
        )
    assert code(error) == "merge_target_not_public"
