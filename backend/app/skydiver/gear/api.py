"""HTTP adapter for private gear (#152). Owner-only.

Reads need a session; writes need a confirmed email. Creates carry a client key
(retry-safe); edits carry the `version` they were based on (409 `edit_conflict`).
Every value is the owner's own declaration: responses say so, and nothing here is
shared, matched against other accounts or presented as verified.
"""

import uuid
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
from app.skydiver.gear.policy import REPACK_SOURCE
from app.skydiver.gear.service import (
    Component,
    ComponentDetail,
    ComponentSummary,
    DueItem,
    GearService,
    KeyReused,
    LimitReached,
    Membership,
    NotFound,
    Rig,
    ServiceEntry,
)

PREFIX = "/api/skydiver/v1"
NO_STORE = {"cache-control": "no-store"}

Kind = Literal["container", "main", "reserve", "aad", "other"]
RelationName = Literal["owned", "borrowed", "rented"]
Method = Literal["purchase", "gift", "inheritance", "other"]
ServiceKindName = Literal["repack", "inspection", "maintenance", "aad_service", "other"]
Short = Annotated[str, Field(max_length=200)]
PartialDateText = Annotated[
    str,
    Field(
        max_length=10,
        description="YYYY, YYYY-MM or YYYY-MM-DD: only the precision that is known.",
    ),
]
Notes = Annotated[str, Field(max_length=2000)]
Version = Annotated[int, Field(ge=1)]


class Problem(BaseModel):
    detail: str


class ComponentDetails(BaseModel):
    manufacturer: Short | None = None
    model: Short | None = None
    serial: Annotated[str, Field(max_length=400)] | None = Field(
        default=None, description="Kept exactly as entered. Private."
    )
    manufactured: PartialDateText | None = None
    relation: RelationName | None = None
    acquisition_method: Method | None = None
    acquired: PartialDateText | None = None
    notes: Notes | None = None
    repack_interval_days: Annotated[int, Field(ge=1, le=730)] | None = Field(
        default=None,
        description=(
            "A reserve's repack interval in days; null: 180 (USPA / FAA 14 CFR"
            " 105.43). Your country's rule may differ."
        ),
    )
    end_of_life_on: date | None = Field(
        default=None,
        description="An end-of-life date you entered (e.g. from the label). Never estimated.",
    )


class ComponentIn(ComponentDetails):
    client_key: uuid.UUID
    kind: Kind
    label: Short


class ComponentUpdateIn(ComponentDetails):
    kind: Kind | None = None
    label: Short | None = None
    version: Version | None = None


class ArchiveIn(BaseModel):
    archived: bool
    version: Version | None = None


class RigPlacementIn(BaseModel):
    rig_id: uuid.UUID | None = Field(description="Null takes it out of its rig.")
    on: date = Field(description="The day the change applies; past rigs keep dates.")
    version: Version | None = None


class ServiceIn(BaseModel):
    client_key: uuid.UUID
    kind: ServiceKindName
    done_on: date
    due_on: date | None = None
    performed_by: Short | None = None
    notes: Notes | None = None


class RigIn(BaseModel):
    client_key: uuid.UUID
    label: Short


class RigUpdateIn(BaseModel):
    label: Short | None = None
    archived: bool | None = None
    version: Version | None = None


class ComponentOut(BaseModel):
    """The owner's own record. `provenance` is always self-reported."""

    id: uuid.UUID
    kind: Kind
    label: str
    manufacturer: str | None
    model: str | None
    serial: str | None
    manufactured: str | None
    relation: RelationName
    acquisition_method: Method | None
    acquired: str | None
    notes: str | None
    repack_interval_days: int | None = Field(
        description="Your own reserve repack interval; null: the default of 180 days."
    )
    end_of_life_on: date | None
    archived: bool
    provenance: Literal["self_reported"] = "self_reported"
    version: int
    updated_at: datetime


class RigRefOut(BaseModel):
    rig_id: uuid.UUID
    rig_label: str
    from_on: date
    until_on: date | None


class ComponentSummaryOut(BaseModel):
    component: ComponentOut
    rig: RigRefOut | None
    next_due: date | None = Field(
        description="Latest due date the owner entered; not an airworthiness status."
    )


class ServiceOut(BaseModel):
    id: uuid.UUID
    kind: ServiceKindName
    done_on: date
    due_on: date | None
    performed_by: str | None
    notes: str | None
    provenance: Literal["self_reported"] = "self_reported"
    created_at: datetime


class GearEventOut(BaseModel):
    kind: str
    detail: dict[str, Any]
    created_at: datetime


class ComponentDetailOut(BaseModel):
    component: ComponentOut
    rig: RigRefOut | None
    rig_history: list[RigRefOut]
    service: list[ServiceOut]
    events: list[GearEventOut]
    same_serial: list[uuid.UUID] = Field(
        description="Your other components with the same serial (yours only)."
    )


class DueComponentOut(BaseModel):
    id: uuid.UUID
    kind: Kind
    label: str


class GearDueOut(BaseModel):
    """A date coming due on your own gear, from your own records. Not an
    airworthiness status: your rigger and the manufacturer decide that."""

    component: DueComponentOut
    kind: Literal["reserve_repack", "service", "end_of_life"]
    service_kind: ServiceKindName | None = Field(
        description="The service entry it comes from; null for an end of life."
    )
    due_on: date = Field(description="Still in time on this day; overdue after it.")
    basis: Literal["entered", "interval"] = Field(
        description="`entered`: your own date. `interval`: your latest repack plus"
        " `interval_days`."
    )
    interval_days: int | None
    interval_source: Literal["USPA / FAA 14 CFR 105.43"] | None = Field(
        description="Set when the default interval applies."
    )
    status: Literal["overdue", "soon", "later"] = Field(
        description="`soon`: due within 30 days. Judged on the latest calendar date"
        " anywhere; compare `due_on` with your own day for the exact count."
    )


class RigMemberOut(BaseModel):
    id: uuid.UUID
    kind: Kind
    label: str
    from_on: date


class RigOut(BaseModel):
    id: uuid.UUID
    label: str
    archived: bool
    version: int
    components: list[RigMemberOut]


_ERRORS: dict[int | str, dict[str, Any]] = {
    code: {"model": Problem} for code in (401, 403, 404, 409, 422)
}


def _component(c: Component) -> ComponentOut:
    return ComponentOut(
        id=c.id,
        kind=c.kind.value,
        label=c.label,
        manufacturer=c.manufacturer,
        model=c.model,
        serial=c.serial,
        manufactured=c.manufactured,
        relation=c.relation.value,
        acquisition_method=c.acquisition_method.value if c.acquisition_method else None,
        acquired=c.acquired,
        notes=c.notes,
        repack_interval_days=c.repack_interval_days,
        end_of_life_on=c.end_of_life_on,
        archived=c.archived_at is not None,
        version=c.version,
        updated_at=c.updated_at,
    )


def _ref(m: Membership | None) -> RigRefOut | None:
    if m is None:
        return None
    return RigRefOut(
        rig_id=m.rig_id, rig_label=m.rig_label, from_on=m.from_on, until_on=m.until_on
    )


def _service(e: ServiceEntry) -> ServiceOut:
    return ServiceOut(
        id=e.id,
        kind=e.kind.value,
        done_on=e.done_on,
        due_on=e.due_on,
        performed_by=e.performed_by,
        notes=e.notes,
        created_at=e.created_at,
    )


def _summary(s: ComponentSummary) -> ComponentSummaryOut:
    return ComponentSummaryOut(
        component=_component(s.component), rig=_ref(s.rig), next_due=s.next_due
    )


def _detail(d: ComponentDetail) -> ComponentDetailOut:
    return ComponentDetailOut(
        component=_component(d.component),
        rig=_ref(d.rig),
        rig_history=[r for r in map(_ref, d.rig_history) if r is not None],
        service=[_service(e) for e in d.service],
        events=[
            GearEventOut(kind=e.kind, detail=e.detail, created_at=e.created_at)
            for e in d.events
        ],
        same_serial=d.same_serial,
    )


def _due(item: DueItem) -> GearDueOut:
    c, due = item.component, item.due
    return GearDueOut(
        component=DueComponentOut(id=c.id, kind=c.kind.value, label=c.label),
        kind=due.kind.value,
        service_kind=due.service_kind.value if due.service_kind else None,
        due_on=due.due_on,
        basis=due.basis,
        interval_days=due.interval_days,
        interval_source=REPACK_SOURCE if due.interval_is_default else None,
        status=item.status.value,
    )


def _rig(rig: Rig, members: list[tuple[Component, Membership]]) -> RigOut:
    return RigOut(
        id=rig.id,
        label=rig.label,
        archived=rig.archived_at is not None,
        version=rig.version,
        components=[
            RigMemberOut(id=c.id, kind=c.kind.value, label=c.label, from_on=m.from_on)
            for c, m in members
        ],
    )


def _problem(error: Exception) -> JSONResponse:
    if isinstance(error, NotFound):
        code, detail = status.HTTP_404_NOT_FOUND, "not_found"
    elif isinstance(error, LimitReached):
        code, detail = status.HTTP_409_CONFLICT, error.code
    elif isinstance(error, KeyReused | EditConflict):
        code, detail = status.HTTP_409_CONFLICT, error.code
    elif isinstance(error, DirectoryRuleError):
        code, detail = status.HTTP_422_UNPROCESSABLE_CONTENT, error.code
    else:
        raise error
    return JSONResponse({"detail": detail}, status_code=code, headers=NO_STORE)


def create_router(
    *,
    service: Callable[[], GearService],
    access: AccessDependencies,
) -> APIRouter:
    router = APIRouter(prefix=PREFIX, tags=["skydiver-gear"], responses=_ERRORS)

    def no_store(response: Response) -> None:
        response.headers["cache-control"] = "no-store"

    deps = [Depends(no_store)]
    Reader = Annotated[Actor, Depends(access.actor)]
    Writer = Annotated[Actor, Depends(access.verified_actor)]
    Errors = (NotFound, LimitReached, KeyReused, EditConflict, DirectoryRuleError)

    # -- components -----------------------------------------------------------------

    @router.get(
        "/gear/components",
        operation_id="listComponents",
        response_model=list[ComponentSummaryOut],
        dependencies=deps,
    )
    def list_components(
        actor: Reader, archived: Annotated[bool, Query()] = False
    ) -> list[ComponentSummaryOut]:
        return [
            _summary(s) for s in service().list_components(actor, archived=archived)
        ]

    @router.get(
        "/gear/due",
        operation_id="listGearDue",
        response_model=list[GearDueOut],
        dependencies=deps,
    )
    def list_gear_due(actor: Reader) -> list[GearDueOut]:
        """Dates coming due on your current gear, soonest first (overdue included)."""
        return [_due(item) for item in service().due(actor)]

    @router.post(
        "/gear/components",
        operation_id="createComponent",
        response_model=ComponentDetailOut,
        responses={201: {"model": ComponentDetailOut}},
        dependencies=deps,
    )
    def create_component(
        body: ComponentIn, actor: Writer, response: Response
    ) -> ComponentDetailOut | JSONResponse:
        try:
            detail, created = service().create_component(
                actor, body.client_key, body.model_dump(exclude={"client_key"})
            )
        except Errors as error:
            return _problem(error)
        response.status_code = 201 if created else 200
        return _detail(detail)

    @router.get(
        "/gear/components/{component_id}",
        operation_id="getComponent",
        response_model=ComponentDetailOut,
        dependencies=deps,
    )
    def get_component(
        component_id: uuid.UUID, actor: Reader
    ) -> ComponentDetailOut | JSONResponse:
        try:
            return _detail(service().component(actor, component_id))
        except Errors as error:
            return _problem(error)

    @router.patch(
        "/gear/components/{component_id}",
        operation_id="updateComponent",
        response_model=ComponentDetailOut,
        dependencies=deps,
    )
    def update_component(
        component_id: uuid.UUID, body: ComponentUpdateIn, actor: Writer
    ) -> ComponentDetailOut | JSONResponse:
        try:
            detail = service().update_component(
                actor,
                component_id,
                body.model_dump(exclude_unset=True, exclude={"version"}),
                expected_version=body.version,
            )
        except Errors as error:
            return _problem(error)
        return _detail(detail)

    @router.post(
        "/gear/components/{component_id}/archive",
        operation_id="archiveComponent",
        response_model=ComponentDetailOut,
        dependencies=deps,
    )
    def archive_component(
        component_id: uuid.UUID, body: ArchiveIn, actor: Writer
    ) -> ComponentDetailOut | JSONResponse:
        try:
            detail = service().set_archived(
                actor, component_id, body.archived, expected_version=body.version
            )
        except Errors as error:
            return _problem(error)
        return _detail(detail)

    @router.delete(
        "/gear/components/{component_id}",
        operation_id="deleteComponent",
        status_code=status.HTTP_204_NO_CONTENT,
        dependencies=deps,
    )
    def delete_component(
        component_id: uuid.UUID,
        actor: Writer,
        version: Annotated[int | None, Query(ge=1)] = None,
    ) -> Response:
        try:
            service().delete_component(actor, component_id, expected_version=version)
        except Errors as error:
            return _problem(error)
        return Response(status_code=status.HTTP_204_NO_CONTENT, headers=NO_STORE)

    @router.post(
        "/gear/components/{component_id}/rig",
        operation_id="placeComponent",
        response_model=ComponentDetailOut,
        dependencies=deps,
    )
    def place_component(
        component_id: uuid.UUID, body: RigPlacementIn, actor: Writer
    ) -> ComponentDetailOut | JSONResponse:
        try:
            detail = service().place_in_rig(
                actor,
                component_id,
                body.rig_id,
                body.on,
                expected_version=body.version,
            )
        except Errors as error:
            return _problem(error)
        return _detail(detail)

    @router.post(
        "/gear/components/{component_id}/service",
        operation_id="addServiceEntry",
        response_model=ServiceOut,
        responses={201: {"model": ServiceOut}},
        dependencies=deps,
    )
    def add_service(
        component_id: uuid.UUID, body: ServiceIn, actor: Writer, response: Response
    ) -> ServiceOut | JSONResponse:
        try:
            entry, created = service().add_service(
                actor,
                component_id,
                body.client_key,
                body.model_dump(exclude={"client_key"}),
            )
        except Errors as error:
            return _problem(error)
        response.status_code = 201 if created else 200
        return _service(entry)

    @router.delete(
        "/gear/components/{component_id}/service/{entry_id}",
        operation_id="deleteServiceEntry",
        status_code=status.HTTP_204_NO_CONTENT,
        dependencies=deps,
    )
    def delete_service(
        component_id: uuid.UUID, entry_id: uuid.UUID, actor: Writer
    ) -> Response:
        try:
            service().delete_service(actor, component_id, entry_id)
        except Errors as error:
            return _problem(error)
        return Response(status_code=status.HTTP_204_NO_CONTENT, headers=NO_STORE)

    # -- rigs -----------------------------------------------------------------------

    @router.get(
        "/gear/rigs",
        operation_id="listRigs",
        response_model=list[RigOut],
        dependencies=deps,
    )
    def list_rigs(actor: Reader) -> list[RigOut]:
        return [_rig(s.rig, s.components) for s in service().list_rigs(actor)]

    @router.post(
        "/gear/rigs",
        operation_id="createRig",
        response_model=RigOut,
        responses={201: {"model": RigOut}},
        dependencies=deps,
    )
    def create_rig(
        body: RigIn, actor: Writer, response: Response
    ) -> RigOut | JSONResponse:
        try:
            rig, created = service().create_rig(actor, body.client_key, body.label)
        except Errors as error:
            return _problem(error)
        response.status_code = 201 if created else 200
        return _rig(rig, [])

    @router.patch(
        "/gear/rigs/{rig_id}",
        operation_id="updateRig",
        response_model=RigOut,
        dependencies=deps,
    )
    def update_rig(
        rig_id: uuid.UUID, body: RigUpdateIn, actor: Writer
    ) -> RigOut | JSONResponse:
        try:
            rig = service().update_rig(
                actor,
                rig_id,
                label=body.label,
                archived=body.archived,
                expected_version=body.version,
            )
            summary = next(
                (s for s in service().list_rigs(actor) if s.rig.id == rig.id), None
            )
        except Errors as error:
            return _problem(error)
        return _rig(rig, summary.components if summary else [])

    return router
