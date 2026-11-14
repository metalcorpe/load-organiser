"""Local development listings loader (#162)."""

import json
import uuid
from datetime import UTC, datetime
from pathlib import Path
from typing import Any

import pytest
from sqlalchemy import text

from app.core.config import settings
from app.core.db import engine
from app.skydiver import devdata
from app.skydiver.directory.policy import SOURCE_NOTE_MAX, DirectoryRuleError
from app.skydiver.directory.service import DirectoryService, Operator, VenueInput
from app.skydiver.directory.store import sql_directory_store_factory
from app.skydiver.opportunities.service import OpportunityService
from app.skydiver.opportunities.store import sql_listing_store_factory
from app.tests.skydiver.support import Accounts

REPO = Path(__file__).resolve().parents[4]


def _email(accounts: Accounts, secret: str) -> str:
    account = accounts.service.current_viewer(secret=secret).account_id
    with engine.connect() as conn:
        return str(conn.execute(text('SELECT email FROM "user" WHERE id = :id'), {"id": account}).scalar_one())  # fmt: skip


def _fixture(tag: str) -> dict[str, Any]:
    return {
        "venues": [
            {
                "key": f"t-{tag}-dz",
                "name": f"Dev DZ {tag}",
                "country": "ES",
                "locality": "Somewhere",
                "latitude": None,
                "longitude": None,
                "source_url": "https://example.org/dz",
            }
        ],  # fmt: skip
        "providers": [
            {
                "key": f"t-{tag}-org",
                "name": f"Dev Org {tag}",
                "kind": "organization",
                "country": "ES",
                "website_url": "https://example.org/",
                "source_url": "https://example.org/about",
                "note": "Owner says: one organizer.",
            }
        ],  # fmt: skip
        "opportunities": [
            {
                "title": f"Dated boogie {tag}",
                "category": "boogie",
                "provider": f"t-{tag}-org",
                "venue": f"t-{tag}-dz",
                "country": "ES",
                "starts_on": "2027-03-25",
                "ends_on": "2027-03-29",
                "time_zone": "Europe/Madrid",
                "disciplines": ["belly"],
                "audience": [],
                "languages": [],
                "summary": "A test boogie.",
                "price_amount": "80",
                "price_currency": "EUR",
                "price_basis": "per_person",
                "registration_url": "https://example.org/register",
                "source_url": "https://example.org/boogie",
            },  # fmt: skip
            {
                "title": f"Ongoing AFF {tag}",
                "category": "course",
                "provider": f"t-{tag}-org",
                "venue": f"t-{tag}-dz",
                "country": "ES",
                "starts_on": None,
                "ends_on": None,
                "time_zone": None,
                "disciplines": ["aff", "freefly"],
                "audience": [],
                "languages": [],
                "registration_url": "https://example.org/contact",
                "source_url": "https://example.org/aff",
            },  # fmt: skip
        ],
    }


def test_loads_through_the_rules_once_and_leaves_undated_listings_in_review(tmp_path: Path) -> None:  # fmt: skip
    accounts = Accounts.create()
    actor = devdata.reviewer_actor(engine, _email(accounts, accounts.session(reviewer=True)))  # fmt: skip
    clock = lambda: datetime.now(UTC)  # noqa: E731
    directory = DirectoryService(stores=sql_directory_store_factory(engine), clock=clock)  # fmt: skip
    listings = OpportunityService(stores=sql_listing_store_factory(engine), clock=clock)  # fmt: skip
    tag = uuid.uuid4().hex[:8]
    path = tmp_path / "dev.json"
    path.write_text(json.dumps(_fixture(tag)))

    first = devdata.load(engine, path, actor, directory, listings)
    assert first["added"] == {"venues": 1, "providers": 1, "opportunities": 2, "published": 1}  # fmt: skip
    assert [d["key"] for d in first["drafts"]] == [
        f"t-{tag}-org-ongoing-aff-{tag}-ongoing"
    ]
    assert first["tags_dropped"] == 1  # "aff" is a training method, not a discipline
    with engine.connect() as conn:
        rows: dict[str, str] = dict(conn.execute(text("SELECT title, status FROM skydiver_opportunity WHERE title LIKE :t"), {"t": f"%{tag}"}).all())  # fmt: skip
    assert rows == {f"Dated boogie {tag}": "published", f"Ongoing AFF {tag}": "review"}

    again = devdata.load(engine, path, actor, directory, listings)
    assert again["added"] == {}
    assert again["skipped"] == 4


FIXTURES = Path(__file__).parent / "fixtures" / "dropzones"


def _only_this_run(monkeypatch: pytest.MonkeyPatch, tag: str) -> None:
    """The test database is shared: other tests' venues sit at the fixture's places and
    carry its aliases (another run's "LEXX")."""
    real_stored, real_names = devdata._stored_venues, devdata._venue_names

    def ids(engine: Any) -> set[uuid.UUID]:
        with engine.connect() as conn:
            return set(conn.execute(text("SELECT id FROM skydiver_venue WHERE name LIKE :t"), {"t": f"%{tag}%"}).scalars())  # fmt: skip

    def stored(engine: Any) -> dict[str, list[devdata.StoredVenue]]:
        mine = ids(engine)
        return {c: [v for v in vs if v.id in mine] for c, vs in real_stored(engine).items()}  # fmt: skip

    def names(engine: Any) -> dict[tuple[str, str], uuid.UUID]:
        mine = ids(engine)
        return {k: v for k, v in real_names(engine).items() if v in mine}

    monkeypatch.setattr(devdata, "_stored_venues", stored)
    monkeypatch.setattr(devdata, "_venue_names", names)


def test_loads_the_dropzone_inventory_with_coordinates_once(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Country files load as venues; `_` files are skipped; known dropzones are not doubled."""
    accounts = Accounts.create()
    actor = devdata.reviewer_actor(engine, _email(accounts, accounts.session(reviewer=True)))  # fmt: skip
    clock = lambda: datetime.now(UTC)  # noqa: E731
    directory = DirectoryService(stores=sql_directory_store_factory(engine), clock=clock)  # fmt: skip
    listings = OpportunityService(stores=sql_listing_store_factory(engine), clock=clock)  # fmt: skip
    tag = uuid.uuid4().hex[:8]
    _only_this_run(monkeypatch, tag)
    folder = tmp_path / "dropzones"
    folder.mkdir()
    # The fixture with this run's tag, so runs sharing the database stay independent.
    for source in FIXTURES.iterdir():
        text_in = source.read_text(encoding="utf-8").replace("TAG", tag)
        (folder / source.name).write_text(text_in, encoding="utf-8")
    path = tmp_path / "dev.json"
    path.write_text(json.dumps(_fixture(tag)))  # "Dev DZ <tag>", ES, no coordinates

    first = devdata.load(engine, path, actor, directory, listings)
    report = first["dropzones"]
    dev_dz = directory.search(query=f"Dev DZ {tag}", country="ES", cursor=None, limit=None).items[0]  # fmt: skip
    active_dz = directory.search(query=f"Active Field {tag}", country="ES", cursor=None, limit=None).items[0]  # fmt: skip
    assert {k: v for k, v in report.items() if k != "refused"} == {
        "files": 1, "added": 4, "closed": 1, "skipped": 0, "resumed": 0, "drafted": 1,
        "duplicates": [
            # ~500 m from a dropzone this run added, under another name.
            {"key": f"es-{tag}-near-active", "matched": str(active_dz.id), "by": "distance"},
            # "Aeródromo Dev DZ" is the listings' "Dev DZ": the same place words.
            {"key": f"es-{tag}-listed-already", "matched": str(dev_dz.id), "by": "name"},
        ],
        "located": 1, "detailed": 0, "aliases_dropped": 0,
    }  # fmt: skip
    # Bad records and a broken file are refused one by one; everything else loaded.
    refused = report["refused"]
    assert refused[-1]["file"] == "PT.json"  # files load in name order
    assert refused[:-1] == [
        {"key": f"es-{tag}-unsourced", "reason": "source_required"},
        {"key": f"es-{tag}-bad-status", "reason": "status_invalid"},
        {"key": f"Bad Key {tag}", "reason": "key_invalid"},
        {"key": f"es-{tag}-bad-coordinates", "reason": "coordinates_invalid"},
    ]
    # Nothing was left behind for refused records, not even a draft.
    for name in ("Unsourced Field", "Bad Status", "Bad Coordinates"):
        with engine.connect() as conn:
            found = conn.execute(text("SELECT count(*) FROM skydiver_venue WHERE name = :n"), {"n": f"{name} {tag}"}).scalar_one()  # fmt: skip
        assert found == 0, name

    def venue(name: str) -> dict[str, Any]:
        page = directory.search(query=name, country="ES", cursor=None, limit=None)
        assert len(page.items) == 1, name
        v = page.items[0]
        return {
            "status": v.status.value, "lat": v.latitude, "lon": v.longitude,
            "aliases": sorted(a.name for a in v.aliases), "note": v.source_note,
            "url": v.source_url, "checked_on": v.checked_on.isoformat() if v.checked_on else None,
        }  # fmt: skip

    active = venue(f"Active Field {tag}")
    assert active["status"] == "listed" and (active["lat"], active["lon"]) == (42.25857, 3.137)  # fmt: skip
    assert active["aliases"] == ["LEXX", f"Skydive Active {tag}"]
    assert (active["url"], active["checked_on"]) == ("https://example.org/federation", "2026-11-13")  # fmt: skip
    assert active["note"].startswith(f"dev-data:es-{tag}-active ")
    # Operators, season and aircraft as the record states them.
    assert active_dz.operators == (
        Operator(f"Skydive Active {tag}", "https://example.org/"),
    )
    assert (active_dz.season, active_dz.aircraft) == (
        "All year, weekends",
        "Cessna 208 Caravan",
    )
    assert venue(f"Closed Field {tag}")["status"] == "closed"
    # An uncertain lead is kept as a draft: not shown as a dropzone, here as on staging.
    assert directory.search(query=f"Unplaced Field {tag}", country="ES", cursor=None, limit=None).items == []  # fmt: skip
    with engine.connect() as conn:
        unplaced = conn.execute(text("SELECT status, checked_on, source_note FROM skydiver_venue WHERE name = :n"), {"n": f"Unplaced Field {tag}"}).one()  # fmt: skip
    assert unplaced.status == "draft"
    assert unplaced.checked_on.isoformat() == "2026-11-14"  # the file's research day
    assert unplaced.source_note.endswith("Research status: uncertain.")
    # The listings' own venue, found by the dropzone's name, got the coordinates.
    known = venue(f"Dev DZ {tag}")
    assert (known["lat"], known["lon"]) == (41.5, 2.1)
    assert directory.search(query=f"Aeródromo Dev {tag}", country="ES", cursor=None, limit=None).items == []  # fmt: skip
    # An alias shared with another dropzone (an operator brand) does not make it the same one.
    second = venue(f"Second Field {tag}")
    assert (second["status"], second["aliases"]) == ("listed", [f"Skydive Active {tag}"])  # fmt: skip
    points = directory.map_points(query=tag, country="ES", cursor=None, limit=None)
    assert sorted(p.name for p in points.items) == sorted(
        [
            f"Active Field {tag}",
            f"Second Field {tag}",
            f"Closed Field {tag}",
            f"Active {tag} West Field",  # shares Active Field's words, 400 km away
            f"Dev DZ {tag}",
        ]  # fmt: skip
    )

    again = devdata.load(engine, path, actor, directory, listings)["dropzones"]
    assert (again["added"], again["skipped"], again["drafted"], again["located"]) == (0, 4, 1, 0)  # fmt: skip
    assert [d["key"] for d in again["duplicates"]] == [f"es-{tag}-near-active", f"es-{tag}-listed-already"]  # fmt: skip


@pytest.mark.parametrize(
    ("stored", "record", "expected"),
    [
        # The cases found in the 2026-11-14 seed: older listings' venues, renamed.
        ("Skydive Madrid (Aeródromo de Lillo)", "Aeródromo de Lillo", "name"),
        (
            "Skydive Bulgaria dropzone, Ihtiman Airfield (LBHT)",
            "Ihtiman Airfield",
            "name",
        ),
        ("Sapareva Banya Airport", "Sapareva Banya Airfield (Kraynitsi)", "name"),
        ("Shumen Airfield (Gradishte)", "Shumen Gradishte Airfield", "name"),
        (
            "Aeródromo de Proença-a-Nova",
            "Aeródromo Municipal de Proença-a-Nova (Moitas)",
            "name",
        ),
        ("Kopaida Airfield", "Kopaida Airfield (Kastro)", "name"),
        # Two airfields of one town; generic words alone; different places.
        ("Wiener Neustadt West Airfield", "Wiener Neustadt Ost Airfield", None),
        ("Aeródromo Municipal", "Skydive Centre", None),
        ("Aeródromo de Évora", "Aeródromo de Portimão", None),
    ],
)
def test_same_place_by_place_words(stored: str, record: str, expected: str | None) -> None:  # fmt: skip
    venue = devdata.StoredVenue(uuid.uuid4(), devdata.place_words(stored), None)
    found = devdata.same_place(devdata.place_words(record), (40.0, -3.0), [venue])
    assert (found[1] if found else None) == expected


def test_an_alias_only_one_record_carries_finds_the_venue_it_names(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """An operator's office stored as a venue is the airfield whose record names it; a
    brand two records carry identifies neither."""
    accounts = Accounts.create()
    actor = devdata.reviewer_actor(engine, _email(accounts, accounts.session(reviewer=True)))  # fmt: skip
    directory = DirectoryService(stores=sql_directory_store_factory(engine), clock=lambda: datetime.now(UTC))  # fmt: skip
    tag = uuid.uuid4().hex[:8]
    _only_this_run(monkeypatch, tag)
    office, brand = (
        directory.create_venue(
            actor,
            VenueInput(
                name=name,
                country="ES",
                source_url="https://example.org/office",
                checked_on=datetime.now(UTC).date(),
            ),
        )  # fmt: skip
        for name in (f"Jump Office {tag}", f"Shared Brand {tag}")
    )

    def record(key: str, name: str, aliases: list[str], lat: float) -> dict[str, Any]:
        return {
            "key": f"es-{tag}-{key}", "name": f"{name} {tag}", "aliases": aliases,
            "country": "ES", "latitude": lat, "longitude": -15.5, "status": "active",
            "sources": [{"url": "https://example.org/airfield", "checked_on": "2026-11-14"}],
        }  # fmt: skip

    folder = tmp_path / "dropzones"
    folder.mkdir()
    (folder / "ES.json").write_text(
        json.dumps(
            {
                "country": "ES",
                "dropzones": [
                    record("airfield", "Real Airfield", [f"Jump Office {tag}"], 27.78),
                    record("north", "North Strip", [f"Shared Brand {tag}"], 28.4),
                    record("south", "South Strip", [f"Shared Brand {tag}"], 27.9),
                ],
            }
        ),
        encoding="utf-8",
    )

    report = devdata.load_dropzones(engine, folder, actor, directory)
    assert report["duplicates"] == [{"key": f"es-{tag}-airfield", "matched": str(office.id), "by": "alias"}]  # fmt: skip
    assert (report["added"], report["located"]) == (2, 1)
    located, _ = directory.reviewer_venue(actor, office.id)
    assert (located.latitude, located.longitude) == (27.78, -15.5)
    untouched, _ = directory.reviewer_venue(actor, brand.id)
    assert untouched.latitude is None


def test_same_place_by_distance_and_its_limit_on_names() -> None:
    here = (38.355397, 21.479198)
    venue = devdata.StoredVenue(uuid.uuid4(), devdata.place_words("Mesolongi Civil Airfield"), here)  # fmt: skip
    near = (38.3600, 21.4792)  # ~500 m, spelled differently
    assert devdata.same_place(devdata.place_words("Messolonghi Civil Airfield"), near, [venue]) == (venue.id, "distance")  # fmt: skip
    # The same words 50 km away name another place; without coordinates, they match.
    far = (38.80, 21.48)
    words = devdata.place_words("Mesolongi Airfield")
    assert devdata.same_place(words, far, [venue]) is None
    assert devdata.same_place(words, None, [venue]) == (venue.id, "name")


def test_an_unfinished_dropzone_stays_a_draft_and_the_next_run_finishes_it(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    accounts = Accounts.create()
    actor = devdata.reviewer_actor(engine, _email(accounts, accounts.session(reviewer=True)))  # fmt: skip
    clock = lambda: datetime.now(UTC)  # noqa: E731
    directory = DirectoryService(stores=sql_directory_store_factory(engine), clock=clock)  # fmt: skip
    tag = uuid.uuid4().hex[:8]
    _only_this_run(monkeypatch, tag)
    folder = tmp_path / "dropzones"
    folder.mkdir()
    record = json.loads((FIXTURES / "ES.json").read_text(encoding="utf-8").replace("TAG", tag))  # fmt: skip
    record["dropzones"] = [d for d in record["dropzones"] if d["key"] == f"es-{tag}-closed"]  # fmt: skip
    (folder / "ES.json").write_text(json.dumps(record), encoding="utf-8")

    real = directory.set_status

    def interrupted(*_args: Any, **_kwargs: Any) -> Any:
        raise DirectoryRuleError("interrupted")

    monkeypatch.setattr(directory, "set_status", interrupted)
    first = devdata.load_dropzones(engine, folder, actor, directory)
    assert first["refused"] == [{"key": f"es-{tag}-closed", "reason": "left as draft: interrupted"}]  # fmt: skip
    assert directory.search(query=f"Closed Field {tag}", country=None, cursor=None, limit=None).items == []  # fmt: skip

    monkeypatch.setattr(directory, "set_status", real)
    second = devdata.load_dropzones(engine, folder, actor, directory)
    assert (second["resumed"], second["added"], second["closed"]) == (1, 1, 1)
    [closed] = directory.search(query=f"Closed Field {tag}", country=None, cursor=None, limit=None).items  # fmt: skip
    assert closed.status.value == "closed"


def test_dropzone_files_skip_notes(tmp_path: Path) -> None:
    for name in ("FR.json", "_coverage.json", "_osm-sweep.json", "README.md"):
        (tmp_path / name).write_text("{}")
    assert [p.name for p in devdata.dropzone_files(tmp_path)] == ["FR.json"]
    assert devdata.dropzone_files(tmp_path / "missing") == []


def test_needs_a_reviewer() -> None:
    accounts = Accounts.create()
    with pytest.raises(devdata.DevDataError):
        devdata.reviewer_actor(engine, _email(accounts, accounts.session()))


def test_refuses_outside_local(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setenv("SKYDIVER_DEV_DATA", "1")
    monkeypatch.setattr(settings, "ENVIRONMENT", "production")
    assert devdata.main(["load", "x.json", "--reviewer", "a@example.com"]) == 2


def test_refuses_without_the_explicit_opt_in(monkeypatch: pytest.MonkeyPatch) -> None:
    """ENVIRONMENT defaults to local in settings, so that alone must not be enough."""
    monkeypatch.setattr(settings, "ENVIRONMENT", "local")
    monkeypatch.delenv("SKYDIVER_DEV_DATA", raising=False)
    assert devdata.main(["load", "x.json", "--reviewer", "a@example.com"]) == 2

    local = {"SKYDIVER_DEV_DATA": "1", "ENVIRONMENT": "local"}
    assert devdata.dev_data_refusal(local, "local", "127.0.0.1") is None
    assert devdata.dev_data_refusal(local, "local", "::1") is None
    assert devdata.dev_data_refusal({"ENVIRONMENT": "local"}, "local", "localhost")
    # The setting's default without the variable itself.
    assert devdata.dev_data_refusal({"SKYDIVER_DEV_DATA": "1"}, "local", "127.0.0.1")
    assert devdata.dev_data_refusal({**local, "SKYDIVER_DEV_DATA": "yes"}, "local", "127.0.0.1")  # fmt: skip
    assert devdata.dev_data_refusal(local, "local", "db.example.org")


def test_the_hosted_load_drafts_first_and_publishes_only_the_chosen_statuses(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    accounts = Accounts.create()
    actor = devdata.reviewer_actor(engine, _email(accounts, accounts.session(reviewer=True)))  # fmt: skip
    directory = DirectoryService(stores=sql_directory_store_factory(engine), clock=lambda: datetime.now(UTC))  # fmt: skip
    tag = uuid.uuid4().hex[:8]
    _only_this_run(monkeypatch, tag)
    folder = tmp_path / "dropzones"
    folder.mkdir()
    for source in FIXTURES.iterdir():
        (folder / source.name).write_text(source.read_text(encoding="utf-8").replace("TAG", tag), encoding="utf-8")  # fmt: skip

    def public() -> list[str]:
        return sorted(v.name for v in directory.search(query=tag, country="ES", cursor=None, limit=None).items)  # fmt: skip

    def counts(report: dict[str, Any]) -> tuple[int, ...]:
        return tuple(report[k] for k in ("added", "resumed", "drafted", "skipped", "located"))  # fmt: skip

    # Step 1: drafts only. The ~500 m neighbour is still recognised, against a draft.
    first = devdata.load_dropzones(
        engine, folder, actor, directory, publish=frozenset()
    )
    assert counts(first) == (0, 0, 6, 0, 0)
    assert [d["key"] for d in first["duplicates"]] == [f"es-{tag}-near-active"]
    assert public() == []
    with engine.connect() as conn:
        note = conn.execute(text("SELECT source_note FROM skydiver_venue WHERE name = :n"), {"n": f"Active Field {tag}"}).scalar_one()  # fmt: skip
    # Shown on the public page once published: words, not the local-only marker.
    assert note == f"Research status: active. Inventory ref es-{tag}-active."

    # Step 2: the owner publishes active dropzones with coordinates; the rest wait.
    second = devdata.load_dropzones(engine, folder, actor, directory, publish=frozenset({"active"}))  # fmt: skip
    assert counts(second) == (3, 3, 3, 0, 0)
    assert public() == sorted([f"Active Field {tag}", f"Second Field {tag}", f"Active {tag} West Field"])  # fmt: skip

    again = devdata.load_dropzones(engine, folder, actor, directory, publish=frozenset({"active"}))  # fmt: skip
    assert counts(again) == (0, 0, 3, 3, 0)


def test_a_venue_loaded_before_details_existed_gets_them_on_the_next_run(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    accounts = Accounts.create()
    actor = devdata.reviewer_actor(engine, _email(accounts, accounts.session(reviewer=True)))  # fmt: skip
    directory = DirectoryService(stores=sql_directory_store_factory(engine), clock=lambda: datetime.now(UTC))  # fmt: skip
    tag = uuid.uuid4().hex[:8]
    _only_this_run(monkeypatch, tag)
    # As an earlier run left it: loaded by key, public, without details.
    old = directory.create_venue(actor, VenueInput(
        name=f"Old Field {tag}", country="ES", source_url="https://example.org/old",
        checked_on=datetime.now(UTC).date(), latitude=40.9, longitude=-4.1,
        source_note=f"dev-data:es-{tag}-old Unreviewed candidate, local development only.",
    ))  # fmt: skip
    record = {
        "key": f"es-{tag}-old", "name": f"Old Field {tag}", "aliases": [], "country": "ES",
        "latitude": 40.9, "longitude": -4.1, "status": "seasonal",
        "operators": [{"name": f"Club {tag}", "website": None, "facebook": "https://www.facebook.com/club"}],
        "season": "May–September", "aircraft": None,
        "sources": [{"url": "https://example.org/old", "checked_on": "2026-11-14"}],
    }  # fmt: skip
    folder = tmp_path / "dropzones"
    folder.mkdir()
    (folder / "ES.json").write_text(json.dumps({"country": "ES", "dropzones": [record]}), encoding="utf-8")  # fmt: skip

    report = devdata.load_dropzones(engine, folder, actor, directory)
    assert (report["skipped"], report["detailed"]) == (1, 1)
    venue, events = directory.reviewer_venue(actor, old.id)
    assert venue.operators == (
        Operator(f"Club {tag}", "https://www.facebook.com/club"),
    )
    assert (venue.season, venue.aircraft) == ("May–September", None)
    assert events[-1].kind == "details_updated"
    # Never over details a reviewer has set: the next run leaves them alone.
    again = devdata.load_dropzones(engine, folder, actor, directory)
    assert again["detailed"] == 0


def test_details_of_a_merged_research_venue_go_to_the_surviving_one(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """The research copy of an older venue was merged into it: the older one gets them."""
    accounts = Accounts.create()
    actor = devdata.reviewer_actor(engine, _email(accounts, accounts.session(reviewer=True)))  # fmt: skip
    directory = DirectoryService(stores=sql_directory_store_factory(engine), clock=lambda: datetime.now(UTC))  # fmt: skip
    tag = uuid.uuid4().hex[:8]
    _only_this_run(monkeypatch, tag)
    today = datetime.now(UTC).date()
    older = directory.create_venue(actor, VenueInput(
        name=f"Older Field {tag}", country="GR", source_url="https://example.org/older", checked_on=today,
    ))  # fmt: skip
    copy = directory.create_venue(actor, VenueInput(
        name=f"Older Field {tag} (Copy)", country="GR", source_url="https://example.org/copy",
        checked_on=today, source_note=f"dev-data:gr-{tag}-older Unreviewed candidate, local development only.",
    ))  # fmt: skip
    directory.merge(actor, copy.id, older.id)
    record = {
        "key": f"gr-{tag}-older", "name": f"Older Field {tag} (Copy)", "aliases": [], "country": "GR",
        "latitude": 38.45, "longitude": 23.14, "status": "active",
        "operators": [{"name": f"Skydive {tag}", "website": "https://skydive.example/"}],
        "sources": [{"url": "https://example.org/copy", "checked_on": "2026-11-14"}],
    }  # fmt: skip
    folder = tmp_path / "dropzones"
    folder.mkdir()
    (folder / "GR.json").write_text(json.dumps({"country": "GR", "dropzones": [record]}), encoding="utf-8")  # fmt: skip

    report = devdata.load_dropzones(engine, folder, actor, directory)
    assert (report["skipped"], report["detailed"]) == (1, 1)
    survivor, _ = directory.reviewer_venue(actor, older.id)
    assert survivor.operators == (
        Operator(f"Skydive {tag}", "https://skydive.example/"),
    )


def test_details_drop_a_quirk_instead_of_the_record() -> None:
    long_name = "N" * 200
    details = devdata._details({
        "operators": [
            {"name": long_name, "website": "https://long.example/"},  # too long: dropped
            {"name": "Club", "website": "not a link", "facebook": "https://fb.example/club"},
            {"name": "club", "website": "https://dup.example/"},  # the same name again
            {"name": "Two", "website": None, "facebook": None},
            {"name": "Three"}, {"name": "Four"}, {"name": "Five"},  # only four are kept
        ],
        "season": "  all   year ", "aircraft": "A" * 300,
    })  # fmt: skip
    assert details["operators"] == [
        {"name": "Club", "url": "https://fb.example/club"},
        {"name": "Two", "url": None},
        {"name": "Three", "url": None},
        {"name": "Four", "url": None},
    ]
    assert details["season"] == "all year"
    assert len(details["aircraft"]) == 160 and details["aircraft"].endswith("…")


def test_the_hosted_load_runs_only_from_the_staging_script(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    args = ["dropzones", str(tmp_path), "--reviewer", "a@example.com"]
    monkeypatch.setenv("ENVIRONMENT", "local")
    monkeypatch.setenv("DATABASE_URL", "postgresql://example.invalid/db")
    assert devdata.main(args) == 2
    monkeypatch.setenv("ENVIRONMENT", "staging")
    monkeypatch.delenv("DATABASE_URL")
    assert devdata.main(args) == 2
    assert devdata.hosted_refusal({"ENVIRONMENT": "staging", "DATABASE_URL": "postgresql://x/y"}) is None  # fmt: skip
    with pytest.raises(SystemExit):
        devdata.main([*args, "--publish", "active,listed"])  # not a research status


def test_refuses_a_dropzones_path_that_is_not_a_folder(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("SKYDIVER_DEV_DATA", "1")
    monkeypatch.setenv("ENVIRONMENT", "local")
    monkeypatch.setattr(settings, "ENVIRONMENT", "local")
    monkeypatch.setattr(settings, "POSTGRES_SERVER", "127.0.0.1")
    missing = str(tmp_path / "nowhere")
    args = ["load", "x.json", "--reviewer", "a@example.com", "--dropzones", missing]
    assert devdata.main(args) == 2


def test_the_dev_listings_file_matches_what_the_loader_reads() -> None:
    data = json.loads((REPO / "docs/product/inventory/dev-listings.json").read_text())
    providers = {p["key"] for p in data["providers"]}
    venues = {v["key"] for v in data["venues"]}
    assert all(v["source_url"] for v in data["venues"])
    for o in data["opportunities"]:
        assert o["provider"] in providers, o["title"]
        assert o["venue"] is None or o["venue"] in venues, o["title"]
        assert o["category"] in ("event", "boogie", "camp", "course"), o["title"]
    # Notes go through the source-note length rule (a 286-character note once broke seeding).
    for p in data["providers"]:
        note = devdata._note(p["key"], p.get("note"))
        assert len(note) <= SOURCE_NOTE_MAX and note.endswith(p.get("note") or "."), p["key"]  # fmt: skip
    assert len(devdata._note("k" * 60, "x" * 500)) == SOURCE_NOTE_MAX
