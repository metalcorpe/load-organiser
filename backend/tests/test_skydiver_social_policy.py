"""#156 profile visibility and follow rules as plain values (no database)."""

import pytest

from app.skydiver.directory.policy import DirectoryRuleError
from app.skydiver.social import policy
from app.skydiver.social.policy import Facts

ANON = Facts()
STRANGER = Facts(signed_in=True)
FOLLOWER = Facts(signed_in=True, approved_follower=True)
BLOCKED = Facts(signed_in=True, blocked_either_way=True)
BLOCKED_FOLLOWER = Facts(
    signed_in=True, approved_follower=True, blocked_either_way=True
)
OWNER = Facts(is_owner=True, signed_in=True)


@pytest.mark.parametrize(
    ("discoverable", "hidden", "facts", "visible"),
    [
        (True, False, ANON, True),
        (True, False, STRANGER, True),
        (True, False, BLOCKED, False),  # signed in and blocked: not even public
        (False, False, ANON, False),
        (False, False, STRANGER, False),
        (False, False, FOLLOWER, True),  # approved followers keep access
        (False, False, BLOCKED_FOLLOWER, False),
        (True, True, ANON, False),  # hidden by a reviewer
        (True, True, FOLLOWER, False),
        (False, True, OWNER, True),  # the owner always sees their own
    ],
)
def test_profile_visibility(
    discoverable: bool, hidden: bool, facts: Facts, visible: bool
) -> None:
    assert (
        policy.profile_visible(discoverable=discoverable, hidden=hidden, facts=facts)
        is visible
    )


def test_follow_requests() -> None:
    def refusal(visible: bool, facts: Facts, has_profile: bool = True) -> str | None:
        return policy.may_request_follow(
            visible=visible, facts=facts, requester_has_profile=has_profile
        )

    assert refusal(True, STRANGER) is None
    assert refusal(True, OWNER) == "follow_self"
    assert refusal(False, STRANGER) == "not_found"
    assert refusal(True, BLOCKED) == "not_found"
    assert refusal(True, STRANGER, has_profile=False) == "profile_required"


def _code(call: object) -> str:
    with pytest.raises(DirectoryRuleError) as raised:
        call()  # type: ignore[operator]
    return raised.value.code


def test_profile_fields() -> None:
    assert policy.handle("  Sky_Diver9 ") == "sky_diver9"
    assert _code(lambda: policy.handle("x" * 31)) == "handle_invalid"
    assert _code(lambda: policy.handle("Admin")) == "handle_reserved"
    assert policy.display_name("  A   B ") == "A B"
    assert _code(lambda: policy.display_name("   ")) == "display_name_required"
    assert policy.disciplines(["belly", "belly", "angle"]) == ["belly", "angle"]
    assert _code(lambda: policy.disciplines(["unspecified"])) == "discipline_invalid"
    assert _code(lambda: policy.disciplines(sorted(policy.DISCIPLINES)[:6])) == (
        "too_many_disciplines"
    )
    assert policy.search_query("  Al  ") == "al"
    assert _code(lambda: policy.search_query("a")) == "query_too_short"
