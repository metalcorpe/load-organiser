# Social activity and jumping together

Status: proposed product direction prompted by the owner's request for following jumpers and seeing activity across locations. Not implemented; no adoption or retention benefit has been measured. This is a proposed V1 revision, not a commitment to a general social network.

The [release brief](release-brief.md) now defines a concrete recommended beta bundle and correction/audience rules. The product owner confirmed initial review of post/profile reports. The broader alternatives and future ideas below remain discovery context.

## Product job and loop

Help a jumper answer: what are people I know doing, where have they been jumping, and could we plan something together?

See a friend's shared jump or an event → inspect the venue/opportunity → save a plan → optionally share a visit intention → meet/jump → log actual activity → optionally publish a selected summary → friends discover the activity.

This could give logging a social benefit and discovery a personal connection without requiring DZ adoption. It needs actual people sharing and useful opportunities; do not invent activity or present demo participants as real.

## Proposed small social scope

| Capability | Behavior | Boundary |
| --- | --- | --- |
| Jumper profiles | Display name, optional bio/disciplines/home DZ, selected shared activity | No private identifiers, serials, full history, or qualification evidence by default |
| Follow jumpers | Follow/request-follow, approve where applicable, unfollow | A follow gives access to the chosen audience, not the private logbook |
| Following feed | Chronological cards the viewer is permitted to read | No algorithmic ranking, fabricated activity, or inferred jump completion |
| Share a jump | After logging, preview fields, choose audience/timing, and publish | Logging/imports stay private by default; no automatic bulk publication |
| DZ-page activity | Relevant shared cards visible to the viewer, with activity and publication dates | Recent shared activity, not a live manifest or official visitor/jump totals |
| Visit intentions | Explicitly share a destination/event/date with an audience | Saved plans stay private; intention is not presence, registration, or acceptance |
| Essential controls | Audience edits, unpublish, block/report, and moderation | Release dependencies rather than later polish |

Comments, reactions, participant tagging, group/direct chat, global feeds, and livestreaming are extensions, not assumed first-cut scope.

## Examples

- “Alex shared a 4-way jump at DZ A from Saturday.” Show selected details and optionally an external media link.
- “Sam plans to attend this camp next month.” Explicit intention, not a booking or qualification claim.
- “Three posts from people you follow at DZ B this month.” Count visible posts, not all visitors or people currently on site.

If a jumper imports old history today, feed recency reflects publication; the card separately shows the actual activity date. Never label an old jump as current presence.

## Location and sharing

Activity starts private. Candidate audiences: private, approved followers, or public for the selected summary. A public profile does not mean a public logbook. Preview what is shared; location may be omitted or shared after a delay.

Only explicitly published activity/intentions appear in location views. Never infer presence from GPS files, private logs, home DZ, weather requests, bookings, or saved plans. No background tracking or live map of people is needed.

Every profile/feed/location view and direct API read must enforce audience, block, and unpublish rules. Removing access must also affect notifications and caches under an explicit retention policy. Do not expose private venue details in notification previews.

Browsing/following does not disclose the follower's own records. Media, membership evidence, gear serials, and service documents need separate disclosure rules; a shared summary cannot make its private source attachments accessible.

## Record integration

A post references an activity/version and selected fields; it is not another completed jump. Logging updates statistics and equipment usage; publishing does not increment those counts. Source labels remain meaningful, and social reactions never verify credentials or ownership.

Changes confined to unshared source fields leave the summary unchanged. A change to fields actually included in the published summary withdraws it before the relevant source change is committed; republishing requires a new preview and never copies newly private fields. Deleting/unpublishing a card does not erase a separate professional sign-off or operational record. Define correction, retention, and revocation behavior before implementation.

Later participant-tag invitations need recipient consent before revealing identity/location publicly. Accepting a social tag is not instructor verification. Several participants can link their own entries to a group activity without merging their individual jumps or duplicating any person's count.

## First use, operations, and cost

For an empty following feed, show real sourced opportunities and an explicit people-search/invite path. No mass contact upload is assumed. Keep the private logbook useful even when a user follows nobody.

Use paginated chronological feeds, lightweight cards, external media links, and bounded refresh. Avoid video storage and constant live updates initially. Audience enforcement, reporting, and moderation add real work even on free hosting.

No risk-oriented leaderboards are proposed. Supporter status must not imply competence, buy moderation outcomes, or reveal personal data. The product owner handles initial post/profile reports; the release brief proposes a bounded workflow. Response capacity, impersonation handling and later notification scope/frequency still need validation.

## Acceptance examples

- A private log/import creates no post or public presence signal.
- Public DZ pages show public cards; permitted follower-only cards stay scoped even on the same page.
- Saving an event remains private until a separate sharing action.
- Unpublishing/blocking removes access through feeds, location views, and direct API reads.
- Sharing a card never publishes full serials, private notes, or credential documents.
- Social posts and accepted tags do not increase jump totals or establish qualifications.

## Discovery questions

Is the main job following friends, discovering activity at a destination, or coordinating a future weekend? What do users want to share, with whom, and when? Can a small connected group benefit before a large network exists? Are comments/reactions needed early? Who will review abuse and impersonation reports?

Related: [proposed V1](version-one.md), [product model](product-model.md), [directory](dropzone-directory.md), and [discovery board](discovery-board.md).
