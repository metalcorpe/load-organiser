"""#146 authorization policy: plain values, no database or settings."""

import subprocess
import sys
import uuid
from pathlib import Path

import pytest

from app.skydiver.access.policy import (
    Actor,
    Audience,
    Relationship,
    Role,
    actor_roles,
    may_view,
    owns,
)

BACKEND_DIR = Path(__file__).resolve().parents[1]
OWNER = uuid.uuid4()


def actor(person_id: uuid.UUID | None = None, *roles: Role) -> Actor:
    return Actor(
        account_id=uuid.uuid4(),
        person_id=person_id or uuid.uuid4(),
        email_verified=True,
        roles=frozenset(roles),
    )


FOLLOWER = Relationship(approved_follower=True)
BLOCKED = Relationship(blocked_either_way=True)
FOLLOWER_BLOCKED = Relationship(approved_follower=True, blocked_either_way=True)


@pytest.mark.parametrize(
    ("viewer", "audience", "active", "relationship", "visible"),
    [
        # The owner always sees their own item, whatever its state.
        (actor(OWNER), Audience.PRIVATE, True, Relationship(), True),
        (actor(OWNER), Audience.PUBLIC, False, Relationship(), True),
        # Private: nobody else, including reviewers and followers.
        (None, Audience.PRIVATE, True, Relationship(), False),
        (actor(), Audience.PRIVATE, True, FOLLOWER, False),
        (actor(None, Role.REVIEWER), Audience.PRIVATE, True, Relationship(), False),
        # Followers: approved followers only, and not across a block.
        (None, Audience.FOLLOWERS, True, Relationship(), False),
        (actor(), Audience.FOLLOWERS, True, Relationship(), False),
        (actor(), Audience.FOLLOWERS, True, FOLLOWER, True),
        (actor(), Audience.FOLLOWERS, True, FOLLOWER_BLOCKED, False),
        (actor(None, Role.REVIEWER), Audience.FOLLOWERS, True, Relationship(), False),
        # Public: anonymous and unrelated viewers; a block denies that viewer only.
        (None, Audience.PUBLIC, True, Relationship(), True),
        (actor(), Audience.PUBLIC, True, Relationship(), True),
        (actor(), Audience.PUBLIC, True, BLOCKED, False),
        # Withdrawn/moderated items are hidden from everyone but the owner.
        (None, Audience.PUBLIC, False, Relationship(), False),
        (actor(), Audience.FOLLOWERS, False, FOLLOWER, False),
    ],
)
def test_may_view(
    viewer: Actor | None,
    audience: Audience,
    active: bool,
    relationship: Relationship,
    visible: bool,
) -> None:
    assert (
        may_view(
            viewer,
            owner_person_id=OWNER,
            audience=audience,
            active=active,
            relationship=relationship,
        )
        is visible
    )


def test_ownership_is_by_person_identity() -> None:
    assert owns(actor(OWNER), OWNER)
    assert not owns(actor(), OWNER)
    assert not owns(None, OWNER)


def test_unknown_stored_roles_grant_nothing() -> None:
    assert actor_roles(frozenset({"reviewer", "superuser", "admin"})) == {Role.REVIEWER}
    assert actor_roles(frozenset()) == frozenset()


def test_access_policy_imports_no_framework_or_persistence(tmp_path: Path) -> None:
    # Run from an empty directory so a stray "../.env" can never be read.
    code = (
        "import sys, app.skydiver.access.policy;"
        "bad=[m for m in sys.modules if m.split('.')[0] in "
        "('fastapi','sqlalchemy','sqlmodel','pydantic','starlette')"
        " or m in ('app.core.config','app.core.db','app.models')];"
        "assert not bad, bad"
    )
    result = subprocess.run(
        [sys.executable, "-c", code],
        cwd=tmp_path,
        env={"PYTHONPATH": str(BACKEND_DIR), "PATH": ""},
        capture_output=True,
        text=True,
        check=False,
    )
    assert result.returncode == 0, result.stderr
