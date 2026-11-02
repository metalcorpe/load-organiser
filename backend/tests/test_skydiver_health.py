"""Contract tests for the #144 beta health endpoint. No database or settings needed."""

import json
import subprocess
import sys
from datetime import UTC, datetime
from pathlib import Path

from fastapi import FastAPI
from fastapi.testclient import TestClient
from sqlalchemy import create_engine

from app.skydiver.adapters import sql_database_probe
from app.skydiver.api import API_PREFIX, create_router
from app.skydiver.openapi import build_openapi

FIXED = datetime(2026, 11, 2, 12, 0, tzinfo=UTC)
BACKEND_DIR = Path(__file__).resolve().parents[1]


def client_with(probe_result: bool) -> TestClient:
    app = FastAPI()
    app.include_router(
        create_router(database_probe=lambda: probe_result, clock=lambda: FIXED)
    )
    return TestClient(app)


def test_health_ok_is_uncached() -> None:
    response = client_with(True).get(f"{API_PREFIX}/health")
    assert response.status_code == 200
    assert response.headers["cache-control"] == "no-store"
    assert response.json() == {
        "status": "ok",
        "database": "ok",
        "checked_at": "2026-11-02T12:00:00Z",
    }


def test_health_reports_database_unavailable_as_503() -> None:
    response = client_with(False).get(f"{API_PREFIX}/health")
    assert response.status_code == 503
    assert response.headers["cache-control"] == "no-store"
    assert response.json()["status"] == "unavailable"
    assert response.json()["database"] == "unavailable"


def test_health_rejects_unsafe_methods() -> None:
    assert client_with(True).post(f"{API_PREFIX}/health").status_code == 405


def test_sql_probe_against_reachable_and_unreachable_engines() -> None:
    assert sql_database_probe(create_engine("sqlite://"))() is True
    # Port 9 (discard) is closed locally; connection is refused without a server.
    refused = create_engine(
        "postgresql+psycopg://probe:probe@127.0.0.1:9/probe",
        connect_args={"connect_timeout": 2},
    )
    assert sql_database_probe(refused)() is False


def test_exported_openapi_contains_only_beta_paths() -> None:
    document = build_openapi()
    assert list(document["paths"]) == [f"{API_PREFIX}/health"]
    operation = document["paths"][f"{API_PREFIX}/health"]["get"]
    assert operation["operationId"] == "getHealth"
    assert "security" not in operation
    assert set(operation["responses"]) >= {"200", "503"}


def test_beta_modules_do_not_load_application_settings(tmp_path: Path) -> None:
    # Run from an empty directory so a stray "../.env" can never be read.
    code = (
        "import sys, app.skydiver.openapi, app.skydiver.api, app.skydiver.health;"
        "bad=[m for m in ('app.core.config','app.core.db','app.models') if m in sys.modules];"
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


def test_committed_web_contract_matches_backend() -> None:
    committed = BACKEND_DIR.parent / "web" / "contracts" / "skydiver-v1.openapi.json"
    assert json.loads(committed.read_text()) == build_openapi()
