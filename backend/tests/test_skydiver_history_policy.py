"""#154 prior-history totals and currency guidance as plain values (no database)."""

from datetime import date, timedelta

import pytest

from app.skydiver.directory.policy import DirectoryRuleError
from app.skydiver.history import currency, licences, policy
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


# -- progress toward the next licence (USPA SIM 3-1) ------------------------------

L = currency.Licence


def _progress(
    licence: currency.Licence, jumps: int, minutes: int, *, without: int = 0,
    prior: bool = False,
) -> licences.Progress | None:  # fmt: skip
    return licences.progress(
        licence, jumps=jumps, jumps_include_prior=prior,
        freefall_seconds=minutes * 60, entries_with_freefall=jumps - without,
        entries_without_freefall=without,
    )  # fmt: skip


def test_the_licence_table_follows_uspa_sim_3_1() -> None:
    assert licences.SOURCE == "USPA SIM 3-1"
    table = {k: (v[0], v[1].jumps, v[1].freefall_seconds) for k, v in licences.NEXT_LICENCE.items()}  # fmt: skip
    assert table == {
        L.STUDENT: (L.A, 25, 0),
        L.A: (L.B, 50, 30 * 60),
        L.B: (L.C, 200, 60 * 60),
        L.C: (L.D, 500, 3 * 60 * 60),
    }


@pytest.mark.parametrize(
    ("licence", "jumps", "minutes"),
    [(L.STUDENT, 25, 0), (L.A, 50, 30), (L.B, 200, 60), (L.C, 500, 180)],
)
def test_exactly_at_each_threshold_is_met_and_one_below_is_not(
    licence: currency.Licence, jumps: int, minutes: int
) -> None:
    at = _progress(licence, jumps, minutes)
    assert at is not None and at.jumps_met and at.freefall_met
    fewer = _progress(licence, jumps - 1, minutes)
    assert fewer is not None and not fewer.jumps_met and fewer.freefall_met
    if minutes:
        short = licences.progress(
            licence, jumps=jumps, jumps_include_prior=False,
            freefall_seconds=minutes * 60 - 1, entries_with_freefall=jumps,
            entries_without_freefall=0,
        )  # fmt: skip
        assert short is not None and short.jumps_met and not short.freefall_met


def test_a_b_licence_with_60_jumps_and_40_minutes_is_on_the_way_to_c() -> None:
    p = _progress(L.B, 60, 40, without=3)
    assert p is not None
    assert (p.next_licence, p.requirement) == (L.C, licences.Requirement(200, 3600))
    assert (p.jumps, p.freefall_seconds, p.entries_without_freefall) == (60, 2400, 3)
    assert not p.jumps_met and not p.freefall_met


def test_no_licence_gives_nothing_and_d_has_no_next_step() -> None:
    assert _progress(L.NONE, 10, 10) is None
    d = _progress(L.D, 900, 600)
    assert d is not None
    assert (d.next_licence, d.requirement) == (None, None)
    assert not d.jumps_met and not d.freefall_met
