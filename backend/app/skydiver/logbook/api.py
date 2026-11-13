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
from pydantic import BaseModel, ConfigDict, Field

from app.skydiver.access.http import AccessDependencies
from app.skydiver.access.policy import Actor
from app.skydiver.directory.policy import DirectoryRuleError
from app.skydiver.directory.service import EditConflict
from app.skydiver.logbook.loading import Loading, in_unit
from app.skydiver.logbook.policy import JumpType
from app.skydiver.logbook.service import (
    AlreadyUndone,
    BatchPreview,
    BatchResult,
    JumpDeleted,
    JumpDetail,
    JumpFilter,
    JumpView,
    KeyReused,
    LikelyDuplicate,
    LimitReached,
    LoadingContext,
    LogbookService,
    NotFound,
    NumberedRef,
    PrintPage,
    UndoResult,
    UndoUnavailable,
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
    aircraft: Annotated[str, Field(max_length=120)] | None = Field(
        default=None,
        description='The aircraft as you write it, e.g. "Cessna 208 SX-ABC" (60 at most).',
    )
    exit_weight_grams: Annotated[int, Field(ge=1, le=1_000_000)] | None = Field(
        default=None,
        description="Your exit weight on this jump (body and gear) in grams, 30,000"
        " to 250,000; omit or null to use your usual exit weight.",
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
    canopy_size_sqft: int | None = Field(
        default=None, description="A main or reserve canopy's size in square feet."
    )


WeightUnitName = Literal["kg", "lb"]
MissingName = Literal["exit_weight", "main_canopy", "canopy_size", "several_mains"]


class WingLoadingOut(BaseModel):
    """Exit weight in pounds over the main canopy's size in square feet, from your
    own entries. Not advice: no limit or recommendation is applied."""

    value: float | None = Field(
        description="Pounds per square foot, two decimals; null when unknown."
    )
    exit_weight_grams: int | None = Field(description="The exit weight used.")
    exit_weight_from_jump: bool = Field(
        description="This jump's own exit weight, not your usual one."
    )
    unit: WeightUnitName = Field(description="Your unit for showing weights.")
    canopy_size_sqft: int | None = Field(description="The main canopy's size used.")
    missing: list[MissingName] = Field(
        description="What is missing when `value` is null: `exit_weight` (none on the"
        " jump or in your settings), `main_canopy` (none recorded on the jump),"
        " `canopy_size` (the main has no size), `several_mains` (more than one main"
        " recorded)."
    )


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
    aircraft: str | None
    exit_weight_grams: int | None = Field(
        description="This jump's own exit weight, if you entered one."
    )
    wing_loading: WingLoadingOut
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
    aircraft: str | None
    wing_loading: WingLoadingOut


class MatchedOut(BaseModel):
    """Totals over every jump matching the filters (all jumps when unfiltered)."""

    jumps: int
    freefall_seconds: int | None = Field(
        description="Sum over the matching jumps that recorded a freefall time."
    )
    freefall_recorded: int = Field(
        description="How many matching jumps recorded a freefall time."
    )
    first_on: date | None
    last_on: date | None


class JumpPageOut(BaseModel):
    items: list[JumpSummaryOut]
    next_cursor: str | None
    recorded_total: int = Field(
        description="Detailed entries you recorded; not a lifetime total."
    )
    matched: MatchedOut


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


class BroughtForwardOut(BaseModel):
    jumps: int = Field(description="Your entries dated before `from_on`.")
    freefall_seconds: int = Field(
        description="Their recorded freefall time; entries without one add nothing."
    )


class PrintPageOut(BaseModel):
    """Full entries, oldest first, for printing your own logbook."""

    items: list[JumpOut]
    next_cursor: str | None
    brought_forward: BroughtForwardOut


class ExitWeightOut(BaseModel):
    grams: int = Field(description="The weight in grams.")
    value: float = Field(description="In `unit`, to one decimal, as you entered it.")
    unit: WeightUnitName


class LoadingContextOut(BaseModel):
    """For the jump form: your usual exit weight and the highest wing loading among
    your other jumps, to compare a new one with."""

    exit_weight: ExitWeightOut | None = Field(description="Null when not set.")
    unit: WeightUnitName = Field(description="Your unit for weights.")
    highest: float | None = Field(
        description="The highest known wing loading of your other jumps; null when"
        " none is known."
    )


class RecentAircraftOut(BaseModel):
    """A starting value for a new entry at this place; null when none is recorded."""

    aircraft: str | None


class BatchChangesIn(BaseModel):
    """What every chosen jump gets. Leave a key out to keep each jump's own value;
    `aircraft: null` clears it and `component_ids: []` clears the gear used."""

    model_config = ConfigDict(extra="forbid")

    jump_type: JumpTypeName | None = None
    venue_id: uuid.UUID | None = Field(default=None, description="A listed dropzone.")
    place_id: uuid.UUID | None = Field(
        default=None, description="One of your private places."
    )
    aircraft: Annotated[str, Field(max_length=120)] | None = None
    component_ids: Annotated[list[uuid.UUID], Field(max_length=20)] | None = Field(
        default=None, description="Replaces the set of your own components used."
    )


class BatchPreviewIn(BaseModel):
    jump_ids: Annotated[list[uuid.UUID], Field(min_length=1, max_length=400)] = Field(
        description="Your jumps to change, at most 200."
    )
    changes: BatchChangesIn


class BatchJumpIn(BaseModel):
    id: uuid.UUID
    version: Version = Field(description="The version the preview showed.")


class BatchApplyIn(BaseModel):
    jumps: Annotated[list[BatchJumpIn], Field(min_length=1, max_length=400)] = Field(
        description="At most 200; a jump changed since its version is skipped."
    )
    changes: BatchChangesIn


class BatchUndoIn(BaseModel):
    batch_id: uuid.UUID


class BatchItemOut(JumpSummaryOut):
    version: int
    will_change: bool = Field(description="False when it already has these values.")


class BatchPreviewOut(BaseModel):
    """What the change would do. Nothing is written."""

    items: list[BatchItemOut]
    missing: int = Field(description="Chosen jumps that are not in your logbook.")
    changing: int = Field(description="Jumps that would change.")
    location: LocationOut | None = Field(description="The new place, if it changes.")
    components: list[ComponentRefOut] | None = Field(
        description="The new gear used, if it changes."
    )


class SkippedOut(BaseModel):
    id: uuid.UUID
    reason: Literal["edited", "not_found", "gone", "invalid"] = Field(
        description="`edited`: changed since it was shown; `not_found`/`gone`: no longer"
        " there, or its earlier place or gear was deleted; `invalid`: an earlier value"
        " is no longer accepted (e.g. its dropzone is no longer listed)."
    )


class BatchResultOut(BaseModel):
    batch_id: uuid.UUID | None = Field(description="Null when no jump changed.")
    changed: list[uuid.UUID]
    unchanged: list[uuid.UUID] = Field(description="Already had these values.")
    skipped: list[SkippedOut]


class LatestBatchOut(BaseModel):
    """Your latest change of many jumps; it can be undone once, for 24 hours."""

    batch_id: uuid.UUID
    created_at: datetime
    changed: int
    undo_until: datetime
    undone: bool
    can_undo: bool


class LatestBatchStateOut(BaseModel):
    latest: LatestBatchOut | None


class UndoResultOut(BaseModel):
    restored: list[uuid.UUID]
    skipped: list[SkippedOut]


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
        ComponentRefOut(
            id=c.id,
            kind=c.kind,
            label=c.label,
            archived=c.archived,
            canopy_size_sqft=c.canopy_size,
        )
        for c in view.components
    ]


def _loading(view: JumpView) -> WingLoadingOut:
    w: Loading | None = view.loading
    return WingLoadingOut(
        value=float(w.value) if w and w.value is not None else None,
        exit_weight_grams=w.weight_grams if w else None,
        exit_weight_from_jump=bool(w and w.weight_from_jump),
        unit=view.weight_unit.value,
        canopy_size_sqft=w.canopy_size if w else None,
        missing=[m.value for m in w.missing] if w else [],
    )


def loading_context_out(found: LoadingContext) -> LoadingContextOut:
    usual = found.usual
    return LoadingContextOut(
        exit_weight=ExitWeightOut(
            grams=usual.grams,
            value=float(in_unit(usual.grams, usual.unit)),
            unit=usual.unit.value,
        )
        if usual.grams is not None
        else None,
        unit=usual.unit.value,
        highest=float(found.highest) if found.highest is not None else None,
    )


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
        aircraft=j.aircraft,
        exit_weight_grams=j.exit_weight_grams,
        wing_loading=_loading(view),
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
        aircraft=j.aircraft,
        wing_loading=_loading(view),
    )


def _batch_preview(preview: BatchPreview) -> BatchPreviewOut:
    items = [
        BatchItemOut(
            **_summary(view).model_dump(), version=view.jump.version, will_change=change
        )
        for view, change in preview.items
    ]
    loc = preview.location
    return BatchPreviewOut(
        items=items,
        missing=preview.missing,
        changing=sum(1 for i in items if i.will_change),
        location=LocationOut(
            kind="venue" if loc.kind == "venue" else "place",
            id=loc.id,
            name=loc.name,
            country=loc.country,
            closed=loc.closed,
        )
        if loc
        else None,
        components=[
            ComponentRefOut(
                id=c.id,
                kind=c.kind,
                label=c.label,
                archived=c.archived,
                canopy_size_sqft=c.canopy_size,
            )
            for c in preview.components
        ]
        if preview.components is not None
        else None,
    )


def _skipped(items: list[tuple[uuid.UUID, str]]) -> list[SkippedOut]:
    return [SkippedOut(id=i, reason=r) for i, r in items]  # type: ignore[arg-type]


def _batch_result(result: BatchResult) -> BatchResultOut:
    return BatchResultOut(
        batch_id=result.batch_id,
        changed=result.changed,
        unchanged=result.unchanged,
        skipped=_skipped(result.skipped),
    )


def _undo_result(result: UndoResult) -> UndoResultOut:
    return UndoResultOut(restored=result.restored, skipped=_skipped(result.skipped))


def _print_page(page: PrintPage) -> PrintPageOut:
    return PrintPageOut(
        items=[_jump(v) for v in page.items],
        next_cursor=page.next_cursor,
        brought_forward=BroughtForwardOut(
            jumps=page.before_jumps, freefall_seconds=page.before_freefall_seconds
        ),
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
    elif isinstance(
        error, LimitReached | KeyReused | EditConflict | UndoUnavailable | AlreadyUndone
    ):
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
        UndoUnavailable,
        AlreadyUndone,
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
        q: Annotated[
            str | None,
            Query(
                max_length=100,
                description="Text in the place name, aircraft or your private notes.",
            ),
        ] = None,
        jump_type: JumpTypeName | None = None,
        venue_id: Annotated[
            uuid.UUID | None, Query(description="A listed dropzone, merges included.")
        ] = None,
        place_id: Annotated[
            uuid.UUID | None, Query(description="One of your private places.")
        ] = None,
        from_date: Annotated[date | None, Query(description="On or after.")] = None,
        to_date: Annotated[date | None, Query(description="On or before.")] = None,
        number_from: Annotated[int | None, Query(ge=1, le=1_000_000)] = None,
        number_to: Annotated[int | None, Query(ge=1, le=1_000_000)] = None,
    ) -> JumpPageOut | JSONResponse:
        search = JumpFilter(
            text=q,
            jump_type=JumpType(jump_type) if jump_type else None,
            venue_id=venue_id,
            place_id=place_id,
            from_date=from_date,
            to_date=to_date,
            number_from=number_from,
            number_to=number_to,
        )
        try:
            page = service().list_jumps(
                actor, cursor=cursor, limit=limit, search=search
            )
        except Errors as error:
            return _problem(error)
        m = page.matched
        return JumpPageOut(
            items=[_summary(v) for v in page.items],
            next_cursor=page.next_cursor,
            recorded_total=page.recorded_total,
            matched=MatchedOut(
                jumps=m.jumps,
                freefall_seconds=m.freefall_seconds,
                freefall_recorded=m.freefall_recorded,
                first_on=m.first_on,
                last_on=m.last_on,
            ),
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

    # Before /jumps/{jump_id}, which would otherwise take "recent-aircraft" as an id.
    @router.get(
        "/jumps/recent-aircraft",
        operation_id="getRecentAircraft",
        response_model=RecentAircraftOut,
        dependencies=deps,
    )
    def get_recent_aircraft(
        actor: Reader,
        venue_id: Annotated[
            uuid.UUID | None, Query(description="A listed dropzone, merges included.")
        ] = None,
        place_id: Annotated[
            uuid.UUID | None, Query(description="One of your private places.")
        ] = None,
    ) -> RecentAircraftOut | JSONResponse:
        """The aircraft of your newest jump at this place that recorded one."""
        try:
            found = service().recent_aircraft(
                actor, venue_id=venue_id, place_id=place_id
            )
        except Errors as error:
            return _problem(error)
        return RecentAircraftOut(aircraft=found)

    # Before /jumps/{jump_id}, which would otherwise take "wing-loading" as an id.
    @router.get(
        "/jumps/wing-loading",
        operation_id="getWingLoadingContext",
        response_model=LoadingContextOut,
        dependencies=deps,
    )
    def get_wing_loading_context(
        actor: Reader,
        exclude: Annotated[
            uuid.UUID | None,
            Query(description="A jump of yours being edited, left out of `highest`."),
        ] = None,
    ) -> LoadingContextOut:
        """Your usual exit weight and the highest wing loading among your jumps."""
        return loading_context_out(service().loading_context(actor, exclude=exclude))

    # -- many jumps at once (before /jumps/{jump_id}) ------------------------------

    @router.post(
        "/jumps/batch/preview",
        operation_id="previewJumpBatch",
        response_model=BatchPreviewOut,
        dependencies=deps,
    )
    def preview_batch(
        body: BatchPreviewIn, actor: Reader
    ) -> BatchPreviewOut | JSONResponse:
        """What setting these values on these jumps would change. Writes nothing."""
        try:
            preview = service().preview_batch(
                actor, body.jump_ids, body.changes.model_dump(exclude_unset=True)
            )
        except Errors as error:
            return _problem(error)
        return _batch_preview(preview)

    @router.post(
        "/jumps/batch",
        operation_id="applyJumpBatch",
        response_model=BatchResultOut,
        dependencies=deps,
    )
    def apply_batch(body: BatchApplyIn, actor: Writer) -> BatchResultOut | JSONResponse:
        """Set these values on these jumps, each compare-and-swap on its version."""
        versions: dict[uuid.UUID, int] = {}
        for item in body.jumps:
            versions.setdefault(item.id, item.version)
        try:
            result = service().apply_batch(
                actor, versions, body.changes.model_dump(exclude_unset=True)
            )
        except Errors as error:
            return _problem(error)
        return _batch_result(result)

    @router.get(
        "/jumps/batch/latest",
        operation_id="getLatestJumpBatch",
        response_model=LatestBatchStateOut,
        dependencies=deps,
    )
    def latest_batch(actor: Reader) -> LatestBatchStateOut:
        found = service().latest_batch(actor)
        return LatestBatchStateOut(
            latest=LatestBatchOut(
                batch_id=found.id,
                created_at=found.created_at,
                changed=found.changed,
                undo_until=found.undo_until,
                undone=found.undone,
                can_undo=found.can_undo,
            )
            if found
            else None
        )

    @router.post(
        "/jumps/batch/undo",
        operation_id="undoJumpBatch",
        response_model=UndoResultOut,
        dependencies=deps,
    )
    def undo_batch(body: BatchUndoIn, actor: Writer) -> UndoResultOut | JSONResponse:
        """Put back what your latest change of many jumps replaced, where untouched since."""
        try:
            return _undo_result(service().undo_batch(actor, body.batch_id))
        except Errors as error:
            return _problem(error)

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

    # Before `/jumps/{jump_id}`, which would otherwise read "in-order" as an id.
    @router.get(
        "/jumps/in-order",
        operation_id="listJumpsInOrder",
        response_model=PrintPageOut,
        dependencies=deps,
    )
    def list_jumps_in_order(
        actor: Reader,
        from_on: date | None = None,
        until_on: date | None = None,
        cursor: Annotated[str | None, Query(max_length=200)] = None,
        limit: Annotated[int | None, Query(ge=1, le=200)] = None,
    ) -> PrintPageOut | JSONResponse:
        try:
            page = service().in_order(
                actor, from_on=from_on, until_on=until_on, cursor=cursor, limit=limit
            )
        except Errors as error:
            return _problem(error)
        return _print_page(page)

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
