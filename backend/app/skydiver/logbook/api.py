"""HTTP adapter for the private jump logbook (#153). Owner-only.

Reads need a session; writes need a confirmed email. A create carries a client key
(retry-safe; a replay after deletion answers 410 `jump_deleted`) and may be refused
with 409 `likely_duplicate` naming the earlier entry until the jumper confirms it
is a distinct jump. Edits and deletes carry the `version` they were based on
(409 `edit_conflict`). Nothing here is shared, verified or derived from a plan,
post or operator record.
"""

import uuid
from collections.abc import Callable
from datetime import date, datetime, time
from typing import Annotated, Any, Literal

from fastapi import APIRouter, Depends, Query, Response, status
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from app.skydiver.access.http import AccessDependencies
from app.skydiver.access.policy import Actor
from app.skydiver.directory.policy import DirectoryRuleError
from app.skydiver.directory.service import EditConflict
from app.skydiver.logbook.service import (
    JumpDeleted,
    JumpDetail,
    JumpView,
    KeyReused,
    LikelyDuplicate,
    LimitReached,
    LogbookService,
    NotFound,
    NumberedRef,
)

PREFIX = "/api/skydiver/v1"
NO_STORE = {"cache-control": "no-store"}

JumpTypeName = Literal[
    "unspecified", "belly", "freefly", "angle", "wingsuit", "canopy", "crw",
    "accuracy", "hop_and_pop", "tandem", "training", "other",
]  # fmt: skip
Unit = Literal["ft", "m"]
Datum = Literal["unspecified", "agl", "msl"]
Version = Annotated[int, Field(ge=1)]
Source = Literal["manual", "restored", "imported"]
_SOURCES: dict[str, Source] = {"restored": "restored", "imported": "imported"}


class Problem(BaseModel):
    detail: str


class DuplicateProblem(BaseModel):
    detail: Literal["likely_duplicate"]
    duplicate_of: uuid.UUID


class JumpFields(BaseModel):
    exit_time: time | None = Field(
        default=None, description="Local exit time as entered; needs `time_zone`."
    )
    time_zone: Annotated[str, Field(max_length=64)] | None = Field(
        default=None, description="IANA time zone of `exit_time`, e.g. Europe/Madrid."
    )
    jump_number: Annotated[int, Field(ge=1, le=1_000_000)] | None = None
    exit_altitude: Annotated[int, Field(ge=1, le=100_000)] | None = None
    deployment_altitude: Annotated[int, Field(ge=1, le=100_000)] | None = None
    altitude_unit: Unit | None = Field(
        default=None, description="Required when an altitude is given."
    )
    altitude_datum: Datum | None = None
    freefall_seconds: Annotated[int, Field(ge=0, le=3600)] | None = None
    component_ids: Annotated[list[uuid.UUID], Field(max_length=20)] | None = Field(
        default=None, description="Your own components actually used. Omit if unknown."
    )
    other_gear: Annotated[str, Field(max_length=400)] | None = Field(
        default=None, description="Borrowed, rented or unrecorded equipment."
    )
    notes: Annotated[str, Field(max_length=4000)] | None = None
    links: (
        Annotated[list[Annotated[str, Field(max_length=2100)]], Field(max_length=10)]
        | None
    ) = None


class JumpIn(JumpFields):
    client_key: uuid.UUID
    jumped_on: date = Field(description="The local calendar date of the jump.")
    venue_id: uuid.UUID | None = Field(default=None, description="A listed dropzone.")
    place_id: uuid.UUID | None = Field(
        default=None, description="One of your private places."
    )
    jump_type: JumpTypeName
    confirm_distinct: bool = Field(
        default=False,
        description="Save even though a likely duplicate exists (two real jumps).",
    )


class JumpUpdateIn(JumpFields):
    jumped_on: date | None = None
    venue_id: uuid.UUID | None = None
    place_id: uuid.UUID | None = None
    jump_type: JumpTypeName | None = None
    version: Version | None = None


class LocationOut(BaseModel):
    kind: Literal["venue", "place"]
    id: uuid.UUID
    name: str | None = Field(description="Null when a dropzone is no longer listed.")
    country: str | None
    closed: bool


class ComponentRefOut(BaseModel):
    id: uuid.UUID
    kind: str
    label: str
    archived: bool


class JumpOut(BaseModel):
    """The owner's own record. `provenance` is always self-reported."""

    id: uuid.UUID
    jumped_on: date
    location: LocationOut
    jump_type: JumpTypeName
    jump_number: int | None
    exit_time: time | None
    time_zone: str | None
    exit_altitude: int | None
    deployment_altitude: int | None
    altitude_unit: Unit | None
    altitude_datum: Datum
    freefall_seconds: int | None
    components: list[ComponentRefOut]
    other_gear: str | None
    notes: str | None
    links: list[str]
    source: Source = Field(
        description=(
            "`restored`: re-created from the owner's own export; `imported`: from"
            " the owner's own spreadsheet."
        )
    )
    provenance: Literal["self_reported"] = "self_reported"
    version: int
    created_at: datetime
    updated_at: datetime


class JumpSummaryOut(BaseModel):
    id: uuid.UUID
    jumped_on: date
    location: LocationOut
    jump_type: JumpTypeName
    jump_number: int | None
    components: list[ComponentRefOut]


class JumpPageOut(BaseModel):
    items: list[JumpSummaryOut]
    next_cursor: str | None
    recorded_total: int = Field(
        description="Detailed entries you recorded; not a lifetime total."
    )


class NumberedJumpOut(BaseModel):
    id: uuid.UUID
    jumped_on: date
    jump_number: int


class NumberGapOut(BaseModel):
    first: int = Field(description="The first missing number.")
    last: int = Field(description="The last missing number.")
    before: NumberedJumpOut
    after: NumberedJumpOut


class NumberRepeatOut(BaseModel):
    jump_number: int
    uses: int
    jumps: list[NumberedJumpOut] = Field(description="At most five of them.")


class JumpNumberingOut(BaseModel):
    """Your own numbering, to suggest the next number and note slips."""

    highest: int | None = Field(description="Null when no jump has a number.")
    gaps: list[NumberGapOut] = Field(description="The first few, lowest first.")
    gap_count: int
    repeats: list[NumberRepeatOut] = Field(description="The first few, lowest first.")
    repeat_count: int


class JumpEventOut(BaseModel):
    kind: str
    detail: dict[str, Any]
    created_at: datetime


class JumpDetailOut(BaseModel):
    jump: JumpOut
    events: list[JumpEventOut]
    same_number: list[uuid.UUID] = Field(
        description="Your other entries with this jump number (a possible mistake)."
    )


_ERRORS: dict[int | str, dict[str, Any]] = {
    code: {"model": Problem} for code in (401, 403, 404, 410, 422)
}
_ERRORS[409] = {"model": Problem | DuplicateProblem}


def _location(view: JumpView) -> LocationOut:
    loc = view.location
    return LocationOut(
        kind="venue" if loc.kind == "venue" else "place",
        id=loc.id,
        name=loc.name,
        country=loc.country,
        closed=loc.closed,
    )


def _components(view: JumpView) -> list[ComponentRefOut]:
    return [
        ComponentRefOut(id=c.id, kind=c.kind, label=c.label, archived=c.archived)
        for c in view.components
    ]


def _jump(view: JumpView) -> JumpOut:
    j = view.jump
    return JumpOut(
        id=j.id,
        jumped_on=j.jumped_on,
        location=_location(view),
        jump_type=j.jump_type.value,
        jump_number=j.jump_number,
        exit_time=j.exit_time,
        time_zone=j.time_zone,
        exit_altitude=j.exit_altitude,
        deployment_altitude=j.deployment_altitude,
        altitude_unit=j.altitude_unit.value if j.altitude_unit else None,
        altitude_datum=j.altitude_datum.value,
        freefall_seconds=j.freefall_seconds,
        components=_components(view),
        other_gear=j.other_gear,
        notes=j.notes,
        links=list(j.links),
        source=_SOURCES.get(j.source, "manual"),
        version=j.version,
        created_at=j.created_at,
        updated_at=j.updated_at,
    )


def _summary(view: JumpView) -> JumpSummaryOut:
    j = view.jump
    return JumpSummaryOut(
        id=j.id,
        jumped_on=j.jumped_on,
        location=_location(view),
        jump_type=j.jump_type.value,
        jump_number=j.jump_number,
        components=_components(view),
    )


def _detail(d: JumpDetail) -> JumpDetailOut:
    return JumpDetailOut(
        jump=_jump(d.view),
        events=[
            JumpEventOut(kind=e.kind, detail=e.detail, created_at=e.created_at)
            for e in d.events
        ],
        same_number=d.same_number,
    )


def _numbered(ref: NumberedRef) -> NumberedJumpOut:
    return NumberedJumpOut(id=ref.id, jumped_on=ref.jumped_on, jump_number=ref.number)


def _problem(error: Exception) -> JSONResponse:
    body: dict[str, Any]
    if isinstance(error, NotFound):
        code, body = status.HTTP_404_NOT_FOUND, {"detail": "not_found"}
    elif isinstance(error, LikelyDuplicate):
        code = status.HTTP_409_CONFLICT
        body = {"detail": error.code, "duplicate_of": str(error.duplicate_of)}
    elif isinstance(error, LimitReached | KeyReused | EditConflict):
        code, body = status.HTTP_409_CONFLICT, {"detail": error.code}
    elif isinstance(error, JumpDeleted):
        code, body = status.HTTP_410_GONE, {"detail": error.code}
    elif isinstance(error, DirectoryRuleError):
        code, body = status.HTTP_422_UNPROCESSABLE_CONTENT, {"detail": error.code}
    else:
        raise error
    return JSONResponse(body, status_code=code, headers=NO_STORE)


def create_router(
    *,
    service: Callable[[], LogbookService],
    access: AccessDependencies,
) -> APIRouter:
    router = APIRouter(prefix=PREFIX, tags=["skydiver-logbook"], responses=_ERRORS)

    def no_store(response: Response) -> None:
        response.headers["cache-control"] = "no-store"

    deps = [Depends(no_store)]
    Reader = Annotated[Actor, Depends(access.actor)]
    Writer = Annotated[Actor, Depends(access.verified_actor)]
    Errors = (
        NotFound,
        LikelyDuplicate,
        LimitReached,
        KeyReused,
        EditConflict,
        JumpDeleted,
        DirectoryRuleError,
    )

    @router.get(
        "/jumps",
        operation_id="listJumps",
        response_model=JumpPageOut,
        dependencies=deps,
    )
    def list_jumps(
        actor: Reader,
        cursor: Annotated[str | None, Query(max_length=200)] = None,
        limit: Annotated[int | None, Query(ge=1, le=50)] = None,
    ) -> JumpPageOut | JSONResponse:
        try:
            page = service().list_jumps(actor, cursor=cursor, limit=limit)
        except Errors as error:
            return _problem(error)
        return JumpPageOut(
            items=[_summary(v) for v in page.items],
            next_cursor=page.next_cursor,
            recorded_total=page.recorded_total,
        )

    # Before /jumps/{jump_id}, which would otherwise take "numbering" as an id.
    @router.get(
        "/jumps/numbering",
        operation_id="getJumpNumbering",
        response_model=JumpNumberingOut,
        dependencies=deps,
    )
    def get_numbering(actor: Reader) -> JumpNumberingOut:
        found = service().numbering(actor)
        return JumpNumberingOut(
            highest=found.highest,
            gaps=[
                NumberGapOut(
                    first=g.first,
                    last=g.last,
                    before=_numbered(g.before),
                    after=_numbered(g.after),
                )
                for g in found.gaps
            ],
            gap_count=found.gap_count,
            repeats=[
                NumberRepeatOut(
                    jump_number=r.number,
                    uses=r.uses,
                    jumps=[_numbered(j) for j in r.refs],
                )
                for r in found.repeats
            ],
            repeat_count=found.repeat_count,
        )

    @router.post(
        "/jumps",
        operation_id="createJump",
        response_model=JumpDetailOut,
        responses={201: {"model": JumpDetailOut}},
        dependencies=deps,
    )
    def create_jump(
        body: JumpIn, actor: Writer, response: Response
    ) -> JumpDetailOut | JSONResponse:
        try:
            detail, created = service().create_jump(
                actor,
                body.client_key,
                body.model_dump(exclude={"client_key", "confirm_distinct"}),
                confirm_distinct=body.confirm_distinct,
            )
        except Errors as error:
            return _problem(error)
        response.status_code = 201 if created else 200
        return _detail(detail)

    @router.get(
        "/jumps/{jump_id}",
        operation_id="getJump",
        response_model=JumpDetailOut,
        dependencies=deps,
    )
    def get_jump(jump_id: uuid.UUID, actor: Reader) -> JumpDetailOut | JSONResponse:
        try:
            return _detail(service().jump(actor, jump_id))
        except Errors as error:
            return _problem(error)

    @router.patch(
        "/jumps/{jump_id}",
        operation_id="updateJump",
        response_model=JumpDetailOut,
        dependencies=deps,
    )
    def update_jump(
        jump_id: uuid.UUID, body: JumpUpdateIn, actor: Writer
    ) -> JumpDetailOut | JSONResponse:
        try:
            return _detail(
                service().update_jump(
                    actor,
                    jump_id,
                    body.model_dump(exclude_unset=True, exclude={"version"}),
                    expected_version=body.version,
                )
            )
        except Errors as error:
            return _problem(error)

    @router.delete(
        "/jumps/{jump_id}",
        operation_id="deleteJump",
        status_code=status.HTTP_204_NO_CONTENT,
        dependencies=deps,
    )
    def delete_jump(
        jump_id: uuid.UUID,
        actor: Writer,
        version: Annotated[int | None, Query(ge=1)] = None,
    ) -> Response:
        try:
            service().delete_jump(actor, jump_id, expected_version=version)
        except Errors as error:
            return _problem(error)
        return Response(status_code=status.HTTP_204_NO_CONTENT, headers=NO_STORE)

    return router
