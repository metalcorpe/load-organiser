"""#148 directory rules: plain values, no database or settings."""

import subprocess
import sys
import uuid
from contextlib import AbstractContextManager
from datetime import date
from pathlib import Path
from typing import Any

import pytest

from app.skydiver.directory import policy
from app.skydiver.directory.policy import DirectoryRuleError, MergeCheck, VenueStatus
from app.skydiver.directory.service import decode_cursor, encode_cursor

BACKEND_DIR = Path(__file__).resolve().parents[1]


def rule(code: str) -> AbstractContextManager[Any]:
    return pytest.raises(DirectoryRuleError, match=f"^{code}$")


def test_text_is_trimmed_collapsed_and_bounded() -> None:
    assert policy.clean_text(
        "  Skydive \n  Empuriabrava ", field="name", maximum=120
    ) == ("Skydive Empuriabrava")
    with rule("name_required"):
        policy.clean_text("   ", field="name", maximum=120)
    with rule("name_too_long"):
        policy.clean_text("x" * 121, field="name", maximum=120)
    assert policy.optional_text("  ", field="locality", maximum=10) is None


def test_country_is_an_assigned_iso_code() -> None:
    assert policy.country_code(" es ") == "ES"
    for bad in ("UK", "EU", "XX", "ESP", ""):
        with rule("country_invalid"):
            policy.country_code(bad)


def test_coordinates_are_a_bounded_pair() -> None:
    assert policy.coordinates(None, None) == (None, None)
    assert policy.coordinates(42.2512345678, 3.1) == (42.251235, 3.1)
    with rule("coordinates_incomplete"):
        policy.coordinates(42.0, None)
    with rule("coordinates_invalid"):
        policy.coordinates(91, 0)
    with rule("coordinates_invalid"):
        policy.coordinates(0, -181)


@pytest.mark.parametrize(
    "url",
    [
        "javascript:alert(1)",
        "ftp://example.com/x",
        "https://user:pw@example.com/",
        "//example.com/x",
        "https:///nohost",
        "https://example.com/" + "a" * 2048,
    ],
)
def test_source_url_must_be_plain_http_or_https(url: str) -> None:
    with rule("source_url_invalid"):
        policy.source_url(url)


def test_source_url_accepts_https() -> None:
    assert policy.source_url(" https://example.com/dz ") == "https://example.com/dz"


def test_checked_date_cannot_be_in_the_future() -> None:
    today = date(2026, 11, 3)
    assert policy.checked_on(today, today) == today
    with rule("checked_on_in_future"):
        policy.checked_on(date(2026, 11, 4), today)


def test_search_key_ignores_case_accents_and_punctuation() -> None:
    assert policy.search_key("Skydive Ampuriabrava — Empúriabrava!") == (
        "skydive ampuriabrava empuriabrava"
    )
    assert policy.search_key("ÖSTERREICH") == policy.search_key("osterreich")
    assert policy.search_key("100%_drop") == "100 drop"


def test_page_size_defaults_and_caps() -> None:
    assert policy.page_size(None) == 20
    assert policy.page_size(500) == 50
    assert policy.page_size(0) == 1


@pytest.mark.parametrize(
    ("source", "target", "same", "code"),
    [
        (VenueStatus.LISTED, VenueStatus.LISTED, True, "merge_into_self"),
        (VenueStatus.MERGED, VenueStatus.LISTED, False, "merge_already_merged"),
        (VenueStatus.LISTED, VenueStatus.MERGED, False, "merge_already_merged"),
        (VenueStatus.LISTED, VenueStatus.DRAFT, False, "merge_target_not_public"),
        (VenueStatus.CLOSED, VenueStatus.DRAFT, False, "merge_target_not_public"),
    ],
)
def test_invalid_merges(
    source: VenueStatus, target: VenueStatus, same: bool, code: str
) -> None:
    with rule(code):
        policy.check_merge(MergeCheck(source, target, same))


@pytest.mark.parametrize(
    ("source", "target"),
    [
        (VenueStatus.LISTED, VenueStatus.LISTED),
        (VenueStatus.LISTED, VenueStatus.CLOSED),
        (VenueStatus.DRAFT, VenueStatus.LISTED),
        (VenueStatus.DRAFT, VenueStatus.DRAFT),
    ],
)
def test_valid_merges(source: VenueStatus, target: VenueStatus) -> None:
    policy.check_merge(MergeCheck(source, target, False))


def test_status_transitions() -> None:
    policy.check_transition(VenueStatus.DRAFT, VenueStatus.LISTED)
    policy.check_transition(VenueStatus.LISTED, VenueStatus.CLOSED)
    policy.check_transition(VenueStatus.CLOSED, VenueStatus.LISTED)
    for current, new in [
        (VenueStatus.LISTED, VenueStatus.DRAFT),  # would break public references
        (VenueStatus.MERGED, VenueStatus.LISTED),
        (VenueStatus.LISTED, VenueStatus.MERGED),  # only via merge
    ]:
        with rule("status_change_invalid"):
            policy.check_transition(current, new)


def test_cursor_round_trip_and_rejection() -> None:
    venue_id = uuid.uuid4()
    assert decode_cursor(encode_cursor("skydive x", venue_id)) == (
        "skydive x",
        venue_id,
    )
    for bad in ("not-base64!", encode_cursor("k", venue_id)[:-3] + "zzz", "W10"):
        with rule("cursor_invalid"):
            decode_cursor(bad)


def test_directory_policy_imports_no_framework_or_persistence(tmp_path: Path) -> None:
    code = (
        "import sys, app.skydiver.directory.policy, app.skydiver.directory.service;"
        "bad=[m for m in sys.modules if m.split('.')[0] in "
        "('fastapi','sqlalchemy','sqlmodel','starlette')"
        " or m in ('app.core.config','app.core.db','app.models')];"
        "assert not bad, bad"
    )
    result = subprocess.run(
        [sys.executable, "-c", code],
        cwd=tmp_path,
        env={"PYTHONPATH": str(BACKEND_DIR), "PATH": ""},
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr
