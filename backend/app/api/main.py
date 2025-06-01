from fastapi import APIRouter

from app.api.routes import items, login, private, users, utils, aircraft, instructors, loads, jumps, weather, analytics
from app.core.config import settings

api_router = APIRouter()
api_router.include_router(login.router)
api_router.include_router(users.router)
api_router.include_router(utils.router)
api_router.include_router(items.router)

# Skydiving organizer routes
api_router.include_router(aircraft.router, prefix="/aircraft", tags=["aircraft"])
api_router.include_router(instructors.router, prefix="/instructors", tags=["instructors"])
api_router.include_router(loads.router, prefix="/loads", tags=["loads"])
api_router.include_router(jumps.router, prefix="/jumps", tags=["jumps"])
api_router.include_router(weather.router, prefix="/weather", tags=["weather"])
api_router.include_router(analytics.router, prefix="/analytics", tags=["analytics"])


if settings.ENVIRONMENT == "local":
    api_router.include_router(private.router)
