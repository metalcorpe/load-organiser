"""HTTP adapter for importing a logbook from a spreadsheet (CSV). Owner-only.

`POST /jumps/import/check` reads a raw `text/csv` body (at most 1 MiB) and
previews what an import would do without writing. `POST /jumps/import` imports
it in one transaction and needs a confirmed email. Options and column choices
travel as query parameters, so the body stays the exact file: `date_order`
(dmy, mdy or ymd), `unit` (ft or m), `country` (ISO code for places that are not
listed) and `col_<field>` (a 0-based column index, or `none`; omitted means
detected from the headings). `expected` may carry the checked fingerprint: an
import of a different file or with other choices then answers `import_changed`.

`GET /jumps/imports` lists the person's imports; `POST /jumps/imports/{id}/undo`
removes what one created. Another person's import answers 404 like a missing one.

Errors: 400 `file_unreadable` / `header_required`, 413 `file_too_large`, 422 for
rules about the whole file (`too_many_rows`, `date_column_required`,
`country_required` with the place names, ...), 409 `jump_limit_reached`,
`place_limit_reached`, `already_undone`, `import_changed`, `import_busy`, 429
`too_many_attempts`.
"""

import uuid
from collections.abc import Callable
from datetime import date, datetime, timedelta
from typing import Annotated, Any, Literal

from fastapi import APIRouter, Depends, Query, Request, Response, status
from fastapi.concurrency import run_in_threadpool
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from app.skydiver.access.http import AccessDependencies
from app.skydiver.access.policy import Actor
from app.skydiver.directory import policy as directory
from app.skydiver.directory.policy import DirectoryRuleError
from app.skydiver.identity.policy import ThrottleRule
from app.skydiver.identity.service import IdentityService, Throttled
from app.skydiver.imports import policy
from app.skydiver.imports.policy import DateOrder, ImportRefused, Options
from app.skydiver.imports.service import (
    AlreadyUndone,
    ImportBusy,
    ImportChanged,
    ImportRecord,
    ImportService,
    LimitReached,
    NotFound,
    PlaceLimitReached,
)
from app.skydiver.logbook.policy import AltitudeUnit

PREFIX = "/api/skydiver/v1"
NO_STORE = {"cache-control": "no-store"}

CHECK_RULE = ThrottleRule("jumps_import_check", 60, timedelta(hours=1))
IMPORT_RULE = ThrottleRule("jumps_import", 10, timedelta(days=1))

JumpTypeName = Literal[
    "unspecified", "belly", "freefly", "angle", "wingsuit", "canopy", "crw",
    "accuracy", "hop_and_pop", "tandem", "training", "other",
]  # fmt: skip
Column = Annotated[str | None, Query(pattern=r"^(none|\d{1,3})$")]


class Problem(BaseModel):
    detail: str
    names: list[str] | None = Field(
        default=None,
        description="For country_required: the place names not in the directory.",
    )


class ColumnsOut(BaseModel):
    date: int | None
    number: int | None
    place: int | None
    type: int | None
    altitude: int | None
    freefall: int | None
    notes: int | None


class RowProblemOut(BaseModel):
    row: int = Field(description="1-based data row (the row under the headings is 1).")
    code: str


class SampleRowOut(BaseModel):
    row: int
    jumped_on: date
    jump_number: int | None
    place: str
    place_kind: Literal["venue", "place", "new_place"]
    jump_type: JumpTypeName
    exit_altitude: int | None
    altitude_unit: Literal["ft", "m"] | None
    freefall_seconds: int | None
    notes: str | None


class ImportCheckOut(BaseModel):
    fingerprint: str = Field(description="Of the exact file and the choices used.")
    encoding: Literal["utf-8", "utf-16", "windows-1252"]
    headings: list[str]
    columns: ColumnsOut
    rows_total: int
    rows_ok: int
    new_places: list[str]
    problems: list[RowProblemOut] = Field(description="The first 50, by row.")
    problems_total: int
    sample: list[SampleRowOut] = Field(description="The first 10 rows to be saved.")
    room: int = Field(description="Jumps that still fit under the 2,000 limit.")
    already_imported_at: datetime | None


class ImportOut(BaseModel):
    id: uuid.UUID
    created_at: datetime
    counts: dict[str, int]
    undone_at: datetime | None


class ImportResultOut(BaseModel):
    outcome: Literal["imported", "already_imported"]
    item: ImportOut


class UndoIn(BaseModel):
    confirm: bool = Field(
        description="Must be true: every jump of the import is deleted, even if edited."
    )


_ERRORS: dict[int | str, dict[str, Any]] = {
    code: {"model": Problem} for code in (400, 401, 403, 404, 409, 413, 422, 429)
}
_CSV_BODY: dict[str, Any] = {
    "requestBody": {
        "required": True,
        "content": {"text/csv": {"schema": {"type": "string"}}},
        "description": "The raw spreadsheet file (CSV), at most 1 MiB.",
    }
}


class _BodyTooLarge(Exception):
    pass


class _NotCsv(Exception):
    pass


async def _raw(request: Request) -> bytes:
    """The request body, refused beyond the cap while it is still streaming."""
    kind = request.headers.get("content-type", "").split(";")[0].strip().lower()
    if kind not in ("text/csv", "application/octet-stream"):
        raise _NotCsv()
    declared = request.headers.get("content-length")
    if declared is not None and (
        not declared.isdigit() or int(declared) > policy.RAW_MAX_BYTES
    ):
        raise _BodyTooLarge()
    body = bytearray()
    async for chunk in request.stream():
        body += chunk
        if len(body) > policy.RAW_MAX_BYTES:
            raise _BodyTooLarge()
    return bytes(body)


def _record(record: ImportRecord) -> ImportOut:
    return ImportOut(
        id=record.id,
        created_at=record.created_at,
        counts=record.counts,
        undone_at=record.undone_at,
    )


def _problem(error: Exception) -> JSONResponse:
    headers = dict(NO_STORE)
    body: dict[str, Any] = {"detail": getattr(error, "code", "")}
    if isinstance(error, _NotCsv):
        code, body = status.HTTP_400_BAD_REQUEST, {"detail": "file_unreadable"}
    elif isinstance(error, _BodyTooLarge):
        code, body = status.HTTP_413_CONTENT_TOO_LARGE, {"detail": "file_too_large"}
    elif isinstance(error, ImportRefused):
        if error.code == "file_too_large":
            code = status.HTTP_413_CONTENT_TOO_LARGE
        elif error.code in ("file_unreadable", "header_required"):
            code = status.HTTP_400_BAD_REQUEST
        else:
            code = status.HTTP_422_UNPROCESSABLE_CONTENT
        if error.names:
            body["names"] = error.names[:50]
    elif isinstance(error, DirectoryRuleError):
        code = status.HTTP_422_UNPROCESSABLE_CONTENT
    elif isinstance(error, NotFound):
        code, body = status.HTTP_404_NOT_FOUND, {"detail": "not_found"}
    elif isinstance(
        error,
        LimitReached | PlaceLimitReached | AlreadyUndone | ImportChanged | ImportBusy,
    ):
        code = status.HTTP_409_CONFLICT
    elif isinstance(error, Throttled):
        code = status.HTTP_429_TOO_MANY_REQUESTS
        headers["retry-after"] = str(error.retry_after_seconds)
    else:
        raise error
    return JSONResponse(body, status_code=code, headers=headers)


def create_router(
    *,
    service: Callable[[], ImportService],
    identity: Callable[[], IdentityService],
    access: AccessDependencies,
) -> APIRouter:
    router = APIRouter(prefix=PREFIX, tags=["skydiver-imports"], responses=_ERRORS)

    def no_store(response: Response) -> None:
        response.headers["cache-control"] = "no-store"

    deps = [Depends(no_store)]
    Reader = Annotated[Actor, Depends(access.actor)]
    Writer = Annotated[Actor, Depends(access.verified_actor)]
    Errors = (
        _NotCsv,
        _BodyTooLarge,
        ImportRefused,
        DirectoryRuleError,
        NotFound,
        LimitReached,
        PlaceLimitReached,
        AlreadyUndone,
        ImportChanged,
        ImportBusy,
        Throttled,
    )

    def consume(rule: ThrottleRule, actor: Actor) -> None:
        identity().consume(rule=rule, key=str(actor.account_id))

    def options(
        date_order: Literal["dmy", "mdy", "ymd"] = "dmy",
        unit: Literal["ft", "m"] = "ft",
        country: Annotated[str | None, Query(pattern=r"^[A-Za-z]{2}$")] = None,
        col_date: Column = None,
        col_number: Column = None,
        col_place: Column = None,
        col_type: Column = None,
        col_altitude: Column = None,
        col_freefall: Column = None,
        col_notes: Column = None,
    ) -> Options:
        given = {
            "date": col_date, "number": col_number, "place": col_place,
            "type": col_type, "altitude": col_altitude, "freefall": col_freefall,
            "notes": col_notes,
        }  # fmt: skip
        return Options(
            date_order=DateOrder(date_order),
            unit=AltitudeUnit(unit),
            country=country,
            mapping={
                name: None if value == "none" else int(value)
                for name, value in given.items()
                if value is not None
            },
        )

    Choices = Annotated[Options, Depends(options)]

    def checked(choices: Options) -> Options:
        """The country as the directory stores it (DirectoryRuleError otherwise)."""
        if choices.country is None:
            return choices
        return Options(
            date_order=choices.date_order,
            unit=choices.unit,
            country=directory.country_code(choices.country),
            mapping=choices.mapping,
        )

    @router.post(
        "/jumps/import/check",
        operation_id="checkJumpImport",
        response_model=ImportCheckOut,
        dependencies=deps,
        openapi_extra=_CSV_BODY,
    )
    async def check_import(
        request: Request, actor: Reader, choices: Choices
    ) -> ImportCheckOut | JSONResponse:
        try:
            raw = await _raw(request)
            await run_in_threadpool(consume, CHECK_RULE, actor)
            p = await run_in_threadpool(service().check, actor, raw, checked(choices))
        except Errors as error:
            return _problem(error)
        return ImportCheckOut(
            fingerprint=p.fingerprint,
            encoding=p.encoding,  # type: ignore[arg-type]
            headings=p.headings,
            columns=ColumnsOut(**p.columns),
            rows_total=p.rows_total,
            rows_ok=p.rows_ok,
            new_places=p.new_places,
            problems=[RowProblemOut(row=x.row, code=x.code) for x in p.problems],
            problems_total=p.problems_total,
            sample=[SampleRowOut(**vars(s)) for s in p.sample],
            room=p.room,
            already_imported_at=p.already_imported_at,
        )

    @router.post(
        "/jumps/import",
        operation_id="importJumps",
        response_model=ImportResultOut,
        dependencies=deps,
        openapi_extra=_CSV_BODY,
    )
    async def import_jumps(
        request: Request,
        actor: Writer,
        choices: Choices,
        expected: Annotated[str | None, Query(pattern=r"^[0-9a-f]{64}$")] = None,
    ) -> ImportResultOut | JSONResponse:
        try:
            raw = await _raw(request)
            result = await run_in_threadpool(
                lambda: service().run(
                    actor,
                    raw,
                    checked(choices),
                    expected=expected,
                    before_write=lambda: consume(IMPORT_RULE, actor),
                )
            )
        except Errors as error:
            return _problem(error)
        return ImportResultOut(
            outcome=result.outcome,  # type: ignore[arg-type]
            item=_record(result.record),
        )

    @router.get(
        "/jumps/imports",
        operation_id="listJumpImports",
        response_model=list[ImportOut],
        dependencies=deps,
    )
    def list_imports(actor: Reader) -> list[ImportOut]:
        return [_record(r) for r in service().imports(actor)]

    @router.post(
        "/jumps/imports/{import_id}/undo",
        operation_id="undoJumpImport",
        response_model=ImportOut,
        dependencies=deps,
    )
    def undo_import(
        import_id: uuid.UUID, body: UndoIn, actor: Writer
    ) -> ImportOut | JSONResponse:
        try:
            if not body.confirm:
                raise ImportRefused("confirm_required")
            return _record(service().undo(actor, import_id))
        except Errors as error:
            return _problem(error)

    return router
