"""HTTP adapter for personal history and the prior-history baseline (#154). Owner-only.

Reads need a session; baseline changes need a confirmed email. Without a baseline
only `recorded` is reported. With one, `lifetime` is B plus the entries dated on or
after D, or null with `inconsistent` when more detailed entries predate D than B
declares. A correction carries the `version` it was based on (409 `edit_conflict`);
a first declaration carries none. Nothing here is shared, verified or a credential.
"""

import uuid
from collections.abc import Callable
from datetime import date, datetime
from decimal import Decimal
from typing import Annotated, Any, Literal

from fastapi import APIRouter, Depends, Query, Response, status
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from app.skydiver.access.http import AccessDependencies
from app.skydiver.access.policy import Actor
from app.skydiver.directory.policy import DirectoryRuleError
from app.skydiver.directory.service import EditConflict
from app.skydiver.history import licences
from app.skydiver.history.currency import SOURCE, Currency, Licence
from app.skydiver.history.licences import Progress
from app.skydiver.history.policy import Totals
from app.skydiver.history.service import (
    HistoryService,
    MilestoneList,
    StatsView,
    Summary,
)
from app.skydiver.logbook.api import (
    ComponentRefOut,
    ExitWeightOut,
    LocationOut,
    MissingName,
    WeightUnitName,
)
from app.skydiver.logbook.loading import LoadingRange, WeightUnit, in_unit
from app.skydiver.logbook.service import ExitWeight, Location

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
    source: Literal["manual", "restored"]
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
    kind: Literal["declared", "corrected", "removed", "from_export"]
    detail: dict[str, Any]
    created_at: datetime


LicenceName = Literal["none", "student", "a", "b", "c", "d"]


class LicenceIn(BaseModel):
    licence: LicenceName = Field(description="The licence you hold; `none` to clear.")


class LicenceOut(BaseModel):
    licence: LicenceName = Field(description="Self-stated and private; never verified.")


class CurrencyOut(BaseModel):
    """Guidance computed from your own dated entries; not a verified status."""

    licence: LicenceName
    threshold_days: int | None = Field(
        description="Days after the last jump the guidance allows; null without a licence."
    )
    last_jump_on: date | None
    current_until: date | None = Field(
        description=(
            "The last calendar day counted as current; null without a licence or"
            " jumps. Compare with the jumper's own local date."
        )
    )
    source: Literal["USPA SIM 5-2"] = SOURCE


class LicenceProgressOut(BaseModel):
    """Progress toward the next USPA licence from your own entries. Guidance only:
    USPA and your instructors check every requirement, including the ones this app
    does not count (skills, proficiency card, landing accuracy, endorsements)."""

    licence: LicenceName
    next_licence: Literal["a", "b", "c", "d"] | None = Field(
        description="Null for a D licence: there is no next one."
    )
    jumps: int = Field(description="The reported total, else the recorded entries.")
    jumps_required: int | None
    jumps_include_prior: bool = Field(
        description="Your declared prior jump count is part of `jumps`."
    )
    freefall_seconds: int = Field(
        description="Recorded entries only; prior jumps have no freefall time."
    )
    freefall_required_seconds: int | None = Field(
        description="Null when the next licence lists no freefall time."
    )
    entries_with_freefall: int
    entries_without_freefall: int = Field(description="These add no freefall time.")
    source: Literal["USPA SIM 3-1"] = licences.SOURCE


class LoadingMonthOut(BaseModel):
    month: str = Field(description="YYYY-MM")
    highest: float = Field(description="The highest wing loading jumped that month.")
    jumps: int = Field(description="Entries that month with a known wing loading.")


class MissingCountOut(BaseModel):
    missing: MissingName
    jumps: int


class LoadingRangeOut(BaseModel):
    """Wing loading over your entries: exit weight in pounds over the main canopy's
    size in square feet. Not advice."""

    lowest: float | None
    highest: float | None
    known: int = Field(description="Entries with a known wing loading.")
    unknown: int
    missing: list[MissingCountOut] = Field(
        description="What the unknown entries lack (an entry can lack two things)."
    )


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
    currency: CurrencyOut
    progress: LicenceProgressOut | None = Field(description="Null without a licence.")
    wing_loading_months: list[LoadingMonthOut] = Field(
        description="The highest wing loading per month, for the latest 24 months that"
        " have one, oldest first."
    )
    wing_loading: LoadingRangeOut
    exit_weight: ExitWeightOut | None = Field(
        description="Your usual exit weight; null when not set."
    )


class ExitWeightIn(BaseModel):
    value: Annotated[Decimal, Field(gt=0, le=1000, decimal_places=1)] | None = Field(
        description="Your usual exit weight (body and gear), 30 to 250 kg (67 to 551"
        " lb), to one decimal; null clears it."
    )
    unit: WeightUnitName


class ExitWeightSettingOut(BaseModel):
    """Private to you; used only for wing loading. Never verified."""

    exit_weight: ExitWeightOut | None
    unit: WeightUnitName = Field(description="Your unit for weights.")


class PlaceCountOut(BaseModel):
    location: LocationOut
    jumps: int


class PlacesOut(BaseModel):
    items: list[PlaceCountOut] = Field(description="At most 10, most jumps first.")
    others: int = Field(description="Jumps at the other places.")
    other_places: int


class AircraftCountOut(BaseModel):
    aircraft: str = Field(description="Its most used spelling.")
    jumps: int


class AircraftOut(BaseModel):
    items: list[AircraftCountOut] = Field(description="At most 10, most jumps first.")
    others: int = Field(description="Jumps in the other aircraft.")
    other_aircraft: int
    not_recorded: int = Field(description="Entries without an aircraft.")


class YearCountOut(BaseModel):
    year: int
    jumps: int


class FreefallYearOut(BaseModel):
    year: int
    seconds: int = Field(description="Entries with a recorded freefall time only.")
    with_freefall: int
    without_freefall: int


class AltitudeOut(BaseModel):
    unit: Literal["ft", "m"] = Field(description="As entered; never converted.")
    jumps: int = Field(description="Entries with an exit altitude in this unit.")
    average: int
    highest: int


class StatsTotalOut(BaseModel):
    recorded: int = Field(description="Your entries in scope.")
    reported: int | None = Field(
        description="Without a year filter: your declared prior jump count plus the"
        " entries on or after its date, when they agree; else null."
    )
    prior_jumps: int | None = Field(
        description="The declared prior jump count within `reported`."
    )


class StatsOut(BaseModel):
    """Statistics from your own entries, private to you. A declared prior jump
    count is only in `total.reported`: it has no dates, types, places or
    measurements."""

    year: int | None = Field(description="The year filter, if any.")
    years: list[int] = Field(description="Years with an entry, newest first.")
    total: StatsTotalOut
    per_year: list[YearCountOut] = Field(
        description="Every year from your first entry, oldest first; not filtered."
    )
    per_month: list[MonthOut] = Field(
        description="The last 24 calendar months, or the 12 months of the year."
    )
    by_type: list[TypeCountOut]
    by_place: PlacesOut
    by_aircraft: AircraftOut
    freefall: list[FreefallYearOut] = Field(description="Oldest first.")
    altitudes: list[AltitudeOut] = Field(description="Feet first.")
    altitude_not_recorded: int
    wing_loading: LoadingRangeOut


class MilestoneOut(BaseModel):
    kind: Literal["jump_count", "freefall", "jump_type", "place"]
    on: date | None = Field(
        description="The entry's date; null for a jump count within your declared"
        " prior jumps (before you kept this logbook)."
    )
    jump_id: uuid.UUID | None
    number: int | None = Field(description="`jump_count`: the Nth jump.")
    hours: int | None = Field(description="`freefall`: recorded hours crossed.")
    jump_type: str | None = Field(description="`jump_type`: the first of this type.")
    location: LocationOut | None = Field(description="`place`: the first jump here.")


class MilestonesOut(BaseModel):
    """Private milestones derived from your own entries; never shared."""

    items: list[MilestoneOut] = Field(
        description="Newest first; jump counts before this logbook last. Only the"
        " five most recent first jumps at a new place."
    )
    counted: Literal["entries", "with_prior", "unchecked"] = Field(
        description="Jump counts number your entries (`entries`), continue from your"
        " declared prior jumps (`with_prior`), or are left out while that count"
        " disagrees with your entries (`unchecked`)."
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


def _weight(w: ExitWeight | None) -> ExitWeightOut | None:
    if w is None or w.grams is None:
        return None
    return ExitWeightOut(
        grams=w.grams, value=float(in_unit(w.grams, w.unit)), unit=w.unit.value
    )


def _range(r: LoadingRange) -> LoadingRangeOut:
    return LoadingRangeOut(
        lowest=float(r.lowest) if r.lowest is not None else None,
        highest=float(r.highest) if r.highest is not None else None,
        known=r.known,
        unknown=r.unknown,
        missing=[MissingCountOut(missing=m.value, jumps=n) for m, n in r.missing],
    )


def _stats(view: StatsView) -> StatsOut:
    s, t = view.stats, view.totals
    return StatsOut(
        year=s.year,
        years=s.years,
        total=StatsTotalOut(
            recorded=s.jumps,
            reported=t.lifetime if t else None,
            prior_jumps=t.baseline.prior_jumps
            if t and t.baseline and t.lifetime is not None
            else None,
        ),
        per_year=[YearCountOut(year=y, jumps=n) for y, n in s.per_year],
        per_month=[MonthOut(month=m, jumps=n) for m, n in s.per_month],
        by_type=[TypeCountOut(jump_type=k, jumps=n) for k, n in s.by_type],
        by_place=PlacesOut(
            items=[
                PlaceCountOut(location=_location(view.places[k]), jumps=n)
                for k, n in s.by_place.items
            ],
            others=s.by_place.others,
            other_places=s.by_place.other_count,
        ),
        by_aircraft=AircraftOut(
            items=[
                AircraftCountOut(aircraft=a, jumps=n) for a, n in s.by_aircraft.items
            ],
            others=s.by_aircraft.others,
            other_aircraft=s.by_aircraft.other_count,
            not_recorded=s.aircraft_not_recorded,
        ),
        freefall=[
            FreefallYearOut(
                year=f.year,
                seconds=f.seconds,
                with_freefall=f.with_time,
                without_freefall=f.without_time,
            )
            for f in s.freefall
        ],
        altitudes=[
            AltitudeOut(
                unit="m" if a.unit == "m" else "ft",
                jumps=a.jumps,
                average=a.average,
                highest=a.highest,
            )
            for a in s.altitudes
        ],
        altitude_not_recorded=s.altitude_not_recorded,
        wing_loading=_range(s.loading),
    )


def _currency(c: Currency) -> CurrencyOut:
    return CurrencyOut(
        licence=c.licence.value,
        threshold_days=c.days,
        last_jump_on=c.last_jump_on,
        current_until=c.current_until,
    )


def _progress(p: Progress | None) -> LicenceProgressOut | None:
    if p is None:
        return None
    req = p.requirement
    return LicenceProgressOut(
        licence=p.licence.value,
        next_licence=p.next_licence.value if p.next_licence else None,  # type: ignore[arg-type]
        jumps=p.jumps,
        jumps_required=req.jumps if req else None,
        jumps_include_prior=p.jumps_include_prior,
        freefall_seconds=p.freefall_seconds,
        freefall_required_seconds=(req.freefall_seconds or None) if req else None,
        entries_with_freefall=p.entries_with_freefall,
        entries_without_freefall=p.entries_without_freefall,
    )


def _location(loc: Location) -> LocationOut:
    return LocationOut(
        kind="venue" if loc.kind == "venue" else "place",
        id=loc.id,
        name=loc.name,
        country=loc.country,
        closed=loc.closed,
    )


def _milestones(found: MilestoneList) -> MilestonesOut:
    return MilestonesOut(
        items=[
            MilestoneOut(
                kind=v.milestone.kind.value,
                on=v.milestone.on,
                jump_id=v.milestone.jump_id,
                number=v.milestone.number,
                hours=v.milestone.hours,
                jump_type=v.milestone.jump_type,
                location=_location(v.location) if v.location else None,
            )
            for v in found.items
        ],
        counted=found.counted,
    )


def _history(s: Summary) -> HistoryOut:
    return HistoryOut(
        totals=_totals(s.totals),
        baseline=BaselineOut(
            prior_jumps=s.baseline.prior_jumps,
            before_on=s.baseline.before_on,
            source="restored" if s.baseline.source == "restored" else "manual",
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
            LocationCountOut(location=_location(loc), jumps=n)
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
        currency=_currency(s.currency),
        progress=_progress(s.progress),
        wing_loading_months=[
            LoadingMonthOut(month=m, highest=float(v), jumps=n)
            for m, v, n in s.loading_months or []
        ],
        wing_loading=_range(s.loading or LoadingRange(None, None, 0, 0, [])),
        exit_weight=_weight(s.exit_weight),
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
        "/history/milestones",
        operation_id="getMilestones",
        response_model=MilestonesOut,
        dependencies=deps,
    )
    def get_milestones(actor: Reader) -> MilestonesOut:
        """Dated milestones from your own entries, newest first. Computed on read."""
        return _milestones(service().milestones(actor))

    @router.get(
        "/history/stats",
        operation_id="getStats",
        response_model=StatsOut,
        dependencies=deps,
    )
    def get_stats(
        actor: Reader,
        year: Annotated[
            int | None, Query(ge=1919, le=9999, description="Only this year.")
        ] = None,
    ) -> StatsOut | JSONResponse:
        """Statistics from your own entries, computed on read in a few queries."""
        try:
            return _stats(service().stats(actor, year))
        except Errors as error:
            return _problem(error)

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

    @router.get(
        "/me/licence",
        operation_id="getLicence",
        response_model=LicenceOut,
        dependencies=deps,
    )
    def get_licence(actor: Reader) -> LicenceOut:
        return LicenceOut(licence=service().licence(actor).value)

    @router.put(
        "/me/licence",
        operation_id="setLicence",
        response_model=LicenceOut,
        dependencies=deps,
    )
    def set_licence(body: LicenceIn, actor: Writer) -> LicenceOut:
        saved = service().set_licence(actor, Licence(body.licence))
        return LicenceOut(licence=saved.value)

    @router.get(
        "/me/exit-weight",
        operation_id="getExitWeight",
        response_model=ExitWeightSettingOut,
        dependencies=deps,
    )
    def get_exit_weight(actor: Reader) -> ExitWeightSettingOut:
        found = service().exit_weight(actor)
        return ExitWeightSettingOut(exit_weight=_weight(found), unit=found.unit.value)

    @router.put(
        "/me/exit-weight",
        operation_id="setExitWeight",
        response_model=ExitWeightSettingOut,
        dependencies=deps,
    )
    def set_exit_weight(
        body: ExitWeightIn, actor: Writer
    ) -> ExitWeightSettingOut | JSONResponse:
        try:
            saved = service().set_exit_weight(actor, body.value, WeightUnit(body.unit))
        except Errors as error:
            return _problem(error)
        return ExitWeightSettingOut(exit_weight=_weight(saved), unit=saved.unit.value)

    return router
