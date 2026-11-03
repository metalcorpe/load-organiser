"""#151 suggestions, corrections and reports over HTTP against real PostgreSQL."""

import json
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
from app.skydiver.moderation import service as moderation_service
from app.skydiver.moderation.api import create_router
from app.skydiver.moderation.service import SubmissionService
from app.skydiver.moderation.store import sql_submission_store_factory
from app.skydiver.opportunities.service import OpportunityService
from app.skydiver.opportunities.store import sql_listing_store_factory
from app.tests.skydiver.support import Accounts

SOURCE = {"source_url": "https://example.org/dz", "checked_on": "2026-11-01"}


class Api:
    def __init__(self, client: TestClient, accounts: Accounts, gate: dict[str, bool]):
        self.client = client
        self.accounts = accounts
        self.gate = gate
        self.reviewer = accounts.session(reviewer=True)

    def call(
        self, method: str, path: str, secret: str | None = None, body: Any = None
    ) -> httpx2.Response:
        headers = {"authorization": f"Bearer {secret}"} if secret else {}
        return self.client.request(
            method, f"/api/skydiver/v1{path}", json=body, headers=headers
        )

    def venue(self) -> dict[str, Any]:
        body = {"name": f"Zm{uuid.uuid4().hex[:8]} DZ", "country": "ES", **SOURCE}
        response = self.call("POST", "/directory/venues", self.reviewer, body)
        assert response.status_code == 201
        return dict(response.json())

    def submit(self, secret: str, **body: Any) -> httpx2.Response:
        payload = {"client_key": str(uuid.uuid4()), "message": "Dates moved", **body}
        return self.call("POST", "/submissions", secret, payload)


@pytest.fixture(scope="module")
def api() -> Iterator[Api]:
    accounts = Accounts.create()
    gate = {"open": True}
    directory = DirectoryService(
        stores=sql_directory_store_factory(engine), clock=lambda: datetime.now(UTC)
    )
    opportunities = OpportunityService(
        stores=sql_listing_store_factory(engine), clock=lambda: datetime.now(UTC)
    )
    submissions = SubmissionService(
        stores=sql_submission_store_factory(engine),
        clock=lambda: datetime.now(UTC),
        directory=directory,
        opportunities=opportunities,
        is_open=lambda: gate["open"],
    )
    access = AccessDependencies(lambda: accounts.service)
    app = FastAPI()
    app.include_router(create_router(service=lambda: submissions, access=access))
    app.include_router(
        create_directory_router(service=lambda: directory, access=access)
    )
    with TestClient(app) as client:
        yield Api(client, accounts, gate)


def test_correction_is_reviewed_without_revealing_the_submitter(api: Api) -> None:
    venue = api.venue()
    member = api.accounts.session()
    sent = api.submit(
        member, kind="correction", target_kind="venue", target_id=venue["id"],
        message="  The dropzone moved to the north field.  ",
        source_url="https://example.org/news",
    )  # fmt: skip
    assert sent.status_code == 201, sent.text
    item = sent.json()
    assert item["status"] == "open"
    assert item["message"] == "The dropzone moved to the north field."

    queue = api.call("GET", "/directory/submissions?limit=50", api.reviewer).json()[
        "items"
    ]
    case = next(i for i in queue if i["id"] == item["id"])
    member_id = api.accounts.service.current_viewer(secret=member).account_id
    assert str(member_id) not in json.dumps(case)
    assert "submitter" not in json.dumps(case)

    resolved = api.call(
        "POST", f"/directory/submissions/{item['id']}/resolve", api.reviewer,
        {"status": "accepted", "note": "Location updated.", "version": case["version"]},
    )  # fmt: skip
    assert resolved.status_code == 200 and resolved.json()["status"] == "accepted"
    again = api.call(
        "POST", f"/directory/submissions/{item['id']}/resolve", api.reviewer,
        {"status": "declined", "version": case["version"]},
    )  # fmt: skip
    assert again.status_code == 409 and again.json() == {"detail": "edit_conflict"}

    mine = api.call("GET", "/submissions", member).json()
    assert [(m["id"], m["status"], m["resolution_note"]) for m in mine] == [
        (item["id"], "accepted", "Location updated.")
    ]
    other = api.accounts.session()
    assert api.call("GET", "/submissions", other).json() == []


def test_retry_with_the_same_key_is_not_a_duplicate(api: Api) -> None:
    member = api.accounts.session()
    key = str(uuid.uuid4())
    body = {"client_key": key, "kind": "suggest_venue", "message": "Add Skydive X"}
    first = api.call("POST", "/submissions", member, body)
    second = api.call("POST", "/submissions", member, body)
    assert (first.status_code, second.status_code) == (201, 200)
    assert first.json()["id"] == second.json()["id"]
    reused = api.call("POST", "/submissions", member, {**body, "message": "Other"})
    assert reused.status_code == 409
    assert reused.json() == {"detail": "submission_key_reused"}


@pytest.mark.parametrize(
    ("body", "expected"),
    [
        ({"kind": "report"}, "target_required"),
        ({"kind": "correction", "target_kind": "venue"}, "target_incomplete"),
        (
            {
                "kind": "report",
                "target_kind": "opportunity",
                "target_id": str(uuid.uuid4()),
            },
            "target_unavailable",
        ),
        ({"kind": "suggest_listing", "message": "   "}, "message_required"),
        ({"kind": "suggest_listing", "source_url": "ftp://x"}, "source_url_invalid"),
    ],
)
def test_submission_validation(api: Api, body: dict[str, Any], expected: str) -> None:
    response = api.submit(api.accounts.session(), **body)
    assert response.status_code == 422 and response.json() == {"detail": expected}


def test_access_limits_and_pause(api: Api, monkeypatch: pytest.MonkeyPatch) -> None:
    assert api.submit("", kind="suggest_venue").status_code == 401
    unverified = api.accounts.session(verified=False)
    assert api.submit(unverified, kind="suggest_venue").status_code == 403
    member = api.accounts.session()
    assert api.call("GET", "/directory/submissions", member).status_code == 403

    monkeypatch.setattr(moderation_service, "DAILY_LIMIT", 2)
    for _ in range(2):
        assert api.submit(member, kind="suggest_venue").status_code == 201
    over = api.submit(member, kind="suggest_venue")
    assert over.status_code == 409
    assert over.json() == {"detail": "submission_limit_reached"}

    api.gate["open"] = False
    try:
        paused = api.submit(api.accounts.session(), kind="suggest_venue")
        assert paused.status_code == 503
        assert paused.json() == {"detail": "submissions_paused"}
    finally:
        api.gate["open"] = True
