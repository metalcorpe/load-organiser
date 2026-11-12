"""#155 archive rules as plain values (no database)."""

import uuid
from datetime import date
from typing import Any

import pytest

from app.skydiver.records import policy
from app.skydiver.records.format import ArchiveV1
from app.skydiver.records.policy import ArchiveInvalid

TODAY = date(2026, 11, 4)
AT = "2026-10-01T10:00:00Z"


def _archive(**records: Any) -> ArchiveV1:
    base: dict[str, Any] = {
        "places": [], "components": [], "rigs": [], "rig_stints": [],
        "service_entries": [], "gear_events": [], "jumps": [], "jump_events": [],
        "baseline": None, "baseline_events": [], "saved_listings": [], "plans": [],
    }  # fmt: skip
    references = records.pop("references", {"venues": [], "listings": []})
    return ArchiveV1.model_validate(
        {
            "format": "load-organiser.personal-records",
            "version": 1,
            "exported_at": AT,
            "records": base | records,
            "references": references,
        }  # fmt: skip
    )


def _problem(archive: ArchiveV1) -> str:
    with pytest.raises(ArchiveInvalid) as raised:
        policy.check(archive, TODAY)
    return raised.value.problem


def _component(**fields: Any) -> dict[str, Any]:
    return {
        "id": str(uuid.uuid4()), "kind": "main", "label": "Main", "relation": "owned",
        "created_at": AT, "updated_at": AT, **fields,
    }  # fmt: skip


def _rig() -> dict[str, Any]:
    return {"id": str(uuid.uuid4()), "label": "Rig", "created_at": AT, "updated_at": AT}


def test_an_empty_archive_is_valid() -> None:
    policy.check(_archive(), TODAY)
    assert policy.counts(_archive()).jumps == 0


def test_ids_are_unique_within_a_section() -> None:
    c = _component()
    assert _problem(_archive(components=[c, c])) == "components[1].duplicate_id"


def test_rig_stints_never_overlap() -> None:
    c, a, b = _component(), _rig(), _rig()
    ok = [
        {
            "rig_id": a["id"],
            "component_id": c["id"],
            "from_on": "2026-01-01",
            "until_on": "2026-03-01",
        },  # fmt: skip
        {"rig_id": b["id"], "component_id": c["id"], "from_on": "2026-03-01"},
    ]
    policy.check(_archive(components=[c], rigs=[a, b], rig_stints=ok), TODAY)
    open_twice = [
        {"rig_id": a["id"], "component_id": c["id"], "from_on": "2026-01-01"},
        {"rig_id": b["id"], "component_id": c["id"], "from_on": "2026-03-01"},
    ]
    assert (
        _problem(_archive(components=[c], rigs=[a, b], rig_stints=open_twice))
        == "rig_stints[1].overlaps"
    )


def test_gear_rules_match_the_api() -> None:
    borrowed = _component(relation="borrowed", acquisition_method="purchase")
    assert _problem(_archive(components=[borrowed])) == (
        "components[0].acquisition_requires_owned"
    )
    future = _component(manufactured="2027")
    assert (
        _problem(_archive(components=[future])) == "components[0].manufactured_invalid"
    )


def test_jump_rules_match_the_api() -> None:
    place = {"id": str(uuid.uuid4()), "name": "P", "country": "PT", "created_at": AT, "updated_at": AT}  # fmt: skip

    def jump(**fields: Any) -> dict[str, Any]:
        return {
            "id": str(uuid.uuid4()), "jumped_on": "2026-10-01", "jump_type": "belly",
            "place_id": place["id"], "links": [], "component_ids": [],
            "source": "manual", "created_at": AT, "updated_at": AT, **fields,
        }  # fmt: skip

    cases = {
        "jumps[0].jump_date_in_future": jump(jumped_on="2026-11-05"),
        "jumps[0].time_zone_required": jump(exit_time="10:00:00"),
        "jumps[0].exit_time_invalid": jump(time_zone="Europe/Madrid"),
        "jumps[0].altitude_unit_required": jump(exit_altitude=4000),
        "jumps[0].altitudes_incomplete": jump(altitude_unit="ft"),
        "jumps[0].link_invalid": jump(links=["ftp://example.org/x"]),
        "jumps[0].component_unknown": jump(component_ids=[str(uuid.uuid4())]),
    }
    for expected, item in cases.items():
        assert _problem(_archive(places=[place], jumps=[item])) == expected, expected
    both = jump(venue_id=str(uuid.uuid4()))
    assert (
        _problem(_archive(places=[place], jumps=[both])) == "jumps[0].location_required"
    )


def test_plans_and_saved_listings_need_their_references() -> None:
    plan = {
        "title": "Trip", "starts_on": "2027-01-01", "ends_on": "2027-01-02",
        "venue_id": str(uuid.uuid4()), "created_at": AT, "updated_at": AT,
    }  # fmt: skip
    assert _problem(_archive(plans=[plan])) == "plans[0].venue_unknown"
    saved = {"opportunity_id": str(uuid.uuid4()), "title": "B", "created_at": AT}
    assert _problem(_archive(saved_listings=[saved])) == (
        "saved_listings[0].listing_unknown"
    )


def test_remap_rewrites_known_ids_only() -> None:
    old, new = str(uuid.uuid4()), str(uuid.uuid4())
    detail = {"place_id": {"from": old, "to": None}, "notes": "changed", "x": [old, 3]}
    assert policy.remap(detail, {old: new}) == {
        "place_id": {"from": new, "to": None},
        "notes": "changed",
        "x": [new, 3],
    }


def test_text_must_be_what_the_api_would_store() -> None:
    def place(**fields: Any) -> dict[str, Any]:
        return {
            "id": str(uuid.uuid4()), "name": "Strip", "country": "PT",
            "created_at": AT, "updated_at": AT, **fields,
        }  # fmt: skip

    assert _problem(_archive(places=[place(name="   ")])) == "places[0].name_required"
    assert _problem(_archive(places=[place(name=" Strip")])) == "places[0].name_invalid"
    assert (
        _problem(_archive(places=[place(name="Str\nip")])) == "places[0].name_invalid"
    )
    assert (
        _problem(_archive(places=[place(country="ZZ")])) == "places[0].country_invalid"
    )
    assert _problem(_archive(components=[_component(label="Main  canopy")])) == (
        "components[0].label_invalid"
    )
    rig = _rig() | {"label": "\tRig"}
    assert _problem(_archive(rigs=[rig])) == "rigs[0].label_invalid"


# -- spreadsheet (CSV) ------------------------------------------------------------


def test_spreadsheet_guards_formula_text_and_quotes_per_rfc_4180() -> None:
    from datetime import date

    from app.skydiver.records import spreadsheet

    for text, guarded in [
        ("=SUM(A1)", "'=SUM(A1)"),
        ("+31 6", "'+31 6"),
        ("-x", "'-x"),
        ("@here", "'@here"),
        ("\tTab", "'\tTab"),
        ("\rCR", "'\rCR"),
        ("'quoted", "''quoted"),
        ("Plain = fine", "Plain = fine"),
        (" =SUM(A1)", "' =SUM(A1)"),  # a spreadsheet ignores leading spaces
    ]:
        assert spreadsheet.guard(text) == guarded, text

    row = spreadsheet.Row(
        jumped_on=date(2026, 10, 10), jump_number=None, place='A "B", C',
        country=None, jump_type="unspecified", aircraft=None, exit_altitude=None,
        altitude_unit=None, deployment_altitude=None, freefall_seconds=None,
        notes="two\nlines", gear=["Sabre", "=x"],
    )  # fmt: skip
    raw = spreadsheet.render([row])
    assert raw.startswith(b"\xef\xbb\xbf")  # UTF-8 byte-order mark
    text = raw.decode("utf-8-sig")
    assert text == (
        ",".join(spreadsheet.HEADINGS) + "\r\n"
        + '2026-10-10,,"A ""B"", C",,,,,,,,"two\nlines",Sabre; =x\r\n'
    )  # fmt: skip
