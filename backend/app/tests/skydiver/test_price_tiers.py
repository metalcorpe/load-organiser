"""Opportunity price tiers: dated and separate charges (policy rules only)."""

from datetime import date
from decimal import Decimal
from typing import Any

import pytest

from app.skydiver.directory.policy import DirectoryRuleError
from app.skydiver.opportunities import policy
from app.skydiver.opportunities.policy import PriceBasis, PriceTier

ZONE = "Europe/Madrid"


def tier(**extra: Any) -> dict[str, Any]:
    return {
        "label": "Registration",
        "amount": "80",
        "currency": "EUR",
        "basis": "per_person",
        **extra,
    }


def refused(raw: Any, code: str, **context: Any) -> None:
    with pytest.raises(DirectoryRuleError) as caught:
        policy.price_tiers(raw, **context)
    assert caught.value.code == code


def test_tiers_are_cleaned_and_keep_their_order() -> None:
    tiers = policy.price_tiers(
        [
            tier(label="  Registration \n fee ", until_on="2026-11-14"),
            tier(amount=Decimal("95"), from_on=date(2026, 11, 15)),
            tier(
                label="Load organising",
                amount=4.8,
                currency=" eur",
                basis="per_jump",
                optional=True,
            ),
        ],  # fmt: skip
        time_zone=ZONE,
    )
    assert tiers == [
        PriceTier("Registration fee", Decimal("80.00"), "EUR", PriceBasis.PER_PERSON,
                  None, date(2026, 11, 14), False),
        PriceTier("Registration", Decimal("95.00"), "EUR", PriceBasis.PER_PERSON,
                  date(2026, 11, 15), None, False),
        PriceTier("Load organising", Decimal("4.80"), "EUR", PriceBasis.PER_JUMP,
                  None, None, True),
    ]  # fmt: skip
    assert tiers[2].as_json() == {
        "label": "Load organising", "amount": "4.80", "currency": "EUR",
        "basis": "per_jump", "from_on": None, "until_on": None, "optional": True,
    }  # fmt: skip
    # Stored JSON validates back to the same tiers.
    stored = [t.as_json() for t in tiers]
    assert policy.price_tiers(stored, time_zone=ZONE) == tiers


def test_no_tiers() -> None:
    assert policy.price_tiers(None) == []
    assert policy.price_tiers([]) == []
    # An empty list never conflicts with a single price.
    assert policy.price_tiers([], price_amount=Decimal("80")) == []


def test_undated_tiers_need_no_zone_and_a_single_day_is_allowed() -> None:
    assert len(policy.price_tiers([tier()])) == 1
    one_day = policy.price_tiers(
        [tier(from_on="2026-12-24", until_on="2026-12-24")], time_zone=ZONE
    )
    assert one_day[0].from_on == one_day[0].until_on == date(2026, 12, 24)


def test_at_most_six() -> None:
    assert len(policy.price_tiers([tier()] * policy.PRICE_TIERS_MAX)) == 6
    refused([tier()] * 7, "price_tiers_too_many")


@pytest.mark.parametrize(
    "raw",
    [
        "Registration 80 EUR",
        {"label": "Registration"},
        ["Registration"],
        [tier(extra="field")],
        [{"amount": "80", "currency": "EUR", "basis": "per_person"}],  # no label
        [tier(label=80)],
        [tier(currency=None)],
        [tier(basis=None)],
        [tier(optional="yes")],
        [tier(from_on="14/11/2026")],
        [tier(until_on=20261114)],
        [tier(from_on="2026-11-14T00:00:00")],
    ],
)
def test_bad_shape(raw: Any) -> None:
    refused(raw, "price_tiers_invalid", time_zone=ZONE)


@pytest.mark.parametrize(
    ("label", "code"),
    [
        ("", "price_tier_label_required"),
        (" \t ", "price_tier_label_required"),
        ("x" * 61, "price_tier_label_too_long"),
    ],
)
def test_label(label: str, code: str) -> None:
    refused([tier(label=label)], code)


def test_label_limit_counts_collapsed_whitespace() -> None:
    label = "x" * 30 + "     " + "y" * 29  # 60 once collapsed
    assert len(policy.price_tiers([tier(label=label)])[0].label) == 60


@pytest.mark.parametrize(
    ("change", "code"),
    [
        ({"amount": "-0.01"}, "price_invalid"),
        ({"amount": "100000.01"}, "price_invalid"),
        ({"amount": "eighty"}, "price_invalid"),
        ({"amount": None}, "price_invalid"),
        ({"amount": True}, "price_invalid"),
        ({"currency": "RUB"}, "currency_invalid"),
        ({"currency": ""}, "currency_invalid"),
        ({"basis": "per_hour"}, "price_basis_invalid"),
    ],
)
def test_amount_currency_and_basis_follow_the_single_price_rules(
    change: dict[str, Any], code: str
) -> None:
    refused([tier(**change)], code)


def test_dates_in_order() -> None:
    refused(
        [tier(from_on="2026-11-15", until_on="2026-11-14")],
        "price_tier_dates_out_of_order",
        time_zone=ZONE,
    )


@pytest.mark.parametrize(
    "dates", [{"from_on": "2026-11-15"}, {"until_on": "2026-11-14"}]
)
def test_dated_tiers_need_the_listing_zone(dates: dict[str, str]) -> None:
    refused([tier(), tier(**dates)], "price_tier_zone_required")
    assert policy.price_tiers([tier(**dates)], time_zone=ZONE)


def test_tiers_replace_the_single_price() -> None:
    refused([tier()], "price_tiers_with_amount", price_amount=Decimal("80"))
    refused([tier()], "price_tiers_with_amount", price_amount="0")
