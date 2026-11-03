"""HTTP adapter for personal history and the prior-history baseline (#154). Owner-only.

Reads need a session; baseline changes need a confirmed email. Without a baseline
only `recorded` is reported. With one, `lifetime` is B plus the entries dated on or
after D, or null with `inconsistent` when more detailed entries predate D than B
declares. A correction carries the `version` it was based on (409 `edit_conflict`);
a first declaration carries none. Nothing here is shared, verified or a credential.
"""

from collections.abc import Callable
from datetime import date, datetime
from typing import Annotated, Any, Literal

from fastapi import APIRouter, Depends, Query, Response, status
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from app.skydiver.access.http import AccessDependencies
from app.skydiver.access.policy import Actor
from app.skydiver.directory.policy import DirectoryRuleError
from app.skydiver.directory.service import EditConflict
from app.skydiver.history.policy import Totals
from app.skydiver.history.service import HistoryService, Summary
from app.skydiver.logbook.api import ComponentRefOut, LocationOut

PREFIX = "/api/skydiver/v1"
NO_STORE = {"cache-control": "no-store"}


class Problem(BaseModel):
    detail: str


class BaselineIn(BaseModel):
    prior_jumps: Annotated[int, Field(ge=0, le=100_000)] = Field(
        description="Jumps completed before `before_on`, as you declare them."
    )
    before_on: date
    version: Annotated[int, Field(ge=1)] | None = Field(
        default=None, description="Omit to declare; the current version to correct."
    )


class BaselineOut(BaseModel):
    prior_jumps: int
    before_on: date
    source: Literal["manual"]
    version: int
    updated_at: datetime


class TotalsOut(BaseModel):
    recorded: int = Field(description="Distinct detailed entries.")
    prior_jumps: int | None = Field(description="Declared B, if any.")
    before_on: date | None = Field(description="Declared cutoff D, if any.")
    recorded_before: int | None = Field(
        description="Detailed entries before D; already within B."
    )
    recorded_since: int | None = Field(description="Detailed entries on or after D.")
    lifetime: int | None = Field(
        description="B + recorded_since; null without a baseline or when inconsistent."
    )
    inconsistent: bool


class MonthOut(BaseModel):
    month: str = Field(description="YYYY-MM")
    jumps: int


class TypeCountOut(BaseModel):
    jump_type: str
    jumps: int


class LocationCountOut(BaseModel):
    location: LocationOut
    jumps: int


class ComponentUseOut(BaseModel):
    component: ComponentRefOut
    jumps: int
    last_on: date


class BaselineEventOut(BaseModel):
    kind: Literal["declared", "corrected", "removed"]
    detail: dict[str, Any]
    created_at: datetime


class HistoryOut(BaseModel):
    totals: TotalsOut
    baseline: BaselineOut | None
    first_jump_on: date | None
    last_jump_on: date | None
    months: list[MonthOut] = Field(
        description="The last 12 calendar months, oldest first."
    )
    by_type: list[TypeCountOut]
    by_location: list[LocationCountOut]
    by_component: list[ComponentUseOut] = Field(
        description="Only components explicitly recorded on a jump."
    )
    baseline_events: list[BaselineEventOut] = Field(
        description="Private provenance, newest last (at most 50)."
    )


class BaselinePreviewOut(BaseModel):
    current: TotalsOut
    proposed: TotalsOut


_ERRORS: dict[int | str, dict[str, Any]] = {
    code: {"model": Problem} for code in (401, 403, 409, 422)
}


def _totals(t: Totals) -> TotalsOut:
    return TotalsOut(
        recorded=t.recorded,
        prior_jumps=t.baseline.prior_jumps if t.baseline else None,
        before_on=t.baseline.before_on if t.baseline else None,
        recorded_before=t.recorded_before,
        recorded_since=t.recorded_since,
        lifetime=t.lifetime,
        inconsistent=t.inconsistent,
    )


def _history(s: Summary) -> HistoryOut:
    return HistoryOut(
        totals=_totals(s.totals),
        baseline=BaselineOut(
            prior_jumps=s.baseline.prior_jumps,
            before_on=s.baseline.before_on,
            source="manual",
            version=s.baseline.version,
            updated_at=s.baseline.updated_at,
        )
        if s.baseline
        else None,
        first_jump_on=s.first_jump_on,
        last_jump_on=s.last_jump_on,
        months=[MonthOut(month=m, jumps=n) for m, n in s.months],
        by_type=[TypeCountOut(jump_type=k, jumps=n) for k, n in s.by_type],
        by_location=[
            LocationCountOut(
                location=LocationOut(
                    kind="venue" if loc.kind == "venue" else "place",
                    id=loc.id,
                    name=loc.name,
                    country=loc.country,
                    closed=loc.closed,
                ),
                jumps=n,
            )
            for loc, n in s.by_location
        ],
        by_component=[
            ComponentUseOut(
                component=ComponentRefOut(
                    id=u.component.id,
                    kind=u.component.kind,
                    label=u.component.label,
                    archived=u.component.archived,
                ),
                jumps=u.jumps,
                last_on=u.last_on,
            )
            for u in s.by_component
        ],
        baseline_events=[
            BaselineEventOut(
                kind=e.kind,  # type: ignore[arg-type]
                detail=e.detail,
                created_at=e.created_at,
            )
            for e in s.baseline_events
        ],
    )


def _problem(error: Exception) -> JSONResponse:
    if isinstance(error, EditConflict):
        code, body = status.HTTP_409_CONFLICT, {"detail": error.code}
    elif isinstance(error, DirectoryRuleError):
        code, body = status.HTTP_422_UNPROCESSABLE_CONTENT, {"detail": error.code}
    else:
        raise error
    return JSONResponse(body, status_code=code, headers=NO_STORE)


def create_router(
    *,
    service: Callable[[], HistoryService],
    access: AccessDependencies,
) -> APIRouter:
    router = APIRouter(prefix=PREFIX, tags=["skydiver-history"], responses=_ERRORS)

    def no_store(response: Response) -> None:
        response.headers["cache-control"] = "no-store"

    deps = [Depends(no_store)]
    Reader = Annotated[Actor, Depends(access.actor)]
    Writer = Annotated[Actor, Depends(access.verified_actor)]
    Errors = (EditConflict, DirectoryRuleError)

    @router.get(
        "/history",
        operation_id="getHistory",
        response_model=HistoryOut,
        dependencies=deps,
    )
    def get_history(actor: Reader) -> HistoryOut:
        return _history(service().summary(actor))

    @router.get(
        "/history/baseline/preview",
        operation_id="previewBaseline",
        response_model=BaselinePreviewOut,
        dependencies=deps,
    )
    def preview_baseline(
        actor: Reader,
        prior_jumps: Annotated[int, Query(ge=0, le=100_000)],
        before_on: date,
    ) -> BaselinePreviewOut | JSONResponse:
        try:
            p = service().preview(actor, prior_jumps, before_on)
        except Errors as error:
            return _problem(error)
        return BaselinePreviewOut(
            current=_totals(p.current), proposed=_totals(p.proposed)
        )

    @router.put(
        "/history/baseline",
        operation_id="setBaseline",
        response_model=HistoryOut,
        dependencies=deps,
    )
    def set_baseline(body: BaselineIn, actor: Writer) -> HistoryOut | JSONResponse:
        try:
            summary = service().set_baseline(
                actor, body.prior_jumps, body.before_on, expected_version=body.version
            )
        except Errors as error:
            return _problem(error)
        return _history(summary)

    @router.delete(
        "/history/baseline",
        operation_id="removeBaseline",
        status_code=status.HTTP_204_NO_CONTENT,
        dependencies=deps,
    )
    def remove_baseline(
        actor: Writer, version: Annotated[int, Query(ge=1)]
    ) -> Response:
        try:
            service().remove_baseline(actor, expected_version=version)
        except Errors as error:
            return _problem(error)
        return Response(status_code=status.HTTP_204_NO_CONTENT, headers=NO_STORE)

    return router
