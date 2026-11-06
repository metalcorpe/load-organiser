"""#157 which source edits withdraw a published summary, and input limits."""

import pytest

from app.skydiver.directory.policy import DirectoryRuleError
from app.skydiver.posts import policy
from app.skydiver.posts.policy import Share


@pytest.mark.parametrize(
    ("changed", "expected"),
    [
        ({"notes", "links", "other_gear", "jump_number"}, (False, set())),
        ({"exit_time", "time_zone", "deployment_altitude"}, (False, set())),
        ({"jumped_on"}, (True, set())),
        ({"jump_type"}, (False, {Share.TYPE})),
        ({"place_id", "venue_id"}, (False, {Share.VENUE})),
        ({"altitude_unit"}, (False, {Share.ALTITUDE})),
        (
            {"altitude_datum", "freefall_seconds"},
            (False, {Share.ALTITUDE, Share.FREEFALL}),
        ),
    ],
)
def test_only_shareable_source_fields_can_withdraw(
    changed: set[str], expected: tuple[bool, set[Share]]
) -> None:
    assert policy.touched(changed) == expected


def test_caption_and_link_limits() -> None:
    assert policy.caption("  ") is None
    assert policy.caption("x" * 280) == "x" * 280
    with pytest.raises(DirectoryRuleError, match="caption_too_long"):
        policy.caption("x" * 281)
    assert policy.link("") is None
    assert policy.link("https://video.example/1") == "https://video.example/1"
    with pytest.raises(DirectoryRuleError, match="link_invalid"):
        policy.link("ftp://example.org")
    with pytest.raises(DirectoryRuleError, match="share_invalid"):
        policy.shares(["notes"])
