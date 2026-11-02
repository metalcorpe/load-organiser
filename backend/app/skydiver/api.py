"""HTTP adapter for the skydiver beta API namespace."""

from fastapi import APIRouter, Response, status

from app.skydiver.health import (
    Clock,
    DatabaseProbe,
    HealthStatus,
    check_health,
    utc_now,
)

API_PREFIX = "/api/skydiver/v1"
NO_STORE = "no-store"


def create_router(
    *, database_probe: DatabaseProbe, clock: Clock = utc_now
) -> APIRouter:
    """Build the beta router with its ports supplied by the composition root."""
    router = APIRouter(prefix=API_PREFIX, tags=["skydiver"])

    @router.get(
        "/health",
        operation_id="getHealth",
        summary="Beta API and database availability",
        response_model=HealthStatus,
        responses={
            status.HTTP_503_SERVICE_UNAVAILABLE: {
                "model": HealthStatus,
                "description": "The API is running but cannot reach its database.",
            }
        },
    )
    def read_health(response: Response) -> HealthStatus:
        result = check_health(database_probe=database_probe, clock=clock)
        response.headers["Cache-Control"] = NO_STORE
        if result.status != "ok":
            response.status_code = status.HTTP_503_SERVICE_UNAVAILABLE
        return result

    return router
