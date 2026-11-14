"""HTTP adapter for the directory (#148). Called only by the SvelteKit server.

- Public:   GET /venues, GET /venues/{id}        (listed and closed venues only)
            GET /venue-points                     (the same venues, with coordinates)
- Reviewer: /directory/venues...                 (role `reviewer`; maintenance)
- Owner:    /places...                           (private provisional places)
"""

import uuid
from collections.abc import Callable
from datetime import date, datetime
from typing import Annotated, Any, Literal

from fastapi import APIRouter, Depends, Query, Response, status
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from app.skydiver.access.http import AccessDependencies
from app.skydiver.access.policy import Actor, Role
from app.skydiver.directory.policy import DirectoryRuleError, VenueStatus
from app.skydiver.directory.service import (
    DirectoryService,
    EditConflict,
    LimitReached,
    NotFound,
    Place,
    Venue,
    VenueChanges,
    VenueEvent,
    VenueInput,
)

PREFIX = "/api/skydiver/v1"
NO_STORE = {"cache-control": "no-store"}

# Raw input bounds; the policy applies the exact limits after normalisation.
Name = Annotated[str, Field(min_length=1, max_length=200)]
Country = Annotated[str, Field(min_length=2, max_length=2)]
Url = Annotated[str, Field(max_length=2048)]
Note = Annotated[str, Field(max_length=400)]
ExpectedVersion = Annotated[
    int | None,
    Field(
        ge=1,
        description=(
            "The `version` this change is based on. A different current version "
            "answers 409 `edit_conflict`; omit only for last-writer-wins."
        ),
    ),
]


class Problem(BaseModel):
    detail: str


class AliasOut(BaseModel):
    name: str
    kind: Literal["alternate", "former", "merged"]


class OperatorOut(BaseModel):
    """Who runs the dropzone as its source states it. Not a claim or endorsement."""

    name: str
    url: str | None


class OperatorIn(BaseModel):
    name: Name
    url: Url | None = None


Detail = Annotated[str, Field(max_length=240)]
Operators = Annotated[
    list[OperatorIn],
    Field(max_length=8, description="As the source states them; at most 4 are kept."),
]


class VenueOut(BaseModel):
    """Public venue: source-backed identity only. No operator or endorsement data."""

    id: uuid.UUID
    name: str
    country: str = Field(description="ISO 3166-1 alpha-2 code.")
    locality: str | None
    latitude: float | None
    longitude: float | None
    status: Literal["listed", "closed"]
    aliases: list[AliasOut]
    source_url: str
    source_note: str | None
    checked_on: date
    operators: list[OperatorOut] = Field(
        description="Who runs it, as the source states; not a claim or endorsement."
    )
    season: str | None = Field(description="As the source states it.")
    aircraft: str | None = Field(description="As the source states it.")


class VenuePageOut(BaseModel):
    items: list[VenueOut]
    next_cursor: str | None


class VenuePointOut(BaseModel):
    """A public venue as a map point: the list's venues that have coordinates."""

    id: uuid.UUID
    name: str
    locality: str | None
    country: str = Field(description="ISO 3166-1 alpha-2 code.")
    lat: float = Field(description="WGS84 latitude, decimal degrees.")
    lon: float = Field(description="WGS84 longitude, decimal degrees.")
    closed: bool


class VenuePointPageOut(BaseModel):
    items: list[VenuePointOut]
    next_cursor: str | None


class ReviewVenueItemOut(BaseModel):
    """A row in the maintenance queue (any status)."""

    id: uuid.UUID
    name: str
    country: str
    locality: str | None
    status: Literal["draft", "listed", "closed", "merged"]
    checked_on: date | None
    version: int
    updated_at: datetime


class ReviewVenuePageOut(BaseModel):
    items: list[ReviewVenueItemOut]
    next_cursor: str | None


class VenueDetailOut(BaseModel):
    venue: VenueOut
    replaced_id: uuid.UUID | None = Field(
        description="Set when the requested venue was merged into `venue`."
    )


class VenueRefOut(BaseModel):
    id: uuid.UUID
    name: str
    country: str
    status: Literal["listed", "closed"]


class PlaceOut(BaseModel):
    """A private provisional place. Visible to its owner only."""

    id: uuid.UUID
    name: str
    country: str
    venue: VenueRefOut | None
    updated_at: datetime


class PlaceCreateIn(BaseModel):
    name: Name
    country: Country
    venue_id: uuid.UUID | None = None


class PlaceUpdateIn(BaseModel):
    name: Name | None = None
    country: Country | None = None
    venue_id: uuid.UUID | None = None


class VenueCreateIn(BaseModel):
    name: Name
    country: Country
    locality: Name | None = None
    latitude: float | None = None
    longitude: float | None = None
    source_url: Url | None = None
    source_note: Note | None = None
    checked_on: date | None = None
    operators: Operators = []
    season: Detail | None = None
    aircraft: Detail | None = None
    listed: bool = Field(
        default=True, description="False creates a draft that is not public."
    )


class VenueUpdateIn(BaseModel):
    name: Name | None = None
    country: Country | None = None
    locality: Name | None = None
    latitude: float | None = None
    longitude: float | None = None
    source_url: Url | None = None
    source_note: Note | None = None
    checked_on: date | None = None
    operators: Operators | None = None
    season: Detail | None = None
    aircraft: Detail | None = None
    version: ExpectedVersion = None


class AliasIn(BaseModel):
    name: Name
    version: ExpectedVersion = None


class StatusIn(BaseModel):
    status: Literal["draft", "listed", "closed"]
    version: ExpectedVersion = None


class MergeIn(BaseModel):
    into: uuid.UUID = Field(description="The venue that remains.")
    version: ExpectedVersion = None  # of the merged (source) venue


class EventOut(BaseModel):
    kind: str
    detail: dict[str, Any]
    created_at: datetime


class ReviewerVenueOut(BaseModel):
    id: uuid.UUID
    name: str
    country: str
    locality: str | None
    latitude: float | None
    longitude: float | None
    status: Literal["draft", "listed", "closed", "merged"]
    merged_into_id: uuid.UUID | None
    aliases: list[AliasOut]
    source_url: str | None
    source_note: str | None
    checked_on: date | None
    operators: list[OperatorOut]
    season: str | None
    aircraft: str | None
    updated_at: datetime
    version: int
    events: list[EventOut]


_ERRORS: dict[int | str, dict[str, Any]] = {
    code: {"model": Problem} for code in (401, 403, 404, 409, 422)
}


def _public(venue: Venue) -> VenueOut:
    assert venue.source_url is not None and venue.checked_on is not None
    return VenueOut(
        id=venue.id,
        name=venue.name,
        country=venue.country,
        locality=venue.locality,
        latitude=venue.latitude,
        longitude=venue.longitude,
        status="closed" if venue.status is VenueStatus.CLOSED else "listed",
        aliases=[AliasOut(name=a.name, kind=a.kind.value) for a in venue.aliases],
        source_url=venue.source_url,
        source_note=venue.source_note,
        checked_on=venue.checked_on,
        operators=_operators(venue),
        season=venue.season,
        aircraft=venue.aircraft,
    )


def _operators(venue: Venue) -> list[OperatorOut]:
    return [OperatorOut(name=o.name, url=o.url) for o in venue.operators]


def _place(place: Place) -> PlaceOut:
    venue = place.venue
    return PlaceOut(
        id=place.id,
        name=place.name,
        country=place.country,
        venue=VenueRefOut(
            id=venue.id,
            name=venue.name,
            country=venue.country,
            status="closed" if venue.status is VenueStatus.CLOSED else "listed",
        )
        if venue
        else None,
        updated_at=place.updated_at,
    )


def _reviewer(venue: Venue, events: list[VenueEvent]) -> ReviewerVenueOut:
    return ReviewerVenueOut(
        id=venue.id,
        name=venue.name,
        country=venue.country,
        locality=venue.locality,
        latitude=venue.latitude,
        longitude=venue.longitude,
        status=venue.status.value,
        merged_into_id=venue.merged_into_id,
        aliases=[AliasOut(name=a.name, kind=a.kind.value) for a in venue.aliases],
        source_url=venue.source_url,
        source_note=venue.source_note,
        checked_on=venue.checked_on,
        operators=_operators(venue),
        season=venue.season,
        aircraft=venue.aircraft,
        updated_at=venue.updated_at,
        version=venue.version,
        events=[
            EventOut(kind=e.kind, detail=e.detail, created_at=e.created_at)
            for e in events
        ],
    )


def _problem(error: Exception) -> JSONResponse:
    if isinstance(error, NotFound):
        code, detail = status.HTTP_404_NOT_FOUND, "not_found"
    elif isinstance(error, LimitReached | EditConflict):
        code, detail = status.HTTP_409_CONFLICT, error.code
    elif isinstance(error, DirectoryRuleError):
        code, detail = status.HTTP_422_UNPROCESSABLE_CONTENT, error.code
    else:
        raise error
    return JSONResponse({"detail": detail}, status_code=code, headers=NO_STORE)


def create_router(
    *,
    service: Callable[[], DirectoryService],
    access: AccessDependencies,
) -> APIRouter:
    router = APIRouter(prefix=PREFIX, tags=["skydiver-directory"], responses=_ERRORS)

    def no_store(response: Response) -> None:
        response.headers["cache-control"] = "no-store"

    deps = [Depends(no_store)]
    Reader = Annotated[Actor, Depends(access.actor)]
    Writer = Annotated[Actor, Depends(access.verified_actor)]
    Reviewer = Annotated[Actor, Depends(access.role(Role.REVIEWER))]
    Errors = (NotFound, LimitReached, EditConflict, DirectoryRuleError)

    # -- public -------------------------------------------------------------------

    @router.get(
        "/venues",
        operation_id="searchVenues",
        response_model=VenuePageOut,
        dependencies=deps,
    )
    def search_venues(
        q: Annotated[str | None, Query(max_length=200)] = None,
        country: Annotated[str | None, Query(min_length=2, max_length=2)] = None,
        cursor: Annotated[str | None, Query(max_length=512)] = None,
        limit: Annotated[int | None, Query(ge=1, le=50)] = None,
    ) -> VenuePageOut | JSONResponse:
        try:
            page = service().search(
                query=q, country=country, cursor=cursor, limit=limit
            )
        except Errors as error:
            return _problem(error)
        return VenuePageOut(
            items=[_public(v) for v in page.items], next_cursor=page.next_cursor
        )

    @router.get(
        "/venue-points",
        operation_id="listVenuePoints",
        response_model=VenuePointPageOut,
        dependencies=deps,
        description=(
            "Map points for the venues `GET /venues` finds with the same `q` and "
            "`country`, without venues that have no coordinates. Same order and "
            "cursor form; pages of up to 1000."
        ),
    )
    def list_venue_points(
        q: Annotated[str | None, Query(max_length=200)] = None,
        country: Annotated[str | None, Query(min_length=2, max_length=2)] = None,
        cursor: Annotated[str | None, Query(max_length=512)] = None,
        limit: Annotated[int | None, Query(ge=1, le=1000)] = None,
    ) -> VenuePointPageOut | JSONResponse:
        try:
            page = service().map_points(
                query=q, country=country, cursor=cursor, limit=limit
            )
        except Errors as error:
            return _problem(error)
        return VenuePointPageOut(
            items=[
                VenuePointOut(
                    id=p.id,
                    name=p.name,
                    locality=p.locality,
                    country=p.country,
                    lat=p.latitude,
                    lon=p.longitude,
                    closed=p.closed,
                )
                for p in page.items
            ],
            next_cursor=page.next_cursor,
        )

    @router.get(
        "/venues/{venue_id}",
        operation_id="getVenue",
        response_model=VenueDetailOut,
        dependencies=deps,
    )
    def get_venue(venue_id: uuid.UUID) -> VenueDetailOut | JSONResponse:
        try:
            resolved = service().public_venue(venue_id)
        except Errors as error:
            return _problem(error)
        return VenueDetailOut(
            venue=_public(resolved.venue), replaced_id=resolved.replaced_id
        )

    # -- owner: provisional places ------------------------------------------------

    @router.get(
        "/places",
        operation_id="listPlaces",
        response_model=list[PlaceOut],
        dependencies=deps,
    )
    def list_places(actor: Reader) -> list[PlaceOut]:
        return [_place(p) for p in service().list_places(actor)]

    @router.post(
        "/places",
        operation_id="createPlace",
        status_code=status.HTTP_201_CREATED,
        response_model=PlaceOut,
        dependencies=deps,
    )
    def create_place(body: PlaceCreateIn, actor: Writer) -> PlaceOut | JSONResponse:
        try:
            place = service().create_place(
                actor, name=body.name, country=body.country, venue_id=body.venue_id
            )
        except Errors as error:
            return _problem(error)
        return _place(place)

    @router.patch(
        "/places/{place_id}",
        operation_id="updatePlace",
        response_model=PlaceOut,
        dependencies=deps,
    )
    def update_place(
        place_id: uuid.UUID, body: PlaceUpdateIn, actor: Writer
    ) -> PlaceOut | JSONResponse:
        try:
            place = service().update_place(
                actor, place_id, body.model_dump(exclude_unset=True)
            )
        except Errors as error:
            return _problem(error)
        return _place(place)

    @router.delete(
        "/places/{place_id}",
        operation_id="deletePlace",
        status_code=status.HTTP_204_NO_CONTENT,
        dependencies=deps,
    )
    def delete_place(place_id: uuid.UUID, actor: Writer) -> Response:
        try:
            service().delete_place(actor, place_id)
        except Errors as error:
            return _problem(error)
        return Response(status_code=status.HTTP_204_NO_CONTENT, headers=NO_STORE)

    # -- reviewer -----------------------------------------------------------------

    def reviewed(actor: Actor, venue: Venue) -> ReviewerVenueOut:
        _, events = service().reviewer_venue(actor, venue.id)
        return _reviewer(venue, events)

    @router.get(
        "/directory/venues",
        operation_id="listReviewVenues",
        response_model=ReviewVenuePageOut,
        dependencies=deps,
    )
    def list_review_venues(
        _actor: Reviewer,
        q: Annotated[str | None, Query(max_length=200)] = None,
        status: Annotated[str | None, Query(max_length=16)] = None,
        due: Annotated[
            bool,
            Query(description="Only listed venues whose source check is overdue."),
        ] = False,
        cursor: Annotated[str | None, Query(max_length=512)] = None,
        limit: Annotated[int | None, Query(ge=1, le=50)] = None,
    ) -> ReviewVenuePageOut | JSONResponse:
        try:
            page = service().review_venues(
                query=q, status=status, due=due, cursor=cursor, limit=limit
            )
        except Errors as error:
            return _problem(error)
        return ReviewVenuePageOut(
            items=[
                ReviewVenueItemOut(
                    id=v.id,
                    name=v.name,
                    country=v.country,
                    locality=v.locality,
                    status=v.status.value,
                    checked_on=v.checked_on,
                    version=v.version,
                    updated_at=v.updated_at,
                )
                for v in page.items
            ],
            next_cursor=page.next_cursor,
        )

    @router.get(
        "/directory/venues/{venue_id}",
        operation_id="reviewVenue",
        response_model=ReviewerVenueOut,
        dependencies=deps,
    )
    def review_venue(
        venue_id: uuid.UUID, actor: Reviewer
    ) -> ReviewerVenueOut | JSONResponse:
        try:
            venue, events = service().reviewer_venue(actor, venue_id)
        except Errors as error:
            return _problem(error)
        return _reviewer(venue, events)

    @router.post(
        "/directory/venues",
        operation_id="createVenue",
        status_code=status.HTTP_201_CREATED,
        response_model=ReviewerVenueOut,
        dependencies=deps,
    )
    def create_venue(
        body: VenueCreateIn, actor: Reviewer
    ) -> ReviewerVenueOut | JSONResponse:
        try:
            venue = service().create_venue(actor, VenueInput(**body.model_dump()))
        except Errors as error:
            return _problem(error)
        return reviewed(actor, venue)

    @router.patch(
        "/directory/venues/{venue_id}",
        operation_id="updateVenue",
        response_model=ReviewerVenueOut,
        dependencies=deps,
    )
    def update_venue(
        venue_id: uuid.UUID, body: VenueUpdateIn, actor: Reviewer
    ) -> ReviewerVenueOut | JSONResponse:
        try:
            fields = body.model_dump(exclude_unset=True, exclude={"version"})
            venue = service().update_venue(
                actor, venue_id, VenueChanges(fields), expected_version=body.version
            )
        except Errors as error:
            return _problem(error)
        return reviewed(actor, venue)

    @router.post(
        "/directory/venues/{venue_id}/aliases",
        operation_id="addVenueAlias",
        response_model=ReviewerVenueOut,
        dependencies=deps,
    )
    def add_alias(
        venue_id: uuid.UUID, body: AliasIn, actor: Reviewer
    ) -> ReviewerVenueOut | JSONResponse:
        try:
            venue = service().add_alias(
                actor, venue_id, body.name, expected_version=body.version
            )
        except Errors as error:
            return _problem(error)
        return reviewed(actor, venue)

    @router.post(
        "/directory/venues/{venue_id}/status",
        operation_id="setVenueStatus",
        response_model=ReviewerVenueOut,
        dependencies=deps,
    )
    def set_status(
        venue_id: uuid.UUID, body: StatusIn, actor: Reviewer
    ) -> ReviewerVenueOut | JSONResponse:
        try:
            venue = service().set_status(
                actor, venue_id, VenueStatus(body.status), expected_version=body.version
            )
        except Errors as error:
            return _problem(error)
        return reviewed(actor, venue)

    @router.post(
        "/directory/venues/{venue_id}/merge",
        operation_id="mergeVenue",
        response_model=ReviewerVenueOut,
        dependencies=deps,
    )
    def merge_venue(
        venue_id: uuid.UUID, body: MergeIn, actor: Reviewer
    ) -> ReviewerVenueOut | JSONResponse:
        try:
            venue = service().merge(
                actor, venue_id, body.into, expected_version=body.version
            )
        except Errors as error:
            return _problem(error)
        return reviewed(actor, venue)

    return router
