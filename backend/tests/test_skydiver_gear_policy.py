"""#152 gear rules as plain values (no database)."""

import ast
import pathlib
from datetime import date, timedelta

import pytest

from app.skydiver.directory.policy import DirectoryRuleError
from app.skydiver.gear import policy
from app.skydiver.gear.policy import AcquisitionMethod, Relation

TODAY = date(2026, 11, 3)


def test_policy_imports_no_framework_or_persistence() -> None:
    tree = ast.parse(pathlib.Path(policy.__file__).read_text())
    imported = {
        (node.module or "").split(".")[0]
        for node in ast.walk(tree)
        if isinstance(node, ast.ImportFrom)
    } | {
        alias.name.split(".")[0]
        for node in ast.walk(tree)
        if isinstance(node, ast.Import)
        for alias in node.names
    }
    assert not imported & {"fastapi", "sqlalchemy", "sqlmodel", "pydantic"}


def test_partial_dates_keep_their_precision() -> None:
    month = policy.partial_date("2019-04", field="manufactured", today=TODAY)
    assert month is not None and (month.text, month.precision) == ("2019-04", "month")
    year = policy.partial_date(" 2019 ", field="manufactured", today=TODAY)
    assert year is not None and year.precision == "year"
    assert policy.partial_date("", field="manufactured", today=TODAY) is None
    for bad in ("2019-13", "2019-02-30", "19-04", "2027", "1850", "April 2019"):
        with pytest.raises(DirectoryRuleError) as error:
            policy.partial_date(bad, field="manufactured", today=TODAY)
        assert error.value.code == "manufactured_invalid", bad


def test_serials_are_kept_as_entered() -> None:
    assert policy.serial("  0042-ab/7 ") == "0042-ab/7"
    assert policy.serial("   ") is None
    with pytest.raises(DirectoryRuleError):
        policy.serial("12\n34")
    with pytest.raises(DirectoryRuleError):
        policy.serial("x" * 121)
    # The comparison key ignores case and punctuation; it never replaces the value.
    assert policy.serial_key("0042-ab/7") == policy.serial_key("0042AB7") == "0042AB7"
    assert policy.serial_key("--") is None


def test_acquisition_details_only_for_owned_items() -> None:
    policy.check_acquisition(Relation.OWNED, AcquisitionMethod.PURCHASE, None)
    with pytest.raises(DirectoryRuleError) as error:
        policy.check_acquisition(Relation.BORROWED, AcquisitionMethod.GIFT, None)
    assert error.value.code == "acquisition_requires_owned"


def test_service_and_rig_dates() -> None:
    policy.check_service_dates(date(2026, 10, 1), date(2027, 4, 1), TODAY)
    with pytest.raises(DirectoryRuleError):
        policy.check_service_dates(date(2026, 12, 1), None, TODAY)
    with pytest.raises(DirectoryRuleError):
        policy.check_service_dates(date(2026, 10, 1), date(2026, 9, 1), TODAY)
    policy.check_membership(date(2026, 5, 1), date(2026, 5, 1), TODAY)
    with pytest.raises(DirectoryRuleError) as error:
        policy.check_membership(date(2026, 4, 30), date(2026, 5, 1), TODAY)
    assert error.value.code == "rig_date_before_current"


# -- due dates ----------------------------------------------------------------------

DUE_TODAY = date(2026, 11, 12)


def _fact(
    kind: str, done_on: date, due_on: date | None = None, order: int = 0
) -> policy.ServiceFact:
    return policy.ServiceFact(policy.ServiceKind(kind), done_on, due_on, order)


def _due(kind: str, facts: list[policy.ServiceFact], **fields: object) -> list[policy.Due]:  # fmt: skip
    values: dict[str, object] = {"repack_interval_days": None, "end_of_life_on": None}
    return policy.due_dates(policy.ComponentKind(kind), facts, **(values | fields))  # type: ignore[arg-type]


def test_a_reserve_repack_is_due_180_days_after_it_by_default() -> None:
    (due,) = _due("reserve", [_fact("repack", date(2026, 5, 21))])
    assert due.kind is policy.DueKind.RESERVE_REPACK
    assert (due.due_on, due.basis, due.interval_days) == (date(2026, 11, 17), "interval", 180)  # fmt: skip
    assert due.interval_is_default
    assert policy.REPACK_INTERVAL_DAYS == 180
    assert policy.REPACK_SOURCE == "USPA / FAA 14 CFR 105.43"


def test_the_owners_interval_and_an_entered_due_date_take_precedence() -> None:
    (own,) = _due("reserve", [_fact("repack", date(2026, 1, 1))], repack_interval_days=365)  # fmt: skip
    assert (own.due_on, own.interval_days, own.interval_is_default) == (date(2027, 1, 1), 365, False)  # fmt: skip
    entered = _fact("repack", date(2026, 1, 1), date(2026, 3, 1))
    (due,) = _due("reserve", [entered], repack_interval_days=365)
    assert (due.due_on, due.basis, due.interval_days) == (date(2026, 3, 1), "entered", None)  # fmt: skip


def test_only_the_latest_entry_of_each_kind_counts() -> None:
    facts = [
        _fact("repack", date(2026, 1, 1), date(2026, 2, 1), order=0),
        _fact("repack", date(2026, 6, 1), order=1),
        # The same day as the repack before it, recorded after it: this one wins.
        _fact("repack", date(2026, 6, 1), date(2026, 7, 1), order=2),
    ]
    (due,) = _due("reserve", facts)
    assert due.due_on == date(2026, 7, 1)


def test_nothing_is_estimated_except_a_reserve_repack() -> None:
    # An AAD service without a due date gives nothing: no manufacturer interval.
    assert _due("aad", [_fact("aad_service", date(2026, 1, 1))]) == []
    # A main canopy repack is not a reserve repack.
    assert _due("main", [_fact("repack", date(2026, 1, 1))]) == []
    # A reserve without any repack recorded has nothing to count from.
    assert _due("reserve", []) == []


def test_entered_dates_of_any_kind_are_listed_soonest_first() -> None:
    facts = [
        _fact("aad_service", date(2024, 3, 1), date(2028, 3, 1)),
        _fact("inspection", date(2026, 1, 1), date(2026, 12, 1)),
    ]
    found = _due("aad", facts, end_of_life_on=date(2036, 3, 1))
    assert [(d.kind.value, d.service_kind, d.due_on) for d in found] == [
        ("service", policy.ServiceKind.INSPECTION, date(2026, 12, 1)),
        ("service", policy.ServiceKind.AAD_SERVICE, date(2028, 3, 1)),
        ("end_of_life", None, date(2036, 3, 1)),
    ]


@pytest.mark.parametrize(
    ("offset", "status"),
    [
        (-1, policy.DueStatus.OVERDUE),  # overdue by one day
        (0, policy.DueStatus.SOON),  # due today: still in time
        (5, policy.DueStatus.SOON),
        (30, policy.DueStatus.SOON),  # the last day of the 30-day window
        (31, policy.DueStatus.LATER),
    ],
)
def test_due_status_boundaries(offset: int, status: policy.DueStatus) -> None:
    assert policy.due_status(DUE_TODAY + timedelta(days=offset), DUE_TODAY) is status


def test_interval_and_end_of_life_validation() -> None:
    assert policy.repack_interval(None) is None
    assert (policy.repack_interval(1), policy.repack_interval(730)) == (1, 730)
    for bad in (0, 731, -5):
        with pytest.raises(DirectoryRuleError) as error:
            policy.repack_interval(bad)
        assert error.value.code == "repack_interval_invalid"
    assert policy.end_of_life(date(2036, 1, 1)) == date(2036, 1, 1)
    with pytest.raises(DirectoryRuleError) as error:
        policy.end_of_life(date(2200, 1, 1))
    assert error.value.code == "end_of_life_invalid"
