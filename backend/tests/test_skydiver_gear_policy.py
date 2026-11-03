"""#152 gear rules as plain values (no database)."""

import ast
import pathlib
from datetime import date

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
