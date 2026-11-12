"""#155 personal export and empty-record restore over HTTP against PostgreSQL."""

import json
import threading
import uuid
from collections.abc import Iterator
from concurrent.futures import ThreadPoolExecutor
from contextlib import contextmanager
from datetime import UTC, datetime
from typing import Any

import httpx2
import pytest
from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlmodel import Session, col, func, select

from app.core.db import engine
from app.skydiver.access.http import AccessDependencies
from app.skydiver.access.policy import Actor
from app.skydiver.directory.api import create_router as create_directory_router
from app.skydiver.directory.service import DirectoryService
from app.skydiver.directory.store import sql_directory_store_factory
from app.skydiver.directory.tables import SkydiverProvisionalPlace
from app.skydiver.gear.api import create_router as create_gear_router
from app.skydiver.gear.service import GearService
from app.skydiver.gear.store import sql_gear_store_factory
from app.skydiver.history.api import create_router as create_history_router
from app.skydiver.history.service import HistoryService
from app.skydiver.history.store import sql_history_store_factory
from app.skydiver.logbook.api import create_router as create_logbook_router
from app.skydiver.logbook.service import LogbookService
from app.skydiver.logbook.store import sql_logbook_store_factory
from app.skydiver.opportunities.api import create_router as create_opportunity_router
from app.skydiver.opportunities.service import OpportunityService
from app.skydiver.opportunities.store import sql_listing_store_factory
from app.skydiver.records.api import PASSWORD_HEADER, create_router
from app.skydiver.records.policy import RAW_MAX_BYTES, ArchiveInvalid
from app.skydiver.records.service import RecordsNotEmpty, RecordsService
from app.skydiver.records.store import SqlRecordsStore, sql_records_store_factory
from app.skydiver.records.tables import SkydiverRestoreReceipt
from app.skydiver.saves.api import create_router as create_saves_router
from app.skydiver.saves.service import SavesService
from app.skydiver.saves.store import sql_saves_store_factory
from app.tests.skydiver.support import PASSWORD, Accounts

NOW = datetime(2026, 11, 3, 12, 0, tzinfo=UTC)
SOURCE = {"source_url": "https://example.org/dz", "checked_on": "2026-11-01"}


class Api:
    def __init__(self, client: TestClient, accounts: Accounts, records: RecordsService) -> None:  # fmt: skip
        self.client = client
        self.accounts = accounts
        self.records = records
        self.reviewer = accounts.session(reviewer=True)

    def call(
        self, method: str, path: str, secret: str | None = None, body: Any = None,
        **params: Any,
    ) -> httpx2.Response:  # fmt: skip
        headers = {"authorization": f"Bearer {secret}"} if secret else {}
        return self.client.request(
            method, f"/api/skydiver/v1{path}", json=body, headers=headers,
            params=params or None,
        )  # fmt: skip

    def ok(self, method: str, path: str, secret: str, body: Any = None, status: int = 200, **params: Any) -> Any:  # fmt: skip
        response = self.call(method, path, secret, body, **params)
        assert response.status_code == status, response.text
        return response.json() if response.content else None

    def send(
        self, path: str, secret: str, raw: bytes, *, password: str | None = None,
        content_type: str = "application/json",
    ) -> httpx2.Response:  # fmt: skip
        headers = {"authorization": f"Bearer {secret}", "content-type": content_type}
        if password is not None:
            headers[PASSWORD_HEADER] = password
        return self.client.post(f"/api/skydiver/v1{path}", content=raw, headers=headers)

    def export(self, secret: str) -> bytes:
        response = self.call("GET", "/records/export", secret)
        assert response.status_code == 200, response.text
        assert response.headers["cache-control"] == "no-store"
        assert response.headers["content-disposition"].startswith(
            'attachment; filename="load-organiser-records-'
        )
        return response.content

    def restore(self, secret: str, raw: bytes, password: str = PASSWORD) -> httpx2.Response:  # fmt: skip
        return self.send("/records/restore", secret, raw, password=password)

    def venue(self, name: str) -> str:
        body = {"name": name, "country": "ES", **SOURCE}
        venue = self.ok("POST", "/directory/venues", self.reviewer, body, 201)
        self.ok(
            "POST", f"/directory/venues/{venue['id']}/status", self.reviewer,
            {"status": "listed"},
        )  # fmt: skip
        return str(venue["id"])

    def listing(self, title: str) -> str:
        provider = self.ok(
            "POST", "/directory/providers", self.reviewer,
            {"name": f"{title} Org", "kind": "organization", **SOURCE, "publish": True},
            201,
        )  # fmt: skip
        body = {
            "title": title, "category": "boogie", "provider_id": provider["id"],
            "country": "ES", "location_note": "Airfield", "starts_on": "2026-12-04",
            "ends_on": "2026-12-08", "time_zone": "Europe/Madrid",
            "registration_url": "https://example.org/register", **SOURCE,
        }  # fmt: skip
        item = self.ok("POST", "/directory/opportunities", self.reviewer, body, 201)
        for status in ("review", "published"):
            self.ok(
                "POST", f"/directory/opportunities/{item['id']}/status", self.reviewer,
                {"status": status},
            )  # fmt: skip
        return str(item["id"])

    def populate(self, secret: str) -> dict[str, Any]:
        """A little of everything an account can hold."""
        tag = uuid.uuid4().hex[:8]
        venue = self.venue(f"Rc{tag} DZ")
        listing = self.listing(f"Rc{tag} Boogie")
        place = self.ok("POST", "/places", secret, {"name": "Farm strip", "country": "PT"}, 201)["id"]  # fmt: skip
        main = self.ok(
            "POST", "/gear/components", secret,
            {"client_key": str(uuid.uuid4()), "kind": "main", "label": "Navigator",
             "serial": "N-0042", "relation": "owned", "acquisition_method": "purchase",
             "acquired": "2024-05", "repack_interval_days": 120,
             "end_of_life_on": "2034-05-01"},
            201,
        )["component"]  # fmt: skip
        rig = self.ok("POST", "/gear/rigs", secret, {"client_key": str(uuid.uuid4()), "label": "Rig A"}, 201)  # fmt: skip
        self.ok(
            "POST", f"/gear/components/{main['id']}/rig", secret,
            {"rig_id": rig["id"], "on": "2026-01-10", "version": main["version"]},
        )  # fmt: skip
        self.ok(
            "POST", f"/gear/components/{main['id']}/service", secret,
            {"client_key": str(uuid.uuid4()), "kind": "inspection", "done_on": "2026-02-01"},
            201,
        )  # fmt: skip
        first = self.ok(
            "POST", "/jumps", secret,
            {"client_key": str(uuid.uuid4()), "jumped_on": "2026-10-10",
             "jump_type": "freefly", "venue_id": venue, "jump_number": 120,
             "exit_time": "14:05", "time_zone": "Europe/Madrid", "exit_altitude": 4000,
             "altitude_unit": "m", "altitude_datum": "agl", "notes": "Private note.",
             "links": ["https://example.org/video"], "component_ids": [main["id"]]},
            201,
        )["jump"]  # fmt: skip
        self.ok(
            "PATCH", f"/jumps/{first['id']}", secret,
            {"jump_type": "angle", "version": first["version"]},
        )  # fmt: skip
        self.ok(
            "POST", "/jumps", secret,
            {"client_key": str(uuid.uuid4()), "jumped_on": "2025-03-02",
             "jump_type": "belly", "place_id": place},
            201,
        )  # fmt: skip
        base = self.ok("PUT", "/history/baseline", secret, {"prior_jumps": 200, "before_on": "2026-01-01"})  # fmt: skip
        self.ok(
            "PUT", "/history/baseline", secret,
            {"prior_jumps": 210, "before_on": "2026-01-01", "version": base["baseline"]["version"]},
        )  # fmt: skip
        self.ok("PUT", f"/saved/{listing}", secret, status=201)
        self.ok("PUT", "/me/licence", secret, {"licence": "b"})
        self.ok(
            "POST", "/plans", secret,
            {"title": "Spring visit", "starts_on": "2027-04-01", "ends_on": "2027-04-03",
             "venue_id": venue},
            201,
        )  # fmt: skip
        return {"venue": venue, "listing": listing, "place": place, "jump": first["id"]}


@pytest.fixture(scope="module")
def api() -> Iterator[Api]:
    accounts = Accounts.create()
    directory = DirectoryService(stores=sql_directory_store_factory(engine), clock=lambda: NOW)  # fmt: skip
    opportunities = OpportunityService(stores=sql_listing_store_factory(engine), clock=lambda: NOW)  # fmt: skip
    records = RecordsService(
        stores=sql_records_store_factory(engine), clock=lambda: NOW,
        directory=directory, opportunities=opportunities,
    )  # fmt: skip
    access = AccessDependencies(lambda: accounts.service)
    app = FastAPI()
    app.include_router(
        create_router(
            service=lambda: records, identity=lambda: accounts.service, access=access,
            client_ip=lambda _: "203.0.113.7",
        )
    )  # fmt: skip
    app.include_router(
        create_directory_router(service=lambda: directory, access=access)
    )
    app.include_router(create_opportunity_router(service=lambda: opportunities, access=access))  # fmt: skip
    app.include_router(
        create_saves_router(
            service=lambda: SavesService(
                stores=sql_saves_store_factory(engine), clock=lambda: NOW,
                opportunities=opportunities, directory=directory,
            ),
            access=access,
        )
    )  # fmt: skip
    gear = GearService(stores=sql_gear_store_factory(engine), clock=lambda: NOW)
    app.include_router(create_gear_router(service=lambda: gear, access=access))
    logbook = LogbookService(stores=sql_logbook_store_factory(engine), clock=lambda: NOW, directory=directory)  # fmt: skip
    app.include_router(create_logbook_router(service=lambda: logbook, access=access))
    history = HistoryService(stores=sql_history_store_factory(engine), clock=lambda: NOW, directory=directory)  # fmt: skip
    app.include_router(create_history_router(service=lambda: history, access=access))
    with TestClient(app) as client:
        yield Api(client, accounts, records)


def _shape(archive: dict[str, Any]) -> dict[str, Any]:
    """What must survive a round trip: content, not IDs or restore markers."""
    r = archive["records"]
    return {
        "places": sorted((p["name"], p["country"]) for p in r["places"]),
        "components": [
            (
                c["label"],
                c["serial"],
                c["acquired"],
                c["repack_interval_days"],
                c["end_of_life_on"],
            )
            for c in r["components"]
        ],
        "rigs": [g["label"] for g in r["rigs"]],
        "stints": [(m["from_on"], m["until_on"]) for m in r["rig_stints"]],
        "service": [(s["kind"], s["done_on"]) for s in r["service_entries"]],
        "jumps": [
            (
                j["jumped_on"],
                j["jump_type"],
                j["jump_number"],
                j["exit_time"],
                j["time_zone"],
                j["exit_altitude"],
                j["altitude_unit"],
                j["altitude_datum"],
                j["notes"],
                j["links"],
                len(j["component_ids"]),
            )
            for j in r["jumps"]
        ],  # fmt: skip
        "jump_events": sorted(
            e["kind"] for e in r["jump_events"] if e["kind"] != "from_export"
        ),  # fmt: skip
        "baseline": (r["baseline"]["prior_jumps"], r["baseline"]["before_on"]),
        "baseline_events": [
            e["kind"] for e in r["baseline_events"] if e["kind"] != "from_export"
        ],  # fmt: skip
        "saved": [s["title"] for s in r["saved_listings"]],
        "plans": [(p["title"], p["starts_on"], p["venue_id"]) for p in r["plans"]],
        "licence": r["licence"],
    }


def test_round_trip_into_an_empty_account(api: Api) -> None:
    owner = api.accounts.session()
    made = api.populate(owner)
    raw = api.export(owner)
    archive = json.loads(raw)
    assert (archive["format"], archive["version"]) == (
        "load-organiser.personal-records",
        1,
    )
    text = raw.decode()
    # No credentials, roles or account identity travel in the file.
    for absent in (
        "password",
        "role",
        "email",
        "session",
        "owner_person_id",
        "client_key",
    ):
        assert absent not in text, absent
    assert archive["records"]["jumps"][-1]["notes"] == "Private note."
    # Instants are UTC whatever the database session's time zone.
    stamps = [archive["exported_at"]] + [
        item["created_at"] for section in ("places", "jumps", "jump_events")
        for item in archive["records"][section]
    ]  # fmt: skip
    assert all(stamp.endswith("Z") for stamp in stamps), stamps

    target = api.accounts.session()
    check = api.send("/records/restore/check", target, raw).json()
    assert check["eligible"] and check["reason"] is None
    assert check["counts"] == {
        "places": 1, "components": 1, "rigs": 1, "service_entries": 1, "jumps": 2,
        "baseline": 1, "saved_listings": 1, "plans": 1,
    }  # fmt: skip
    assert api.call("GET", "/records", target).json()["empty"]  # a check writes nothing

    done = api.restore(target, raw)
    assert done.status_code == 200, done.text
    assert done.json()["outcome"] == "restored"
    assert done.json()["counts"]["jumps"] == 2

    again = json.loads(api.export(target))
    assert _shape(again) == _shape(archive)
    assert {j["source"] for j in again["records"]["jumps"]} == {"restored"}
    assert again["records"]["baseline"]["source"] == "restored"
    # New identities: nothing in the target points at the source's records.
    source_ids = {j["id"] for j in archive["records"]["jumps"]}
    assert not source_ids & {j["id"] for j in again["records"]["jumps"]}
    assert api.call("GET", f"/jumps/{made['jump']}", target).status_code == 404
    assert api.call("GET", f"/jumps/{made['jump']}", owner).status_code == 200
    # Totals and explicit gear use agree with the source.
    assert api.ok("GET", "/history", target)["totals"] == api.ok("GET", "/history", owner)["totals"]  # fmt: skip
    uses = api.ok("GET", "/history", target)["by_component"]
    assert [(u["component"]["label"], u["jumps"]) for u in uses] == [("Navigator", 1)]
    assert archive["records"]["licence"] == "b"
    assert api.ok("GET", "/me/licence", target) == {"licence": "b"}


def test_a_set_licence_is_kept_and_does_not_block_a_restore(api: Api) -> None:
    owner, target = api.accounts.session(), api.accounts.session()
    api.ok("PUT", "/me/licence", owner, {"licence": "d"})
    api.ok("POST", "/places", owner, {"name": "Strip", "country": "PT"}, 201)
    raw = api.export(owner)
    # A licence is a setting, not a record: the target still counts as empty.
    api.ok("PUT", "/me/licence", target, {"licence": "student"})
    assert api.call("GET", "/records", target).json()["empty"]
    done = api.restore(target, raw)
    assert done.status_code == 200, done.text
    assert api.ok("GET", "/me/licence", target) == {"licence": "student"}

    # An earlier v1 file without the key restores with no licence.
    old = json.loads(raw)
    del old["records"]["licence"]
    fresh = api.accounts.session()
    assert api.restore(fresh, json.dumps(old).encode()).status_code == 200
    assert api.ok("GET", "/me/licence", fresh) == {"licence": "none"}


def test_an_earlier_file_without_gear_due_settings_restores_with_none(
    api: Api,
) -> None:
    component = {
        "id": str(uuid.uuid4()), "kind": "reserve", "label": "Reserve",
        "relation": "owned", "created_at": "2026-10-01T10:00:00Z",
        "updated_at": "2026-10-01T10:00:00Z",
    }  # fmt: skip
    target = api.accounts.session()
    raw = json.dumps(_archive(components=[component])).encode()
    done = api.restore(target, raw)
    assert done.status_code == 200, done.text
    (restored,) = json.loads(api.export(target))["records"]["components"]
    assert (restored["repack_interval_days"], restored["end_of_life_on"]) == (
        None,
        None,
    )
    # Out-of-range settings are refused before any write.
    bad = json.dumps(_archive(components=[component | {"repack_interval_days": 0}]))
    response = api.send(
        "/records/restore/check",
        api.accounts.session(),
        bad.encode(),
        password=PASSWORD,
    )
    assert response.status_code == 422


def test_an_exact_repeat_is_already_restored_and_writes_nothing(api: Api) -> None:
    owner, target = api.accounts.session(), api.accounts.session()
    api.ok("POST", "/places", owner, {"name": "Strip", "country": "PT"}, 201)
    raw = api.export(owner)
    first = api.restore(target, raw).json()
    place = api.ok("GET", "/places", target)[0]
    api.ok("DELETE", f"/places/{place['id']}", target, status=204)

    repeat = api.restore(target, raw)
    assert repeat.status_code == 200
    assert repeat.json()["outcome"] == "already_restored"
    assert repeat.json()["restored_at"] == first["restored_at"]
    assert api.ok("GET", "/places", target) == []  # the deletion is not refilled
    check = api.send("/records/restore/check", target, raw).json()
    assert check["reason"] == "already_restored" and not check["eligible"]

    # The same content in another file is a different input: refused when non-empty.
    api.ok("POST", "/places", target, {"name": "Other", "country": "PT"}, 201)
    reformatted = json.dumps(json.loads(raw), indent=1).encode()
    refused = api.restore(target, reformatted)
    assert refused.status_code == 409 and refused.json() == {
        "detail": "records_not_empty"
    }


def test_non_empty_records_are_refused_before_any_write(api: Api) -> None:
    owner, target = api.accounts.session(), api.accounts.session()
    api.populate(owner)
    raw = api.export(owner)
    api.ok("POST", "/places", target, {"name": "Mine", "country": "PT"}, 201)
    check = api.send("/records/restore/check", target, raw).json()
    assert check["reason"] == "records_not_empty" and not check["eligible"]
    refused = api.restore(target, raw)
    assert refused.status_code == 409
    summary = api.ok("GET", "/records", target)
    assert summary["counts"]["places"] == 1 and summary["counts"]["jumps"] == 0
    assert summary["last_restore"] is None


def _archive(**records: Any) -> dict[str, Any]:
    empty: dict[str, Any] = {
        "places": [], "components": [], "rigs": [], "rig_stints": [],
        "service_entries": [], "gear_events": [], "jumps": [], "jump_events": [],
        "baseline": None, "baseline_events": [], "saved_listings": [], "plans": [],
    }  # fmt: skip
    references = records.pop("references", {"venues": [], "listings": []})
    return {
        "format": "load-organiser.personal-records", "version": 1,
        "exported_at": "2026-11-01T10:00:00Z", "records": empty | records,
        "references": references,
    }  # fmt: skip


def _jump(**fields: Any) -> dict[str, Any]:
    return {
        "id": str(uuid.uuid4()), "jumped_on": "2026-10-01", "jump_type": "belly",
        "links": [], "component_ids": [], "source": "manual",
        "created_at": "2026-10-01T10:00:00Z", "updated_at": "2026-10-01T10:00:00Z",
        **fields,
    }  # fmt: skip


def _place(**fields: Any) -> dict[str, Any]:
    return {
        "id": str(uuid.uuid4()), "name": "Strip", "country": "PT",
        "created_at": "2026-10-01T10:00:00Z", "updated_at": "2026-10-01T10:00:00Z",
        **fields,
    }  # fmt: skip


@pytest.mark.parametrize(
    ("raw", "status", "detail"),
    [
        (b"not json", 400, {"detail": "archive_malformed"}),
        (b"[]", 400, {"detail": "archive_malformed"}),
        (
            json.dumps(_archive() | {"version": 2}).encode(),
            400,
            {"detail": "archive_version_unsupported"},
        ),  # fmt: skip
        (
            json.dumps(_archive() | {"roles": ["reviewer"]}).encode(),
            422,
            {"detail": "archive_invalid", "problem": "roles.extra_forbidden"},
        ),  # fmt: skip
        (
            json.dumps(_archive(jumps=[_jump(place_id=str(uuid.uuid4()))])).encode(),
            422,
            {"detail": "archive_invalid", "problem": "jumps[0].place_unknown"},
        ),  # fmt: skip
        (
            json.dumps(
                _archive(
                    places=[p := _place()],
                    jumps=[
                        _jump(
                            place_id=p["id"],
                            exit_altitude=1000,
                            deployment_altitude=1500,
                            altitude_unit="m",
                        )
                    ],
                )
            ).encode(),
            422,
            {"detail": "archive_invalid", "problem": "jumps[0].deployment_above_exit"},
        ),  # fmt: skip
        (
            json.dumps(_archive(places=[_place(notes="x")])).encode(),
            422,
            {
                "detail": "archive_invalid",
                "problem": "records.places[0].notes.extra_forbidden",
            },
        ),  # fmt: skip
    ],
)
def test_malformed_and_invalid_archives_write_nothing(
    api: Api, raw: bytes, status: int, detail: dict[str, Any]
) -> None:
    target = api.accounts.session()
    for path in ("/records/restore/check", "/records/restore"):
        response = api.send(path, target, raw, password=PASSWORD)
        assert response.status_code == status, response.text
        assert response.json() == detail
    assert api.ok("GET", "/records", target)["empty"]


def test_oversized_and_wrongly_typed_bodies_are_refused(api: Api) -> None:
    target = api.accounts.session()
    big = api.send("/records/restore/check", target, b" " * (RAW_MAX_BYTES + 1))
    assert big.status_code == 413 and big.json() == {"detail": "archive_too_large"}
    text = api.send("/records/restore/check", target, b"{}", content_type="text/plain")
    assert text.status_code == 400


def test_restore_needs_a_fresh_password_and_a_confirmed_email(api: Api) -> None:
    owner, target = api.accounts.session(), api.accounts.session()
    api.ok("POST", "/places", owner, {"name": "Strip", "country": "PT"}, 201)
    raw = api.export(owner)
    wrong = api.restore(target, raw, password="not the password at all")
    assert wrong.status_code == 422
    assert wrong.json() == {"detail": "password_confirmation_failed"}
    missing = api.send("/records/restore", target, raw)
    assert missing.status_code == 422
    assert api.ok("GET", "/records", target)["empty"]
    unverified = api.accounts.session(verified=False)
    assert api.restore(unverified, raw).status_code == 403


def test_references_no_longer_public_become_private(api: Api) -> None:
    gone_venue, gone_listing = str(uuid.uuid4()), str(uuid.uuid4())
    archive = _archive(
        jumps=[_jump(venue_id=gone_venue)],
        saved_listings=[{"opportunity_id": gone_listing, "title": "Old boogie",
                         "created_at": "2026-10-01T10:00:00Z"}],
        plans=[{"title": "Trip", "starts_on": "2027-01-01", "ends_on": "2027-01-02",
                "opportunity_id": gone_listing, "created_at": "2026-10-01T10:00:00Z",
                "updated_at": "2026-10-01T10:00:00Z"}],
        references={"venues": [{"id": gone_venue, "name": "Gone DZ", "country": "FR"}],
                    "listings": [{"id": gone_listing, "title": "Old boogie"}]},
    )  # fmt: skip
    target = api.accounts.session()
    raw = json.dumps(archive).encode()
    check = api.send("/records/restore/check", target, raw).json()
    assert check["venues_to_private_places"] == 1
    assert check["plan_links_dropped"] == 1
    assert check["saved_not_restorable"] == ["Old boogie"]
    assert api.restore(target, raw).status_code == 200
    jump = api.ok("GET", "/jumps", target)["items"][0]
    assert jump["location"]["kind"] == "place"
    assert (jump["location"]["name"], jump["location"]["country"]) == ("Gone DZ", "FR")
    assert api.ok("GET", "/saved", target) == []
    plans = api.ok("GET", "/plans", target)
    assert plans[0]["title"] == "Trip" and plans[0].get("opportunity") is None


def test_export_is_rate_limited(api: Api) -> None:
    owner = api.accounts.session()
    api.export(owner)
    again = api.call("GET", "/records/export", owner)
    assert again.status_code == 429 and int(again.headers["retry-after"]) > 0


def _actor(api: Api, secret: str) -> Actor:
    viewer = api.accounts.service.current_viewer(secret=secret)
    return Actor(
        account_id=viewer.account_id, person_id=viewer.person_id,
        email_verified=True, roles=frozenset(),
    )  # fmt: skip


def _places(actor: Actor) -> int:
    with Session(engine) as session:
        return int(
            session.execute(
                select(func.count())
                .select_from(SkydiverProvisionalPlace)
                .where(col(SkydiverProvisionalPlace.owner_person_id) == actor.person_id)
            ).scalar_one()
        )


def _receipts(actor: Actor) -> int:
    with Session(engine) as session:
        return int(
            session.execute(
                select(func.count())
                .select_from(SkydiverRestoreReceipt)
                .where(col(SkydiverRestoreReceipt.owner_person_id) == actor.person_id)
            ).scalar_one()
        )


def _service(api: Api, store_type: type[SqlRecordsStore]) -> RecordsService:
    @contextmanager
    def stores() -> Iterator[SqlRecordsStore]:
        with Session(engine) as session:
            try:
                yield store_type(session)
            except BaseException:
                session.rollback()
                raise
            session.commit()

    return RecordsService(
        stores=stores, clock=lambda: NOW,
        directory=api.records._directory, opportunities=api.records._opportunities,
    )  # fmt: skip


def test_a_write_landing_during_restore_rolls_it_back(api: Api) -> None:
    owner, target = api.accounts.session(), api.accounts.session()
    api.ok("POST", "/places", owner, {"name": "Strip", "country": "PT"}, 201)
    raw = api.export(owner)
    actor = _actor(api, target)

    class Interleaved(SqlRecordsStore):
        calls = 0

        def managed_counts(self, actor: Actor) -> dict[str, int]:
            Interleaved.calls += 1
            if Interleaved.calls == 2:  # after the emptiness check, before the recount
                with Session(engine) as other:
                    other.add(SkydiverProvisionalPlace(
                        owner_person_id=actor.person_id, name="Concurrent",
                        country="PT", created_at=NOW, updated_at=NOW,
                    ))  # fmt: skip
                    other.commit()
            return super().managed_counts(actor)

    with pytest.raises(RecordsNotEmpty):
        _service(api, Interleaved).restore(actor, raw, before_write=lambda: None)
    assert _places(actor) == 1  # only the concurrent write; the restore rolled back
    assert _receipts(actor) == 0


def test_a_failure_part_way_rolls_back_everything(api: Api) -> None:
    owner, target = api.accounts.session(), api.accounts.session()
    api.populate(owner)
    raw = api.export(owner)
    actor = _actor(api, target)

    class Failing(SqlRecordsStore):
        def insert_rows(self, table: str, rows: list[dict[str, Any]]) -> None:
            if table == "plans":
                raise ArchiveInvalid("plans.constraint")
            super().insert_rows(table, rows)

    with pytest.raises(ArchiveInvalid):
        _service(api, Failing).restore(actor, raw, before_write=lambda: None)
    assert api.ok("GET", "/records", target)["empty"]
    assert _receipts(actor) == 0


def test_two_different_files_restored_at_once_never_merge(api: Api) -> None:
    """Both restores pass the emptiness check before either commits (#160 race)."""
    first, second, target = (api.accounts.session() for _ in range(3))
    api.ok("POST", "/places", first, {"name": "First strip", "country": "PT"}, 201)
    api.ok("POST", "/places", second, {"name": "Second strip", "country": "ES"}, 201)
    raws = [api.export(first), api.export(second)]
    actor = _actor(api, target)
    both_counted = threading.Barrier(2, timeout=10)

    class Simultaneous(SqlRecordsStore):
        def managed_counts(self, actor: Actor) -> dict[str, int]:
            counts = super().managed_counts(actor)
            if any(counts.values()):  # the recount, with this restore's own rows
                both_counted.wait()
            return counts

    service = _service(api, Simultaneous)

    def attempt(raw: bytes) -> str:
        try:
            return service.restore(actor, raw, before_write=lambda: None).outcome
        except RecordsNotEmpty:
            return "not_empty"

    with ThreadPoolExecutor(max_workers=2) as pool:
        results = sorted(pool.map(attempt, raws))
    assert results == ["not_empty", "restored"]
    assert _places(actor) == 1
    assert _receipts(actor) == 1
