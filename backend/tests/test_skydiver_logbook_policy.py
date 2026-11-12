"""#153 jump rules as plain values (no database)."""

from datetime import date, time

import pytest

from app.skydiver.directory.policy import DirectoryRuleError
from app.skydiver.logbook import policy
from app.skydiver.logbook.policy import AltitudeDatum, AltitudeUnit

TODAY = date(2026, 11, 4)


def _code(call: object) -> str:
    with pytest.raises(DirectoryRuleError) as raised:
        call()  # type: ignore[operator]
    return raised.value.code


def test_jump_date_is_a_calendar_date_up_to_today() -> None:
    assert policy.jump_date(TODAY, TODAY) == TODAY
    assert _code(lambda: policy.jump_date(date(2026, 11, 5), TODAY)) == (
        "jump_date_in_future"
    )
    assert _code(lambda: policy.jump_date(date(1900, 1, 1), TODAY)) == (
        "jump_date_invalid"
    )


def test_exit_time_needs_a_real_zone_and_a_zone_alone_is_dropped() -> None:
    assert policy.exit_time(None, "Europe/Madrid") == (None, None)
    assert policy.exit_time(time(14, 5, 31), " Europe/Madrid ") == (
        time(14, 5),
        "Europe/Madrid",
    )
    assert _code(lambda: policy.exit_time(time(9), None)) == "time_zone_required"
    for zone in ("Mars/Base", "../etc/passwd", "Europe/" + "x" * 70):
        assert _code(lambda z=zone: policy.exit_time(time(9), z)) == (
            "time_zone_invalid"
        )


def test_altitudes_keep_unit_and_datum_and_never_invent_them() -> None:
    none = policy.altitudes(None, None, AltitudeUnit.FT, AltitudeDatum.AGL)
    assert (none.unit, none.datum) == (None, AltitudeDatum.UNSPECIFIED)
    kept = policy.altitudes(4000, 1000, AltitudeUnit.M, None)
    assert (kept.exit, kept.deployment, kept.unit, kept.datum) == (
        4000,
        1000,
        AltitudeUnit.M,
        AltitudeDatum.UNSPECIFIED,
    )
    assert _code(lambda: policy.altitudes(4000, None, None, None)) == (
        "altitude_unit_required"
    )
    assert _code(lambda: policy.altitudes(20_000, None, AltitudeUnit.M, None)) == (
        "altitude_invalid"
    )
    assert _code(lambda: policy.altitudes(0, None, AltitudeUnit.FT, None)) == (
        "altitude_invalid"
    )
    assert _code(lambda: policy.altitudes(3000, 4000, AltitudeUnit.FT, None)) == (
        "deployment_above_exit"
    )


def test_freefall_number_and_links() -> None:
    assert policy.freefall_seconds(0) == 0  # e.g. a clear-and-pull, not unknown
    assert policy.freefall_seconds(None) is None
    assert _code(lambda: policy.freefall_seconds(-1)) == "freefall_invalid"
    assert _code(lambda: policy.jump_number(0)) == "jump_number_invalid"
    assert policy.links(["  https://a.example/x ", ""]) == ["https://a.example/x"]
    assert _code(lambda: policy.links(["ftp://a.example"])) == "link_invalid"
    assert _code(lambda: policy.links(["https://a.example"] * 6)) == "too_many_links"
    assert policy.component_ids(["a", "b", "a"]) == ["a", "b"]


def _numbered(*numbers: int) -> list[policy.Numbered[str]]:
    ordered = sorted(numbers)
    return [policy.Numbered(n, f"j{n}.{i}") for i, n in enumerate(ordered)]


def test_numbering_finds_the_highest_gaps_and_repeats() -> None:
    empty = policy.numbering(_numbered())
    assert (empty.highest, empty.gaps, empty.repeats) == (None, [], [])

    clean = policy.numbering(_numbered(118, 119, 120))
    assert (clean.highest, clean.gap_count, clean.repeat_count) == (120, 0, 0)

    found = policy.numbering(_numbered(118, 119, 120, 125, 130, 130, 131, 133))
    assert found.highest == 133
    assert [(g.first, g.last, g.before, g.after) for g in found.gaps] == [
        (121, 124, "j120.2", "j125.3"),
        (126, 129, "j125.3", "j130.4"),
        (132, 132, "j131.6", "j133.7"),
    ]
    assert found.gap_count == 3
    assert [(r.number, r.uses, r.refs) for r in found.repeats] == [
        (130, 2, ["j130.4", "j130.5"])
    ]
    # Numbers below the first one recorded are not missing.
    assert policy.numbering(_numbered(500, 501)).gaps == []


def test_numbering_notes_stay_bounded() -> None:
    every_other = policy.numbering(_numbered(*range(1, 4000, 2)))  # 2,000 jumps
    assert len(every_other.gaps) == policy.NUMBERING_ISSUES_MAX
    assert every_other.gap_count == 1999
    many = policy.numbering(
        _numbered(*([7] * 9), *([8] * 2), 9, 9, 10, 10, 11, 11, 12, 12)
    )
    assert len(many.repeats) == policy.NUMBERING_ISSUES_MAX
    assert many.repeat_count == 6
    assert (many.repeats[0].uses, len(many.repeats[0].refs)) == (
        9,
        policy.REPEAT_JUMPS_MAX,
    )
