"""The logbook as a spreadsheet (CSV) over HTTP, and its round trip through the import."""

import csv
import io
import uuid
from collections.abc import Iterator
from datetime import UTC, datetime
from typing import Any

import httpx2
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient

from app.core.db import engine
from app.skydiver.access.http import AccessDependencies
from app.skydiver.directory.api import create_router as create_directory_router
from app.skydiver.directory.service import DirectoryService
from app.skydiver.directory.store import sql_directory_store_factory
from app.skydiver.gear.api import create_router as create_gear_router
from app.skydiver.gear.service import GearService
from app.skydiver.gear.store import sql_gear_store_factory
from app.skydiver.imports.api import create_router as create_import_router
from app.skydiver.imports.service import ImportService
from app.skydiver.imports.store import sql_import_store_factory
from app.skydiver.logbook.api import create_router as create_logbook_router
from app.skydiver.logbook.service import LogbookService
from app.skydiver.logbook.store import sql_logbook_store_factory
from app.skydiver.opportunities.service import OpportunityService
from app.skydiver.opportunities.store import sql_listing_store_factory
from app.skydiver.records.api import create_router
from app.skydiver.records.service import RecordsService
from app.skydiver.records.spreadsheet import BOM, HEADINGS
from app.skydiver.records.store import sql_records_store_factory
from app.tests.skydiver.support import Accounts

NOW = datetime(2026, 11, 12, 12, 0, tzinfo=UTC)
SOURCE = {"source_url": "https://example.org/dz", "checked_on": "2026-11-01"}


class Api:
    def __init__(self, client: TestClient, accounts: Accounts) -> None:
        self.client = client
        self.accounts = accounts
        self.reviewer = accounts.session(reviewer=True)

    def call(self, method: str, path: str, secret: str | None = None, body: Any = None, **params: Any) -> httpx2.Response:  # fmt: skip
        headers = {"authorization": f"Bearer {secret}"} if secret else {}
        return self.client.request(
            method, f"/api/skydiver/v1{path}", json=body, headers=headers,
            params=params or None,
        )  # fmt: skip

    def ok(self, method: str, path: str, secret: str, body: Any = None, status: int = 200) -> Any:  # fmt: skip
        response = self.call(method, path, secret, body)
        assert response.status_code == status, response.text
        return response.json() if response.content else None

    def venue(self, name: str) -> str:
        body = {"name": name, "country": "ES", **SOURCE}
        venue = self.ok("POST", "/directory/venues", self.reviewer, body, 201)
        self.ok(
            "POST", f"/directory/venues/{venue['id']}/status", self.reviewer,
            {"status": "listed"},
        )  # fmt: skip
        return str(venue["id"])

    def jump(self, secret: str, **fields: Any) -> dict[str, Any]:
        body = {
            "client_key": str(uuid.uuid4()), "jumped_on": "2026-10-10",
            "jump_type": "belly", "confirm_distinct": True, **fields,
        }  # fmt: skip
        return dict(self.ok("POST", "/jumps", secret, body, 201)["jump"])

    def sheet(self, secret: str, **params: str) -> httpx2.Response:
        return self.call("GET", "/records/spreadsheet", secret, **params)

    def jumps(self, secret: str) -> list[dict[str, Any]]:
        """Every jump of the account in full, oldest first."""
        page = self.call("GET", "/jumps/in-order", secret).json()
        return list(page["items"])


@pytest.fixture(scope="module")
def api() -> Iterator[Api]:
    accounts = Accounts.create()
    directory = DirectoryService(stores=sql_directory_store_factory(engine), clock=lambda: NOW)  # fmt: skip
    records = RecordsService(
        stores=sql_records_store_factory(engine), clock=lambda: NOW, directory=directory,
        opportunities=OpportunityService(stores=sql_listing_store_factory(engine), clock=lambda: NOW),
    )  # fmt: skip
    logbook = LogbookService(stores=sql_logbook_store_factory(engine), clock=lambda: NOW, directory=directory)  # fmt: skip
    imports = ImportService(stores=sql_import_store_factory(engine), clock=lambda: NOW)
    gear = GearService(stores=sql_gear_store_factory(engine), clock=lambda: NOW)
    access = AccessDependencies(lambda: accounts.service)
    app = FastAPI()
    app.include_router(
        create_router(
            service=lambda: records, identity=lambda: accounts.service, access=access,
            client_ip=lambda _: "203.0.113.11",
        )
    )  # fmt: skip
    app.include_router(
        create_import_router(
            service=lambda: imports, identity=lambda: accounts.service, access=access
        )  # fmt: skip
    )
    app.include_router(create_logbook_router(service=lambda: logbook, access=access))
    app.include_router(create_directory_router(service=lambda: directory, access=access))  # fmt: skip
    app.include_router(create_gear_router(service=lambda: gear, access=access))
    with TestClient(app) as client:
        yield Api(client, accounts)


def _rows(raw: bytes) -> list[list[str]]:
    return list(csv.reader(io.StringIO(raw.decode("utf-8-sig"), newline="")))


def test_csv_has_a_bom_crlf_rfc4180_quoting_and_the_import_headings(api: Api) -> None:
    owner = api.accounts.session()
    place = api.ok("POST", "/places", owner, {"name": "Farm, strip", "country": "PT"}, 201)  # fmt: skip
    api.jump(
        owner, place_id=place["id"], jump_number=7, aircraft='Cessna "Caravan"',
        notes="Line one, with a comma\nLine \"two\"", exit_altitude=4000,
        deployment_altitude=1200, altitude_unit="m", freefall_seconds=55,
        jump_type="hop_and_pop",
    )  # fmt: skip
    response = api.sheet(owner)
    assert response.status_code == 200, response.text
    assert response.headers["content-type"] == "text/csv; charset=utf-8"
    assert response.headers["cache-control"] == "no-store"
    assert response.headers["content-disposition"].startswith(
        'attachment; filename="load-organiser-logbook-'
    )
    raw = response.content
    assert raw.startswith(BOM.encode("utf-8"))
    text = raw.decode("utf-8")
    assert text.count("\r\n") == 2  # heading and one row; the note's own break stays \n
    assert '"Farm, strip"' in text
    assert '"Cessna ""Caravan"""' in text
    assert '"Line one, with a comma\nLine ""two"""' in text
    heading, row = _rows(raw)
    assert tuple(heading) == HEADINGS
    assert row == [
        "2026-10-10", "7", "Farm, strip", "PT", "Hop and pop", 'Cessna "Caravan"',
        "4000", "m", "1200", "55", 'Line one, with a comma\nLine "two"', "",
    ]  # fmt: skip


def test_text_a_spreadsheet_would_run_as_a_formula_is_guarded(api: Api) -> None:
    owner = api.accounts.session()
    place = api.ok("POST", "/places", owner, {"name": "@home", "country": "PT"}, 201)
    api.jump(
        owner, place_id=place["id"], notes='=HYPERLINK("https://x.example","y")',
        aircraft="+1 Otter", other_gear="-rented rig",
    )  # fmt: skip
    api.jump(owner, place_id=place["id"], jumped_on="2026-10-11", notes="'quoted")
    _, first, second = _rows(api.sheet(owner).content)
    by = dict(zip(HEADINGS, first, strict=True))
    assert by["Place"] == "'@home"
    assert by["Notes"] == '\'=HYPERLINK("https://x.example","y")'
    assert by["Aircraft"] == "'+1 Otter"
    assert by["Gear"] == "'-rented rig"
    # Text already starting with an apostrophe keeps it through an import.
    assert dict(zip(HEADINGS, second, strict=True))["Notes"] == "''quoted"


def test_only_the_owners_jumps_within_the_dates(api: Api) -> None:
    owner, other = api.accounts.session(), api.accounts.session()
    venue = api.venue(f"Ss{uuid.uuid4().hex[:8]} DZ")
    for day in ("2026-09-30", "2026-10-01", "2026-10-31", "2026-11-01"):
        api.jump(owner, venue_id=venue, jumped_on=day)
    api.jump(other, venue_id=venue, notes="someone else's")
    ranged = api.sheet(owner, from_on="2026-10-01", until_on="2026-10-31")
    assert [r[0] for r in _rows(ranged.content)[1:]] == ["2026-10-01", "2026-10-31"]
    assert b"someone else" not in ranged.content
    # Another person gets only their own jump; nobody gets anything without a session.
    theirs = _rows(api.sheet(other).content)[1:]
    assert [r[10] for r in theirs] == ["someone else's"]
    assert api.call("GET", "/records/spreadsheet").status_code == 401
    empty = api.accounts.session()
    assert _rows(api.sheet(empty).content) == [list(HEADINGS)]


def test_a_reversed_range_is_refused_and_downloads_are_throttled(api: Api) -> None:
    owner = api.accounts.session()
    reversed_range = api.sheet(owner, from_on="2026-10-02", until_on="2026-10-01")
    assert (reversed_range.status_code, reversed_range.json()) == (
        422,
        {"detail": "date_range_invalid"},
    )
    assert api.sheet(owner).status_code == 200
    again = api.sheet(owner)
    assert again.status_code == 429
    assert int(again.headers["retry-after"]) > 0
    # The JSON export has its own allowance.
    assert api.call("GET", "/records/export", owner).status_code == 200


def test_importing_the_file_into_an_empty_account_gives_the_same_jumps(
    api: Api,
) -> None:
    owner = api.accounts.session()
    tag = uuid.uuid4().hex[:8]
    venue = api.venue(f"Rt{tag} Skydive")
    pt = api.ok("POST", "/places", owner, {"name": "Olive grove", "country": "PT"}, 201)
    gr = api.ok("POST", "/places", owner, {"name": "Olive grove", "country": "GR"}, 201)
    main = api.ok(
        "POST", "/gear/components", owner,
        {"client_key": str(uuid.uuid4()), "kind": "main", "label": "Sabre 170"}, 201,
    )["component"]  # fmt: skip
    api.jump(
        owner, venue_id=venue, jump_number=120, jump_type="freefly",
        aircraft="Cessna 208 SX-ABC", exit_altitude=13500, deployment_altitude=3500,
        altitude_unit="ft", freefall_seconds=60, notes="First, \"best\"\nload",
        component_ids=[main["id"]], other_gear="borrowed helmet",
    )  # fmt: skip
    api.jump(owner, place_id=pt["id"], jumped_on="2026-10-11", jump_type="other",
             exit_altitude=4000, altitude_unit="m", notes="=1+1")  # fmt: skip
    api.jump(owner, place_id=gr["id"], jumped_on="2026-10-12", jump_type="unspecified")
    api.jump(owner, place_id=gr["id"], jumped_on="2026-10-13", jump_type="crw",
             deployment_altitude=900, altitude_unit="m")  # fmt: skip
    raw = api.sheet(owner).content

    target = api.accounts.session()
    imported = api.client.post(
        "/api/skydiver/v1/jumps/import", content=raw,
        headers={"authorization": f"Bearer {target}", "content-type": "text/csv"},
    )  # fmt: skip
    assert imported.status_code == 200, imported.text
    assert imported.json()["item"]["counts"] == {
        "rows": 4, "jumps": 4, "new_places": 2, "skipped": 0,
    }  # fmt: skip

    def facts(jump: dict[str, Any]) -> tuple[Any, ...]:
        loc = jump["location"]
        return (
            jump["jumped_on"], jump["jump_number"], loc["kind"], loc["name"],
            loc["country"], jump["jump_type"], jump["aircraft"], jump["exit_altitude"],
            jump["deployment_altitude"], jump["altitude_unit"],
            jump["freefall_seconds"], jump["notes"],
        )  # fmt: skip

    source, copy = api.jumps(owner), api.jumps(target)
    assert [facts(j) for j in copy] == [facts(j) for j in source]
    assert copy[0]["location"]["id"] == venue  # the listed dropzone, not a copy
    # Gear links become text: the labels and other equipment, in "other equipment".
    assert copy[0]["components"] == []
    assert copy[0]["other_gear"] == "Sabre 170; borrowed helmet"
    # Same-named private places in two countries stay two places.
    places = api.ok("GET", "/places", target)
    assert sorted((p["name"], p["country"]) for p in places) == [
        ("Olive grove", "GR"), ("Olive grove", "PT"),
    ]  # fmt: skip


def test_long_gear_is_cut_to_fit_and_the_file_still_imports(api: Api) -> None:
    owner = api.accounts.session()
    place = api.ok("POST", "/places", owner, {"name": "Gear strip", "country": "PT"}, 201)  # fmt: skip
    parts = []
    for n in range(3):
        body = {"client_key": str(uuid.uuid4()), "kind": "other", "label": f"{n}" + "x" * 79}  # fmt: skip
        parts.append(api.ok("POST", "/gear/components", owner, body, 201)["component"]["id"])  # fmt: skip
    api.jump(owner, place_id=place["id"], component_ids=parts)
    raw = api.sheet(owner).content
    gear = _rows(raw)[1][11]
    assert len(gear) == 200 and gear.endswith("\u2026")
    target = api.accounts.session()
    imported = api.client.post(
        "/api/skydiver/v1/jumps/import", content=raw,
        headers={"authorization": f"Bearer {target}", "content-type": "text/csv"},
    )  # fmt: skip
    assert imported.status_code == 200, imported.text
    assert imported.json()["item"]["counts"]["skipped"] == 0
    (copy,) = api.jumps(target)
    assert copy["other_gear"] == gear


def test_a_failed_download_does_not_use_up_the_five_minutes(
    api: Api, monkeypatch: pytest.MonkeyPatch
) -> None:
    owner = api.accounts.session()

    def broken(*_: Any, **__: Any) -> bytes:
        raise RuntimeError("database went away")

    monkeypatch.setattr(RecordsService, "spreadsheet", broken)
    with pytest.raises(RuntimeError):
        api.sheet(owner)
    monkeypatch.undo()
    assert api.sheet(owner).status_code == 200
    assert api.sheet(owner).status_code == 429
