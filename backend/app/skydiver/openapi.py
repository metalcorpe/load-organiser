"""Export the public-safe beta OpenAPI document (beta router only).

Usage (from backend/):  uv run python -m app.skydiver.openapi > ../web/contracts/skydiver-v1.openapi.json

Builds a standalone FastAPI app containing only the skydiver router, so legacy
operations and application settings are never part of the generated contract.
"""

import json
import sys
from typing import Any

from fastapi import FastAPI

from app.skydiver.access.http import AccessDependencies
from app.skydiver.api import create_router
from app.skydiver.directory.api import create_router as create_directory_router
from app.skydiver.directory.service import DirectoryService
from app.skydiver.gear.api import create_router as create_gear_router
from app.skydiver.gear.service import GearService
from app.skydiver.history.api import create_router as create_history_router
from app.skydiver.history.service import HistoryService
from app.skydiver.identity.api import create_router as create_identity_router
from app.skydiver.identity.service import IdentityService
from app.skydiver.logbook.api import create_router as create_logbook_router
from app.skydiver.logbook.service import LogbookService
from app.skydiver.moderation.api import create_router as create_moderation_router
from app.skydiver.moderation.service import SubmissionService
from app.skydiver.opportunities.api import (
    create_router as create_opportunity_router,
)
from app.skydiver.opportunities.service import OpportunityService
from app.skydiver.saves.api import create_router as create_saves_router
from app.skydiver.saves.service import SavesService


def _no_service() -> IdentityService:
    raise RuntimeError("contract export only")


def _no_directory() -> DirectoryService:
    raise RuntimeError("contract export only")


def _no_opportunities() -> OpportunityService:
    raise RuntimeError("contract export only")


def _no_gear() -> GearService:
    raise RuntimeError("contract export only")


def _no_logbook() -> LogbookService:
    raise RuntimeError("contract export only")


def _no_history() -> HistoryService:
    raise RuntimeError("contract export only")


def _no_submissions() -> SubmissionService:
    raise RuntimeError("contract export only")


def _no_saves() -> SavesService:
    raise RuntimeError("contract export only")


def build_openapi() -> dict[str, Any]:
    app = FastAPI(title="Load Organiser skydiver beta API", version="1")
    app.include_router(create_router(database_probe=lambda: True))
    app.include_router(
        create_identity_router(service=_no_service, client_ip=lambda _: "")
    )
    app.include_router(
        create_directory_router(
            service=_no_directory, access=AccessDependencies(_no_service)
        )
    )
    app.include_router(
        create_opportunity_router(
            service=_no_opportunities, access=AccessDependencies(_no_service)
        )
    )
    app.include_router(
        create_saves_router(service=_no_saves, access=AccessDependencies(_no_service))
    )
    app.include_router(
        create_gear_router(service=_no_gear, access=AccessDependencies(_no_service))
    )
    app.include_router(
        create_logbook_router(
            service=_no_logbook, access=AccessDependencies(_no_service)
        )
    )
    app.include_router(
        create_history_router(
            service=_no_history, access=AccessDependencies(_no_service)
        )
    )
    app.include_router(
        create_moderation_router(
            service=_no_submissions, access=AccessDependencies(_no_service)
        )
    )
    return app.openapi()


if __name__ == "__main__":
    json.dump(build_openapi(), sys.stdout, indent=2, sort_keys=True)
    sys.stdout.write("\n")
