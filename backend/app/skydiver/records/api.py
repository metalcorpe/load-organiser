"""HTTP adapter for personal export and empty-record restore (#155). Owner-only.

`GET /records/export` returns the owner's records as a private attachment (format
v1; see docs/product/export-format.md). `POST /records/restore/check` validates an
archive and previews counts and eligibility without writing. `POST /records/restore`
restores it into empty records; it needs a confirmed email and a fresh password
in `x-organiser-confirm-password` (sent only by the web server, like the bearer).
Archive bodies are raw `application/json`, at most 8 MiB, read with a byte cap.

Errors: 400 `archive_malformed` / `archive_version_unsupported`, 413
`archive_too_large`, 422 `archive_invalid` (with a content-free `problem`) or
`password_confirmation_failed`, 409 `records_not_empty`, 429 `too_many_attempts`.
"""

from collections.abc import Callable
from datetime import UTC, datetime, timedelta
from typing import Annotated, Any, Literal

from fastapi import APIRouter, Depends, Request, Response, status
from fastapi.concurrency import run_in_threadpool
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from app.skydiver.access.http import AccessDependencies, bearer_secret
from app.skydiver.access.policy import Actor
from app.skydiver.identity.policy import ThrottleRule
from app.skydiver.identity.service import (
    ConfirmationFailed,
    IdentityService,
    NotAuthenticated,
    Throttled,
)
from app.skydiver.records.policy import RAW_MAX_BYTES, ArchiveInvalid
from app.skydiver.records.service import (
    ArchiveMalformed,
    ArchiveTooLarge,
    ArchiveUnsupported,
    RecordsNotEmpty,
    RecordsService,
)

PREFIX = "/api/skydiver/v1"
NO_STORE = {"cache-control": "no-store"}
PASSWORD_HEADER = "x-organiser-confirm-password"

EXPORT_RULE = ThrottleRule("records_export", 1, timedelta(minutes=5))
CHECK_RULE = ThrottleRule("records_check", 10, timedelta(hours=1))
RESTORE_RULE = ThrottleRule("records_restore", 3, timedelta(days=1))


class Problem(BaseModel):
    detail: str
    problem: str | None = Field(
        default=None, description="For archive_invalid: position and rule, no content."
    )


class ReceiptOut(BaseModel):
    fingerprint: str
    restored_at: datetime
    counts: dict[str, int]


class RecordsOut(BaseModel):
    counts: dict[str, int] = Field(description="Records a restore manages, by kind.")
    empty: bool
    last_restore: ReceiptOut | None


class ArchiveCountsOut(BaseModel):
    places: int
    components: int
    rigs: int
    service_entries: int
    jumps: int
    baseline: int
    saved_listings: int
    plans: int


class RestoreCheckOut(BaseModel):
    fingerprint: str = Field(description="SHA-256 of the exact file.")
    exported_at: datetime
    counts: ArchiveCountsOut
    venues_to_private_places: int
    plan_links_dropped: int
    saved_not_restorable: list[str] = Field(
        description="Public titles of saved listings that are no longer published."
    )
    eligible: bool
    reason: Literal["records_not_empty", "already_restored"] | None
    already_restored_at: datetime | None


class RestoreOut(BaseModel):
    outcome: Literal["restored", "already_restored"]
    fingerprint: str
    restored_at: datetime
    counts: dict[str, int]


_ERRORS: dict[int | str, dict[str, Any]] = {
    code: {"model": Problem} for code in (400, 401, 403, 409, 413, 422, 429)
}
_ARCHIVE_BODY: dict[str, Any] = {
    "requestBody": {
        "required": True,
        "content": {"application/json": {"schema": {"type": "object"}}},
        "description": "The raw archive file (format v1), at most 8 MiB.",
    }
}


class _BodyTooLarge(Exception):
    pass


async def _raw(request: Request) -> bytes:
    """The request body, refused beyond the cap while it is still streaming."""
    if not request.headers.get("content-type", "").startswith("application/json"):
        raise ArchiveMalformed()
    declared = request.headers.get("content-length")
    if declared is not None and (
        not declared.isdigit() or int(declared) > RAW_MAX_BYTES
    ):
        raise _BodyTooLarge()
    body = bytearray()
    async for chunk in request.stream():
        body += chunk
        if len(body) > RAW_MAX_BYTES:
            raise _BodyTooLarge()
    return bytes(body)


def _problem(error: Exception) -> JSONResponse:
    headers = dict(NO_STORE)
    body: dict[str, Any] = {"detail": getattr(error, "code", "")}
    if isinstance(error, ArchiveMalformed | ArchiveUnsupported):
        code = status.HTTP_400_BAD_REQUEST
    elif isinstance(error, ArchiveTooLarge | _BodyTooLarge):
        code, body = status.HTTP_413_CONTENT_TOO_LARGE, {"detail": "archive_too_large"}
    elif isinstance(error, ArchiveInvalid):
        code, body["problem"] = status.HTTP_422_UNPROCESSABLE_CONTENT, error.problem
    elif isinstance(error, ConfirmationFailed):
        code = status.HTTP_422_UNPROCESSABLE_CONTENT
    elif isinstance(error, RecordsNotEmpty):
        code = status.HTTP_409_CONFLICT
    elif isinstance(error, NotAuthenticated):
        code, body = status.HTTP_401_UNAUTHORIZED, {"detail": "not_authenticated"}
    elif isinstance(error, Throttled):
        code = status.HTTP_429_TOO_MANY_REQUESTS
        headers["retry-after"] = str(error.retry_after_seconds)
    else:
        raise error
    return JSONResponse(body, status_code=code, headers=headers)


def create_router(
    *,
    service: Callable[[], RecordsService],
    identity: Callable[[], IdentityService],
    access: AccessDependencies,
    client_ip: Callable[[Request], str],
) -> APIRouter:
    router = APIRouter(prefix=PREFIX, tags=["skydiver-records"], responses=_ERRORS)

    def no_store(response: Response) -> None:
        response.headers["cache-control"] = "no-store"

    deps = [Depends(no_store)]
    Reader = Annotated[Actor, Depends(access.actor)]
    Writer = Annotated[Actor, Depends(access.verified_actor)]
    Errors = (
        ArchiveMalformed,
        ArchiveUnsupported,
        ArchiveTooLarge,
        _BodyTooLarge,
        ArchiveInvalid,
        ConfirmationFailed,
        RecordsNotEmpty,
        NotAuthenticated,
        Throttled,
    )

    def consume(rule: ThrottleRule, actor: Actor) -> None:
        identity().consume(rule=rule, key=str(actor.account_id))

    @router.get(
        "/records",
        operation_id="getRecords",
        response_model=RecordsOut,
        dependencies=deps,
    )
    def get_records(actor: Reader) -> RecordsOut:
        s = service().summary(actor)
        last = s.last_restore
        return RecordsOut(
            counts=s.counts,
            empty=s.empty,
            last_restore=ReceiptOut(
                fingerprint=last.fingerprint,
                restored_at=last.restored_at,
                counts={k: int(v) for k, v in last.counts.items()},
            )
            if last
            else None,
        )

    @router.get(
        "/records/export",
        operation_id="exportRecords",
        responses={200: {"content": {"application/json": {}}}},
    )
    def export_records(actor: Reader) -> Response:
        try:
            consume(EXPORT_RULE, actor)
            data = service().export(actor)
        except Errors as error:
            return _problem(error)
        day = (
            datetime.now(UTC).date().isoformat()
        )  # name only; the file holds the instant
        return Response(
            content=data,
            media_type="application/json",
            headers={
                **NO_STORE,
                "content-disposition": (
                    f'attachment; filename="load-organiser-records-{day}.json"'
                ),
                "x-content-type-options": "nosniff",
            },
        )

    @router.post(
        "/records/restore/check",
        operation_id="checkRestore",
        response_model=RestoreCheckOut,
        dependencies=deps,
        openapi_extra=_ARCHIVE_BODY,
    )
    async def check_restore(
        request: Request, actor: Reader
    ) -> RestoreCheckOut | JSONResponse:
        try:
            raw = await _raw(request)
            await run_in_threadpool(consume, CHECK_RULE, actor)
            c = await run_in_threadpool(service().check, actor, raw)
        except Errors as error:
            return _problem(error)
        return RestoreCheckOut(
            fingerprint=c.fingerprint,
            exported_at=c.exported_at,
            counts=ArchiveCountsOut(**vars(c.counts)),
            venues_to_private_places=c.detached.venues_to_private_places,
            plan_links_dropped=c.detached.plan_links_dropped,
            saved_not_restorable=c.detached.saved_not_restorable,
            eligible=c.eligible,
            reason=c.reason,  # type: ignore[arg-type]
            already_restored_at=c.already_restored_at,
        )

    @router.post(
        "/records/restore",
        operation_id="restoreRecords",
        response_model=RestoreOut,
        dependencies=deps,
        openapi_extra=_ARCHIVE_BODY,
    )
    async def restore_records(
        request: Request,
        actor: Writer,
        secret: Annotated[str, Depends(bearer_secret)],
    ) -> RestoreOut | JSONResponse:
        password = request.headers.get(PASSWORD_HEADER, "")
        ip = client_ip(request)
        try:
            raw = await _raw(request)
            if not password:
                raise ConfirmationFailed()
            await run_in_threadpool(
                lambda: identity().confirm_password(
                    secret=secret, password=password, client_ip=ip
                )
            )
            result = await run_in_threadpool(
                lambda: service().restore(
                    actor, raw, before_write=lambda: consume(RESTORE_RULE, actor)
                )
            )
        except Errors as error:
            return _problem(error)
        return RestoreOut(
            outcome=result.outcome,  # type: ignore[arg-type]
            fingerprint=result.fingerprint,
            restored_at=result.restored_at,
            counts={k: int(v) for k, v in result.counts.items()},
        )

    return router
