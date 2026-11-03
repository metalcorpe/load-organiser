"""#146 deployment boundary: only the beta namespace is served by default.

Probes the composed application (`app.main`), not a router in isolation.
"""

import re
import uuid
from pathlib import Path
from typing import Literal

import pytest
from fastapi import FastAPI
from fastapi.routing import APIRoute, RouteContext, iter_route_contexts
from fastapi.testclient import TestClient
from pydantic import ValidationError
from starlette.middleware.cors import CORSMiddleware

from app.core.config import Settings, settings
from app.main import app, create_app
from app.skydiver.api import API_PREFIX
from app.tests.utils.utils import get_superuser_token_headers

DOC_PATHS = {
    "/docs",
    "/docs/oauth2-redirect",
    "/redoc",
    f"{settings.API_V1_STR}/openapi.json",
}


def _served(application: FastAPI) -> list[RouteContext]:
    # FastAPI 0.162 mounts included routers lazily; this yields effective routes.
    return list(iter_route_contexts(application.routes))


def _api_routes(application: FastAPI) -> list[RouteContext]:
    return [r for r in _served(application) if isinstance(r.original_route, APIRoute)]


def _legacy_requests() -> list[tuple[str, str]]:
    """Every (method, concrete path) the legacy prototype would serve."""
    legacy = create_app(include_legacy=True)
    requests = []
    for route in _api_routes(legacy):
        if (route.path or "").startswith(API_PREFIX):
            continue
        path = re.sub(r"\{[^}]+\}", str(uuid.uuid4()), route.path or "")
        for method in sorted((route.methods or set()) - {"HEAD", "OPTIONS"}):
            requests.append((method, path))
    return requests


def test_default_app_mounts_only_the_beta_namespace() -> None:
    assert not settings.LEGACY_API_ENABLED  # the default for this test run
    paths = {route.path or "" for route in _api_routes(app)}
    assert paths and all(path.startswith(f"{API_PREFIX}/") for path in paths), paths
    other = {route.path or "" for route in _served(app)} - paths
    assert other <= DOC_PATHS, other


def test_documented_inventory_matches_the_legacy_routes() -> None:
    # A legacy route must be classified in the boundary document; the table cannot
    # silently drift from the code.
    document = Path(__file__).resolve().parents[4] / "docs/product/api-boundary.md"
    documented = set(
        re.findall(r"^\| `([A-Z]+ /api/v1/\S*)` \|", document.read_text(), re.M)
    )
    legacy = create_app(include_legacy=True)
    defined = {
        f"{method} {route.path}"
        for route in _api_routes(legacy)
        if not (route.path or "").startswith(API_PREFIX)
        for method in (route.methods or set()) - {"HEAD", "OPTIONS"}
    }
    assert documented == defined, (documented - defined, defined - documented)


def test_every_legacy_endpoint_is_absent_from_the_default_app() -> None:
    legacy_app = create_app(include_legacy=True)
    with TestClient(legacy_app) as legacy_client:
        superuser = get_superuser_token_headers(legacy_client)
    with TestClient(app) as client:
        for method, path in _legacy_requests():
            for headers in ({}, superuser):
                response = client.request(method, path, headers=headers)
                assert response.status_code == 404, (method, path, response.text)


def test_default_app_sends_no_cors_grants() -> None:
    assert all(m.cls is not CORSMiddleware for m in app.user_middleware)  # type: ignore[comparison-overlap]
    with TestClient(app) as client:
        response = client.options(
            f"{API_PREFIX}/auth/session",
            headers={
                "origin": "https://evil.example",
                "access-control-request-method": "GET",
            },
        )
    assert "access-control-allow-origin" not in response.headers


def test_docs_are_not_served_outside_local(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(settings, "ENVIRONMENT", "production")
    deployed = create_app(include_legacy=False)
    paths = {route.path or "" for route in _served(deployed)}
    assert not paths & DOC_PATHS
    assert all(path.startswith(f"{API_PREFIX}/") for path in paths), paths


@pytest.mark.parametrize("environment", ["staging", "production"])
def test_settings_refuse_legacy_api_outside_local(
    environment: Literal["staging", "production"],
) -> None:
    with pytest.raises(ValidationError, match="LEGACY_API_ENABLED"):
        Settings(
            _env_file=None,  # type: ignore[call-arg]
            ENVIRONMENT=environment,
            LEGACY_API_ENABLED=True,
            SECRET_KEY="s" * 32,
            PROJECT_NAME="boundary",
            POSTGRES_SERVER="localhost",
            POSTGRES_USER="u",
            POSTGRES_PASSWORD="p" * 16,
            FIRST_SUPERUSER="admin@example.com",
            FIRST_SUPERUSER_PASSWORD="f" * 16,
            SKYDIVER_WEB_PROXY_KEY="k" * 32,
        )
