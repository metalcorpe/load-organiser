"""Suggestions, corrections and reports about public listings (#151).

A submission never changes a listing by itself: a reviewer reads it and edits the
listing through the maintenance tools. Reviewers do not learn who sent it; the
submitter sees its status and resolution note. Basic abuse limits apply per
account, and the owner can pause intake without affecting anything else.
"""

import hashlib
import json
import uuid
from collections.abc import Callable
from contextlib import AbstractContextManager
from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import StrEnum
from typing import Any, Protocol

from app.skydiver.access.policy import Actor
from app.skydiver.directory import policy as directory_policy
from app.skydiver.directory.policy import DirectoryRuleError as RuleError
from app.skydiver.directory.service import (
    DirectoryService,
    EditConflict,
    decode_cursor,
    encode_cursor,
)
from app.skydiver.directory.service import NotFound as VenueNotFound
from app.skydiver.opportunities.service import NotFound as ListingNotFound
from app.skydiver.opportunities.service import OpportunityService

MESSAGE_MAX = 1000
NOTE_MAX = 280
# Basic abuse limits per account (operating defaults, not measured): a rolling
# daily allowance and a cap on cases still waiting for review.
DAILY_LIMIT = 10
OPEN_LIMIT = 20


class Kind(StrEnum):
    SUGGEST_VENUE = "suggest_venue"
    SUGGEST_LISTING = "suggest_listing"
    CORRECTION = "correction"
    REPORT = "report"
    # About the beta itself, not a listing: never has a target.
    FEEDBACK = "feedback"


class TargetKind(StrEnum):
    VENUE = "venue"
    PROVIDER = "provider"
    OPPORTUNITY = "opportunity"


class Status(StrEnum):
    OPEN = "open"
    ACCEPTED = "accepted"
    DECLINED = "declined"


NEEDS_TARGET = {Kind.CORRECTION, Kind.REPORT}


class NotFound(Exception):
    pass


class Paused(Exception):
    code = "submissions_paused"


class LimitReached(Exception):
    code = "submission_limit_reached"


class KeyReused(Exception):
    """The same client key was sent again with different content."""

    code = "submission_key_reused"


@dataclass(frozen=True)
class Submission:
    id: uuid.UUID
    kind: Kind
    target_kind: TargetKind | None
    target_id: uuid.UUID | None
    message: str
    source_url: str | None
    status: Status
    resolution_note: str | None
    resolved_at: datetime | None
    created_at: datetime
    version: int
    fingerprint: str


@dataclass(frozen=True)
class SubmissionPage:
    items: list[Submission]
    next_cursor: str | None


class SubmissionStore(Protocol):
    def by_key(self, actor: Actor, client_key: uuid.UUID) -> Submission | None: ...
    def count_since(self, actor: Actor, since: datetime) -> int: ...
    def count_open(self, actor: Actor) -> int: ...
    def insert(
        self, actor: Actor, client_key: uuid.UUID, values: dict[str, Any], now: datetime
    ) -> uuid.UUID: ...
    def get(self, submission_id: uuid.UUID) -> Submission | None: ...
    def mine(self, actor: Actor, limit: int) -> list[Submission]: ...
    def queue(
        self,
        status: Status | None,
        after: tuple[str, uuid.UUID] | None,
        limit: int,
    ) -> list[Submission]: ...
    def resolve(
        self,
        submission_id: uuid.UUID,
        *,
        status: Status,
        note: str | None,
        actor: Actor,
        now: datetime,
        expected_version: int,
    ) -> None:
        """Compare-and-swap; raises EditConflict if the version moved."""
        ...


StoreFactory = Callable[[], AbstractContextManager[SubmissionStore]]
Clock = Callable[[], datetime]


def fingerprint(values: dict[str, Any]) -> str:
    """Stable digest of the validated content, to tell a retry from a reuse."""
    canonical = json.dumps(
        {k: str(v) if v is not None else None for k, v in sorted(values.items())}
    )
    return hashlib.sha256(canonical.encode()).hexdigest()


class SubmissionService:
    def __init__(
        self,
        *,
        stores: StoreFactory,
        clock: Clock,
        directory: DirectoryService,
        opportunities: OpportunityService,
        is_open: Callable[[], bool],
    ) -> None:
        self._stores = stores
        self._clock = clock
        self._directory = directory
        self._opportunities = opportunities
        self._is_open = is_open

    def submit(
        self, actor: Actor, client_key: uuid.UUID, fields: dict[str, Any]
    ) -> tuple[Submission, bool]:
        """Idempotent by `client_key`: a retry returns the original (created=False)."""
        values = self._validated(fields)
        digest = fingerprint(values)
        now = self._clock()
        with self._stores() as store:
            existing = store.by_key(actor, client_key)
            if existing is not None:
                if existing.fingerprint != digest:
                    raise KeyReused()
                return existing, False
            if not self._is_open():
                raise Paused()
            # Limits are read, not locked: parallel requests from one account can
            # overshoot by their number, which is acceptable for an abuse limit.
            if store.count_open(actor) >= OPEN_LIMIT or (
                store.count_since(actor, now - timedelta(days=1)) >= DAILY_LIMIT
            ):
                raise LimitReached()
            submission_id = store.insert(
                actor, client_key, values | {"fingerprint": digest}, now
            )
            created = store.get(submission_id)
        assert created is not None
        return created, True

    def mine(self, actor: Actor) -> list[Submission]:
        with self._stores() as store:
            return store.mine(actor, 100)

    def queue(
        self,
        *,
        status: str | None = Status.OPEN.value,
        cursor: str | None = None,
        limit: int | None = None,
    ) -> SubmissionPage:
        state = _parse(Status, status, "status") if status else None
        size = directory_policy.page_size(limit)
        after = decode_cursor(cursor) if cursor else None
        if after is not None:
            try:
                datetime.fromisoformat(after[0])
            except ValueError:
                raise RuleError("cursor_invalid") from None
        with self._stores() as store:
            rows = store.queue(state, after, size + 1)
        next_cursor = None
        if len(rows) > size:
            last = rows[size - 1]
            next_cursor = encode_cursor(last.created_at.isoformat(), last.id)
        return SubmissionPage(rows[:size], next_cursor)

    def resolve(
        self,
        actor: Actor,
        submission_id: uuid.UUID,
        *,
        status: str,
        note: str | None,
        expected_version: int | None,
    ) -> Submission:
        outcome = _parse(Status, status, "status")
        if outcome is None or outcome is Status.OPEN:
            raise RuleError("status_invalid")
        clean_note = directory_policy.optional_text(
            note, field="note", maximum=NOTE_MAX
        )
        now = self._clock()
        with self._stores() as store:
            current = store.get(submission_id)
            if current is None:
                raise NotFound()
            if expected_version is not None and expected_version != current.version:
                raise EditConflict()
            if current.status is not Status.OPEN:
                raise RuleError("submission_resolved")
            store.resolve(
                submission_id,
                status=outcome,
                note=clean_note,
                actor=actor,
                now=now,
                expected_version=current.version,
            )
            resolved = store.get(submission_id)
        assert resolved is not None
        return resolved

    # -- helpers ------------------------------------------------------------------

    def _validated(self, raw: dict[str, Any]) -> dict[str, Any]:
        kind = _parse(Kind, raw.get("kind"), "kind")
        assert kind is not None
        target_kind = _parse(TargetKind, raw.get("target_kind"), "target_kind")
        target_id = raw.get("target_id")
        if (target_kind is None) != (target_id is None):
            raise RuleError("target_incomplete")
        if kind in NEEDS_TARGET and target_id is None:
            raise RuleError("target_required")
        if kind is Kind.FEEDBACK and target_id is not None:
            raise RuleError("target_not_allowed")
        if target_kind is not None and target_id is not None:
            target_id = self._public_target(target_kind, target_id)
        message = directory_policy.clean_text(
            raw.get("message") or "", field="message", maximum=MESSAGE_MAX
        )
        source = raw.get("source_url")
        return {
            "kind": kind.value,
            "target_kind": target_kind.value if target_kind else None,
            "target_id": target_id,
            "message": message,
            "source_url": directory_policy.source_url(source) if source else None,
        }

    def _public_target(self, kind: TargetKind, target_id: uuid.UUID) -> uuid.UUID:
        """Only public records can be referenced; the current ID is stored."""
        try:
            if kind is TargetKind.VENUE:
                return self._directory.public_venue(target_id).venue.id
            if kind is TargetKind.PROVIDER:
                return self._opportunities.public_provider(target_id).value.id
            return self._opportunities.public_opportunity(target_id).value.row.id
        except VenueNotFound, ListingNotFound:
            raise RuleError("target_unavailable") from None


def _parse[E: StrEnum](kind: type[E], value: Any, field: str) -> E | None:
    if value is None or value == "":
        return None
    try:
        return kind(value)
    except ValueError:
        raise RuleError(f"{field}_invalid") from None
