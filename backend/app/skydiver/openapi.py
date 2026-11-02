"""Export the public-safe beta OpenAPI document (beta router only).

Usage (from backend/):  uv run python -m app.skydiver.openapi > ../web/contracts/skydiver-v1.openapi.json

Builds a standalone FastAPI app containing only the skydiver router, so legacy
operations and application settings are never part of the generated contract.
"""

import json
import sys
from typing import Any

from fastapi import FastAPI

from app.skydiver.api import create_router


def build_openapi() -> dict[str, Any]:
    app = FastAPI(title="Load Organiser skydiver beta API", version="1")
    app.include_router(create_router(database_probe=lambda: True))
    return app.openapi()


if __name__ == "__main__":
    json.dump(build_openapi(), sys.stdout, indent=2, sort_keys=True)
    sys.stdout.write("\n")
