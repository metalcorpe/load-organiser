"""HTTP adapter for private saves and visit plans (#150). Owner-only.

- GET    /saved                      the viewer's bookmarks with current listing state
- GET    /saved/{opportunity_id}     whether the viewer saved it (404 when not)
- PUT    /saved/{opportunity_id}     idempotent save (201 new, 200 existing)
- DELETE /saved/{opportunity_id}     idempotent removal
- GET/POST /plans, PATCH/DELETE /plans/{id}

Reads need a session; writes need a confirmed email. Nothing here is visible to
other people, organizers or reviewers, and no response asserts registration.
"""

import uuid
from collections.abc import Callable
from datetime import date, datetime
from typing import Annotated, Any

from fastapi import APIRouter, Depends, Response, status
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from app.skydiver.access.http import AccessDependencies
from app.skydiver.access.policy import Actor
from app.skydiver.directory.api import VenueRefOut
from app.skydiver.directory.policy import DirectoryRuleError, VenueStatus
from app.skydiver.opportunities.api import OpportunityOut, opportunity_out
from app.skydiver.opportunities.service import Opportunity, Resolved
from app.skydiver.saves.service import (
    LimitReached,
    NotFound,
    Plan,
    Saved,
    SavedRow,
    SavesService,
)

PREFIX = "/api/skydiver/v1"
NO_STORE = {"cache-control": "no-store"}

Title = Annotated[str, Field(min_length=1, max_length=400)]
Note = Annotated[str, Field(max_length=2000)]


class Problem(BaseModel):
    detail: str


class SavedOut(BaseModel):
    """A private bookmark. Saving is not registration, attendance or interest."""

    opportunity_id: uuid.UUID = Field(description="The ID that was saved.")
    title: str = Field(description="The listing title when it was saved.")
    saved_at: datetime
    opportunity: OpportunityOut | None = Field(
        description="Current public listing; null once it is no longer public."
    )


class SavedStateOut(BaseModel):
    opportunity_id: uuid.UUID
    saved_at: datetime


class PlaceRefOut(BaseModel):
    id: uuid.UUID
    name: str
    country: str


class PlanOut(BaseModel):
    """A private dated plan. Never shared, never a jump or presence record."""

    id: uuid.UUID
    title: str
    starts_on: date
    ends_on: date
    note: str | None
    opportunity_id: uuid.UUID | None = Field(
        description="Linked listing as stored; see `opportunity` for its state."
    )
    opportunity: OpportunityOut | None = Field(
        description="Current public listing; null when unlinked or no longer public."
    )
    venue_id: uuid.UUID | None
    venue: VenueRefOut | None
    place_id: uuid.UUID | None
    place: PlaceRefOut | None
    updated_at: datetime


class PlanIn(BaseModel):
    title: Title
    starts_on: date
    ends_on: date
    note: Note | None = None
    opportunity_id: uuid.UUID | None = None
    venue_id: uuid.UUID | None = None
    place_id: uuid.UUID | None = None


class PlanUpdateIn(BaseModel):
    title: Title | None = None
    starts_on: date | None = None
    ends_on: date | None = None
    note: Note | None = None
    opportunity_id: uuid.UUID | None = None
    venue_id: uuid.UUID | None = None
    place_id: uuid.UUID | None = None


_ERRORS: dict[int | str, dict[str, Any]] = {
    code: {"model": Problem} for code in (401, 403, 404, 409, 422)
}


def _current(found: Resolved[Opportunity] | None) -> OpportunityOut | None:
    return opportunity_out(found.value) if found else None


def _saved(item: Saved) -> SavedOut:
    return SavedOut(
        opportunity_id=item.opportunity_id,
        title=item.title,
        saved_at=item.saved_at,
        opportunity=_current(item.current),
    )


def _state(row: SavedRow) -> SavedStateOut:
    return SavedStateOut(opportunity_id=row.opportunity_id, saved_at=row.saved_at)


def _plan(plan: Plan) -> PlanOut:
    row, venue, place = plan.row, plan.venue, plan.place
    return PlanOut(
        id=row.id,
        title=row.title,
        starts_on=row.starts_on,
        ends_on=row.ends_on,
        note=row.note,
        opportunity_id=row.opportunity_id,
        opportunity=_current(plan.opportunity),
        venue_id=row.venue_id,
        venue=VenueRefOut(
            id=venue.id,
            name=venue.name,
            country=venue.country,
            status="closed" if venue.status is VenueStatus.CLOSED else "listed",
        )
        if venue
        else None,
        place_id=row.place_id,
        place=PlaceRefOut(id=place.id, name=place.name, country=place.country)
        if place
        else None,
        updated_at=row.updated_at,
    )


def _problem(error: Exception) -> JSONResponse:
    if isinstance(error, NotFound):
        code, detail = status.HTTP_404_NOT_FOUND, "not_found"
    elif isinstance(error, LimitReached):
        code, detail = status.HTTP_409_CONFLICT, error.code
    elif isinstance(error, DirectoryRuleError):
        code, detail = status.HTTP_422_UNPROCESSABLE_CONTENT, error.code
    else:
        raise error
    return JSONResponse({"detail": detail}, status_code=code, headers=NO_STORE)


def create_router(
    *,
    service: Callable[[], SavesService],
    access: AccessDependencies,
) -> APIRouter:
    router = APIRouter(prefix=PREFIX, tags=["skydiver-saves"], responses=_ERRORS)

    def no_store(response: Response) -> None:
        response.headers["cache-control"] = "no-store"

    deps = [Depends(no_store)]
    Reader = Annotated[Actor, Depends(access.actor)]
    Writer = Annotated[Actor, Depends(access.verified_actor)]
    Errors = (NotFound, LimitReached, DirectoryRuleError)

    # -- saved opportunities --------------------------------------------------------

    @router.get(
        "/saved",
        operation_id="listSaved",
        response_model=list[SavedOut],
        dependencies=deps,
    )
    def list_saved(actor: Reader) -> list[SavedOut]:
        return [_saved(item) for item in service().list_saved(actor)]

    @router.get(
        "/saved/{opportunity_id}",
        operation_id="getSaved",
        response_model=SavedStateOut,
        dependencies=deps,
    )
    def get_saved(
        opportunity_id: uuid.UUID, actor: Reader
    ) -> SavedStateOut | JSONResponse:
        try:
            return _state(service().saved(actor, opportunity_id))
        except Errors as error:
            return _problem(error)

    @router.put(
        "/saved/{opportunity_id}",
        operation_id="saveOpportunity",
        response_model=SavedStateOut,
        responses={201: {"model": SavedStateOut}},
        dependencies=deps,
    )
    def save_opportunity(
        opportunity_id: uuid.UUID, actor: Writer, response: Response
    ) -> SavedStateOut | JSONResponse:
        try:
            row, created = service().save(actor, opportunity_id)
        except Errors as error:
            return _problem(error)
        response.status_code = 201 if created else 200
        return _state(row)

    @router.delete(
        "/saved/{opportunity_id}",
        operation_id="unsaveOpportunity",
        status_code=status.HTTP_204_NO_CONTENT,
        dependencies=deps,
    )
    def unsave_opportunity(opportunity_id: uuid.UUID, actor: Writer) -> Response:
        service().unsave(actor, opportunity_id)
        return Response(status_code=status.HTTP_204_NO_CONTENT, headers=NO_STORE)

    # -- visit plans --------------------------------------------------------------

    @router.get(
        "/plans",
        operation_id="listPlans",
        response_model=list[PlanOut],
        dependencies=deps,
    )
    def list_plans(actor: Reader) -> list[PlanOut]:
        return [_plan(plan) for plan in service().list_plans(actor)]

    @router.post(
        "/plans",
        operation_id="createPlan",
        response_model=PlanOut,
        status_code=status.HTTP_201_CREATED,
        dependencies=deps,
    )
    def create_plan(body: PlanIn, actor: Writer) -> PlanOut | JSONResponse:
        try:
            plan = service().create_plan(actor, body.model_dump())
        except Errors as error:
            return _problem(error)
        return _plan(plan)

    @router.patch(
        "/plans/{plan_id}",
        operation_id="updatePlan",
        response_model=PlanOut,
        dependencies=deps,
    )
    def update_plan(
        plan_id: uuid.UUID, body: PlanUpdateIn, actor: Writer
    ) -> PlanOut | JSONResponse:
        try:
            plan = service().update_plan(
                actor, plan_id, body.model_dump(exclude_unset=True)
            )
        except Errors as error:
            return _problem(error)
        return _plan(plan)

    @router.delete(
        "/plans/{plan_id}",
        operation_id="deletePlan",
        status_code=status.HTTP_204_NO_CONTENT,
        dependencies=deps,
    )
    def delete_plan(plan_id: uuid.UUID, actor: Writer) -> Response:
        try:
            service().delete_plan(actor, plan_id)
        except Errors as error:
            return _problem(error)
        return Response(status_code=status.HTTP_204_NO_CONTENT, headers=NO_STORE)

    return router
