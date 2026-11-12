"""#154 prior-history totals and currency guidance as plain values (no database)."""

from datetime import date, timedelta

import pytest

from app.skydiver.directory.policy import DirectoryRuleError
from app.skydiver.history import currency, policy
from app.skydiver.history.policy import Baseline

TODAY = date(2026, 11, 4)


def _code(call: object) -> str:
    with pytest.raises(DirectoryRuleError) as raised:
        call()  # type: ignore[operator]
    return raised.value.code


def test_without_a_baseline_only_recorded_entries_are_reported() -> None:
    t = policy.totals(7, 0, None)
    assert (t.recorded, t.lifetime, t.inconsistent) == (7, None, False)
    assert t.recorded_before is None and t.recorded_since is None


def test_decision_fixture_b200_plus_entries_since_the_cutoff() -> None:
    base = Baseline(200, date(2026, 1, 1))
    # Three detailed entries on/after D: 203.
    assert policy.totals(3, 0, base).lifetime == 203
    # One more detailed entry before D is already within B: still 203.
    t = policy.totals(4, 1, base)
    assert (t.lifetime, t.recorded_before, t.recorded_since) == (203, 1, 3)
    assert not t.inconsistent


def test_more_detailed_entries_before_the_cutoff_than_declared_is_flagged() -> None:
    base = Baseline(2, date(2026, 1, 1))
    assert policy.totals(5, 2, base).lifetime == 5  # exactly B before D is consistent
    t = policy.totals(6, 3, base)
    assert t.inconsistent and t.lifetime is None
    assert t.baseline == base  # B is kept as declared, never inflated
    assert (t.recorded, t.recorded_before, t.recorded_since) == (6, 3, 3)


def test_a_zero_baseline_counts_only_entries_since_the_cutoff() -> None:
    base = Baseline(0, date(2026, 1, 1))
    assert policy.totals(2, 0, base).lifetime == 2
    assert policy.totals(2, 1, base).inconsistent


def test_recorded_before_must_be_within_recorded() -> None:
    with pytest.raises(ValueError):
        policy.totals(1, 2, None)


def test_baseline_validation() -> None:
    assert policy.baseline(0, TODAY, TODAY) == Baseline(0, TODAY)
    assert policy.baseline(policy.PRIOR_MAX, date(1919, 1, 1), TODAY).prior_jumps == (
        policy.PRIOR_MAX
    )
    assert _code(lambda: policy.baseline(-1, TODAY, TODAY)) == "prior_jumps_invalid"
    assert (
        _code(lambda: policy.baseline(policy.PRIOR_MAX + 1, TODAY, TODAY))
        == "prior_jumps_invalid"
    )
    assert (
        _code(lambda: policy.baseline(1, date(2026, 11, 5), TODAY))
        == "baseline_date_in_future"
    )
    assert (
        _code(lambda: policy.baseline(1, date(1918, 12, 31), TODAY))
        == "baseline_date_invalid"
    )


def test_recent_months_cross_the_year() -> None:
    months = policy.recent_months(date(2026, 2, 10), 4)
    assert months == ["2025-11", "2025-12", "2026-01", "2026-02"]
    assert len(policy.recent_months(TODAY)) == 12


# -- currency guidance (USPA SIM 5-2) ---------------------------------------------

LAST = date(2026, 1, 1)


@pytest.mark.parametrize(
    ("licence", "days"),
    [
        (currency.Licence.STUDENT, 30),
        (currency.Licence.A, 60),
        (currency.Licence.B, 90),
        (currency.Licence.C, 180),
        (currency.Licence.D, 180),
    ],
)
def test_each_licence_is_current_through_its_last_day(
    licence: currency.Licence, days: int
) -> None:
    c = currency.currency(licence, LAST)
    assert c.days == days
    assert c.current_until == LAST + timedelta(days=days)
    assert currency.is_current(c, LAST) is True
    assert currency.is_current(c, LAST + timedelta(days=days)) is True  # day N
    assert currency.is_current(c, LAST + timedelta(days=days + 1)) is False  # N + 1


def test_a_licence_boundary_day_60_current_day_61_not() -> None:
    c = currency.currency(currency.Licence.A, date(2026, 3, 1))
    assert c.current_until == date(2026, 4, 30)
    assert currency.is_current(c, date(2026, 4, 30)) is True
    assert currency.is_current(c, date(2026, 5, 1)) is False


def test_no_licence_gives_no_guidance() -> None:
    c = currency.currency(currency.Licence.NONE, LAST)
    assert (c.days, c.current_until) == (None, None)
    assert currency.is_current(c, LAST) is None


def test_no_jumps_gives_no_guidance() -> None:
    c = currency.currency(currency.Licence.B, None)
    assert (c.days, c.last_jump_on, c.current_until) == (90, None, None)
    assert currency.is_current(c, LAST) is None


def test_the_policy_table_covers_every_licence() -> None:
    assert set(currency.RECURRENCY_DAYS) == set(currency.Licence) - {
        currency.Licence.NONE
    }
