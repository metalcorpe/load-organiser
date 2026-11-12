"""#154 prior-history totals and currency guidance as plain values (no database)."""

import uuid
from datetime import date, time, timedelta

import pytest

from app.skydiver.directory.policy import DirectoryRuleError
from app.skydiver.history import currency, licences, milestones, policy
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


# -- milestones -------------------------------------------------------------------

M = milestones.MilestoneKind
VENUE = ("venue", uuid.UUID(int=1))


def _entry(
    on: str, *, n: int | None = None, at: str | None = None, kind: str = "belly",
    freefall: int | None = None, place: tuple[str, uuid.UUID] = VENUE, i: int = 0,
) -> milestones.Entry:  # fmt: skip
    return milestones.Entry(
        id=uuid.UUID(int=1000 + i), jumped_on=date.fromisoformat(on), jump_number=n,
        exit_time=time.fromisoformat(at) if at else None, jump_type=kind,
        freefall_seconds=freefall, place=place,
    )  # fmt: skip


def _days(count: int, start: date = date(2025, 1, 1)) -> list[milestones.Entry]:
    return [_entry((start + timedelta(days=i)).isoformat(), i=i) for i in range(count)]


def _counts(found: list[milestones.Milestone]) -> list[tuple[int | None, date | None]]:
    return [(m.number, m.on) for m in found if m.kind is M.JUMP_COUNT]


def test_jump_count_marks_are_fixed_then_every_thousand() -> None:
    assert list(milestones.jump_counts(24)) == [1]
    assert list(milestones.jump_counts(25)) == [1, 25]
    assert list(milestones.jump_counts(3500)) == [
        1, 25, 50, 100, 200, 250, 500, 1000, 2000, 3000,
    ]  # fmt: skip


def test_the_25th_entry_is_the_25th_jump_without_a_prior_count() -> None:
    entries = _days(26)
    found = milestones.milestones(entries, prior=None)
    assert _counts(found) == [(25, date(2025, 1, 25)), (1, date(2025, 1, 1))]
    assert _counts(milestones.milestones(entries[:24], prior=None)) == [(1, date(2025, 1, 1))]  # fmt: skip


def test_counts_within_the_prior_jumps_are_undated_and_after_it_count_on() -> None:
    # 30 declared before 2025-02-01; one entry before the cutoff is already within it.
    entries = [_entry("2025-01-15", i=99)] + _days(21, date(2025, 2, 1))
    prior = milestones.Prior(30, date(2025, 2, 1))
    found = milestones.milestones(entries, prior=prior)
    # The 50th jump is the 20th entry on or after the cutoff.
    assert _counts(found) == [
        (50, date(2025, 2, 20)),
        (25, None),  # before this logbook
        (1, None),
    ]
    assert [m.jump_id for m in found if m.on is None] == [None, None]
    # An inconsistent prior count dates no jump count at all.
    assert _counts(milestones.milestones(entries, prior=None, count_jumps=False)) == []


def test_a_milestone_exactly_at_the_prior_count_is_before_the_logbook() -> None:
    prior = milestones.Prior(25, date(2025, 1, 1))
    found = milestones.milestones(_days(1), prior=prior)
    assert _counts(found) == [(25, None), (1, None)]


def test_same_day_entries_follow_the_jump_number_then_exit_time() -> None:
    # Recorded out of order on one day: the jumper's numbers decide which is first.
    second = _entry("2025-03-01", n=2, i=1, kind="freefly")
    first = _entry("2025-03-01", n=1, i=2, kind="belly")
    found = milestones.milestones([second, first], prior=None)
    assert _counts(found) == [(1, date(2025, 3, 1))]
    assert next(m for m in found if m.number == 1).jump_id == first.id
    # Newest first: the later jump's milestone comes before the earlier one's.
    assert [(m.kind, m.jump_id) for m in found] == [
        (M.JUMP_TYPE, second.id),
        (M.JUMP_COUNT, first.id),
        (M.JUMP_TYPE, first.id),
        (M.PLACE, first.id),
    ]
    # Without numbers, the exit time orders them.
    late = _entry("2025-03-01", at="15:00", i=1)
    early = _entry("2025-03-01", at="09:30", i=2)
    found = milestones.milestones([late, early], prior=None)
    assert next(m for m in found if m.number == 1).jump_id == early.id


def test_first_of_each_type_skips_unspecified() -> None:
    entries = [
        _entry("2025-01-01", kind="unspecified", i=1),
        _entry("2025-01-02", kind="belly", i=2),
        _entry("2025-01-03", kind="belly", i=3),
        _entry("2025-01-04", kind="wingsuit", i=4),
    ]
    found = milestones.milestones(entries, prior=None)
    assert [(m.jump_type, m.on) for m in found if m.kind is M.JUMP_TYPE] == [
        ("wingsuit", date(2025, 1, 4)),
        ("belly", date(2025, 1, 2)),
    ]


def test_freefall_hours_date_the_entry_that_crossed_them() -> None:
    start = date(2025, 1, 1)
    # 600 s each (the logbook's per-jump maximum), one entry without a time.
    entries = [
        _entry((start + timedelta(days=i)).isoformat(), freefall=600, i=i)
        for i in range(29)
    ] + [
        _entry("2025-03-01", i=40),  # none recorded: adds nothing
        _entry("2025-03-02", freefall=599, i=41),  # 17,999 s: 1 s short of 5 hours
        _entry("2025-03-03", freefall=1, i=42),
    ]
    found = milestones.milestones(entries, prior=None)
    assert [(m.hours, m.on) for m in found if m.kind is M.FREEFALL] == [
        (5, date(2025, 3, 3)),
        (1, date(2025, 1, 6)),  # the 6th entry: exactly 3,600 s
    ]


def test_only_the_five_most_recent_new_places_are_listed() -> None:
    entries = [
        _entry(f"2025-01-{d:02d}", place=("place", uuid.UUID(int=d)), i=d)
        for d in range(1, 8)
    ] + [
        _entry("2025-01-20", place=("place", uuid.UUID(int=1)), i=20)
    ]  # a return visit
    found = milestones.milestones(entries, prior=None)
    places = [m.place for m in found if m.kind is M.PLACE]
    assert places == [("place", uuid.UUID(int=d)) for d in (7, 6, 5, 4, 3)]


def test_two_thousand_entries_in_one_pass() -> None:
    entries = _days(2000)
    found = milestones.milestones(entries, prior=None)
    assert _counts(found)[0] == (2000, date(2025, 1, 1) + timedelta(days=1999))
