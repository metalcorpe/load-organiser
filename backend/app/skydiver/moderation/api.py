"""HTTP adapter for suggestions, corrections and reports (#151).

- POST /submissions                      signed-in, confirmed accounts; idempotent key
- GET  /submissions                      the viewer's own submissions and their status
- GET  /directory/submissions            reviewer queue (no submitter identity)
- POST /directory/submissions/{id}/resolve
"""

import uuid
from collections.abc import Callable
from datetime import datetime
from typing import Annotated, Any, Literal

from fastapi import APIRouter, Depends, Query, Response, status
from fastapi.responses import JSONResponse
from pydantic import BaseModel, Field

from app.skydiver.access.http import AccessDependencies
from app.skydiver.access.policy import Actor, Role
from app.skydiver.directory.policy import DirectoryRuleError
from app.skydiver.directory.service import EditConflict
from app.skydiver.moderation.service import (
    KeyReused,
    LimitReached,
    NotFound,
    Paused,
    Submission,
    SubmissionService,
)

PREFIX = "/api/skydiver/v1"
NO_STORE = {"cache-control": "no-store"}

KindName = Literal["suggest_venue", "suggest_listing", "correction", "report"]
TargetName = Literal["venue", "provider", "opportunity"]
StatusName = Literal["open", "accepted", "declined"]


class Problem(BaseModel):
    detail: str


class SubmissionIn(BaseModel):
    client_key: uuid.UUID = Field(
        description="Generated once per submission; a retry with the same key and "
        "content returns the original instead of a duplicate."
    )
    kind: KindName
    target_kind: TargetName | None = None
    target_id: uuid.UUID | None = None
    message: Annotated[str, Field(min_length=1, max_length=4000)]
    source_url: Annotated[str, Field(max_length=2048)] | None = None


class OwnSubmissionOut(BaseModel):
    """What the submitter sees: their content, the status and the outcome note."""

    id: uuid.UUID
    kind: KindName
    target_kind: TargetName | None
    target_id: uuid.UUID | None
    message: str
    source_url: str | None
    status: StatusName
    resolution_note: str | None
    resolved_at: datetime | None
    created_at: datetime


class ReviewSubmissionOut(OwnSubmissionOut):
    """What a reviewer sees. Deliberately carries no submitter identity."""

    version: int


class ReviewSubmissionPageOut(BaseModel):
    items: list[ReviewSubmissionOut]
    next_cursor: str | None


class ResolveIn(BaseModel):
    status: Literal["accepted", "declined"]
    note: Annotated[str, Field(max_length=1000)] | None = Field(
        default=None, description="Shown to the submitter."
    )
    version: Annotated[int, Field(ge=1)] | None = None


_ERRORS: dict[int | str, dict[str, Any]] = {
    code: {"model": Problem} for code in (401, 403, 404, 409, 422, 503)
}


def _fields(item: Submission) -> dict[str, Any]:
    return {
        "id": item.id,
        "kind": item.kind.value,
        "target_kind": item.target_kind.value if item.target_kind else None,
        "target_id": item.target_id,
        "message": item.message,
        "source_url": item.source_url,
        "status": item.status.value,
        "resolution_note": item.resolution_note,
        "resolved_at": item.resolved_at,
        "created_at": item.created_at,
    }


def _problem(error: Exception) -> JSONResponse:
    if isinstance(error, NotFound):
        code, detail = status.HTTP_404_NOT_FOUND, "not_found"
    elif isinstance(error, Paused):
        code, detail = status.HTTP_503_SERVICE_UNAVAILABLE, error.code
    elif isinstance(error, LimitReached | KeyReused | EditConflict):
        code, detail = status.HTTP_409_CONFLICT, error.code
    elif isinstance(error, DirectoryRuleError):
        code, detail = status.HTTP_422_UNPROCESSABLE_CONTENT, error.code
    else:
        raise error
    return JSONResponse({"detail": detail}, status_code=code, headers=NO_STORE)


def create_router(
    *,
    service: Callable[[], SubmissionService],
    access: AccessDependencies,
) -> APIRouter:
    router = APIRouter(prefix=PREFIX, tags=["skydiver-moderation"], responses=_ERRORS)

    def no_store(response: Response) -> None:
        response.headers["cache-control"] = "no-store"

    deps = [Depends(no_store)]
    Reader = Annotated[Actor, Depends(access.actor)]
    Writer = Annotated[Actor, Depends(access.verified_actor)]
    Reviewer = Annotated[Actor, Depends(access.role(Role.REVIEWER))]
    Errors = (
        NotFound,
        Paused,
        LimitReached,
        KeyReused,
        EditConflict,
        DirectoryRuleError,
    )

    @router.post(
        "/submissions",
        operation_id="createSubmission",
        response_model=OwnSubmissionOut,
        responses={201: {"model": OwnSubmissionOut}},
        dependencies=deps,
    )
    def create_submission(
        body: SubmissionIn, actor: Writer, response: Response
    ) -> OwnSubmissionOut | JSONResponse:
        try:
            item, created = service().submit(
                actor, body.client_key, body.model_dump(exclude={"client_key"})
            )
        except Errors as error:
            return _problem(error)
        response.status_code = 201 if created else 200
        return OwnSubmissionOut(**_fields(item))

    @router.get(
        "/submissions",
        operation_id="listOwnSubmissions",
        response_model=list[OwnSubmissionOut],
        dependencies=deps,
    )
    def list_own_submissions(actor: Reader) -> list[OwnSubmissionOut]:
        return [OwnSubmissionOut(**_fields(i)) for i in service().mine(actor)]

    @router.get(
        "/directory/submissions",
        operation_id="listReviewSubmissions",
        response_model=ReviewSubmissionPageOut,
        dependencies=deps,
    )
    def list_review_submissions(
        _actor: Reviewer,
        status: Annotated[str | None, Query(max_length=16)] = "open",
        cursor: Annotated[str | None, Query(max_length=512)] = None,
        limit: Annotated[int | None, Query(ge=1, le=50)] = None,
    ) -> ReviewSubmissionPageOut | JSONResponse:
        try:
            page = service().queue(status=status, cursor=cursor, limit=limit)
        except Errors as error:
            return _problem(error)
        return ReviewSubmissionPageOut(
            items=[
                ReviewSubmissionOut(**_fields(i), version=i.version) for i in page.items
            ],
            next_cursor=page.next_cursor,
        )

    @router.post(
        "/directory/submissions/{submission_id}/resolve",
        operation_id="resolveSubmission",
        response_model=ReviewSubmissionOut,
        dependencies=deps,
    )
    def resolve_submission(
        submission_id: uuid.UUID, body: ResolveIn, actor: Reviewer
    ) -> ReviewSubmissionOut | JSONResponse:
        try:
            item = service().resolve(
                actor,
                submission_id,
                status=body.status,
                note=body.note,
                expected_version=body.version,
            )
        except Errors as error:
            return _problem(error)
        return ReviewSubmissionOut(**_fields(item), version=item.version)

    return router
