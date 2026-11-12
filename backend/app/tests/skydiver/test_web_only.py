"""#161 closed beta: with SKYDIVER_REQUIRE_PROXY_KEY the API answers only the web server."""

import pytest
from fastapi.testclient import TestClient

from app.core.config import Settings, settings
from app.main import create_app

KEY = "k" * 40
API = "/api/skydiver/v1"


@pytest.fixture
def client(monkeypatch: pytest.MonkeyPatch) -> TestClient:
    monkeypatch.setattr(settings, "SKYDIVER_REQUIRE_PROXY_KEY", True)
    monkeypatch.setattr(settings, "SKYDIVER_WEB_PROXY_KEY", KEY)
    return TestClient(create_app(include_legacy=False))


def test_direct_callers_get_a_plain_404_everywhere_but_health(
    client: TestClient,
) -> None:
    for path in (
        "/opportunities",
        "/venues",
        "/jumps",
        "/auth/registrations",
        "/nowhere",
    ):
        for headers in ({}, {"x-organiser-proxy-key": "wrong" * 8}):
            response = client.get(API + path, headers=headers)
            assert response.status_code == 404, (path, headers)
            assert response.json() == {"detail": "Not Found"}
            assert response.headers["cache-control"] == "no-store"
    posted = client.post(API + "/auth/registrations", json={"email": "a@example.com"})
    assert posted.status_code == 404
    assert client.get(API + "/health").status_code in (200, 503)


def test_the_web_server_key_passes(client: TestClient) -> None:
    headers = {"x-organiser-proxy-key": KEY}
    assert client.get(API + "/opportunities", headers=headers).status_code == 200
    assert (
        client.get(API + "/jumps", headers=headers).status_code == 401
    )  # still needs a session


def test_requiring_the_key_without_one_refuses_to_start(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.delenv("SKYDIVER_WEB_PROXY_KEY", raising=False)
    with pytest.raises(ValueError, match="SKYDIVER_REQUIRE_PROXY_KEY"):
        Settings(
            SKYDIVER_REQUIRE_PROXY_KEY=True, SKYDIVER_WEB_PROXY_KEY=None, _env_file=None
        )  # type: ignore[call-arg]


def test_off_by_default() -> None:
    assert Settings(_env_file=None).SKYDIVER_REQUIRE_PROXY_KEY is False  # type: ignore[call-arg]
