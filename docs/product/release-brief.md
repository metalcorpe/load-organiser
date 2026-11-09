# Initial beta release brief

Status: selected working first-beta baseline under delegated expert product judgment. See [product decisions](beta-decisions.md) for the scope calls and their rationale. This is an implementation specification for later Claude Code work, not delivered behavior or validated demand.
## Confirmed direction and responsibilities

- Individual skydivers first, with dropzone adoption later. No participating DZ is required.
- Public discovery starts in Europe. Personal accounts, gear, logs, and provisional DZ references work worldwide.
- The product owner maintains the initial DZ/opportunity listings, handles corrections, and reviews shared-post/profile reports during the small beta.
- Mobile-friendly responsive SvelteKit/TypeScript website; FastAPI/PostgreSQL retained. Native apps are deferred.
- Initial objective is expense coverage plus contingency, without personal income. A funding provider, paid hosting, or recurring subsidy is not selected.
- Product work remains analysis, documentation, and implementation handoff preparation. The separately authorized dependency refresh is [PR #170](https://github.com/metalcorpe/load-organiser/pull/170); it does not implement the proposed product.

The [two-pass product review](product-review.md) records the risks that prompted the [selected decisions](beta-decisions.md). Those decisions now resolve the scope recommendations; real user value and maintenance capacity still require evidence.

## Audience and first-use value

Selected first audience: active recreational skydivers who want to find European opportunities, keep personal records across venues, and follow a few people they know. No discipline-specific restriction. Students can browse and record personal activity, but formal training progression/sign-offs are deferred. English is the initial interface language; retain original names, languages, prerequisites, and source links instead of presenting machine translations as official information.

A visitor should find a useful real listing before creating an account or entering historical jumps. Empty discovery results show the actual coverage and a suggestion route. An empty following feed offers people search and separately labeled discovery links, without fabricated posts or automatic contact uploads.

## Included release bundle

| Capability | First cut | Limit |
| --- | --- | --- |
| Discovery | List/search real DZs and dated events/boogies/camps/courses; filter by country/place, category, discipline, and applicable dates | No map, calendar view, distance calculation, live inventory, ranking, or native registration needed for beta |
| Provider and venue detail | Basic offering-provider identity, source, last check, venue location, related dated offerings and original contact/registration link | Provider and venue remain separate; standalone coach/school directories are deferred |
| Accounts and saves | Account/recovery, private saved opportunities and simple destination/event/date plans | A save/plan is not registration, payment, check-in, or a reservation |
| Personal logbook | Manual completed jumps, edits/deletion, DZ/gear references, recorded totals, optional self-declared prior-history baseline and recent activity | Separate from manifest loads; no jump is created from a plan or social post |
| Private gear | Container/harness, main, reserve, AAD; identifiers, acquisition details and manually entered service dates | Self-declared inventory/history; no verified title, transfers, applicability engine, or service certification |
| Social | Minimal discoverable profiles, approved follows, selected shared jump summaries, chronological following feed, authorized DZ activity | No comments, reactions, messaging, tagging, global feed, or live presence |
| Portability | Versioned structured export and own-export restore into empty records, with duplicate-safe repeat acknowledgement | No third-party/device import promise; export remains available without payment |
| Maintenance | Source-backed listing review, correction/report queue, profile/post moderation, duplicate resolution | Owner-operated during beta; no provider publishing portal or promised response time |

## Minimum personal data and entry rules

### Jump entry

| Field | Requirement and behavior |
| --- | --- |
| Internal identity/owner | Assigned by the service, stable across edits and export/restore; not inferred from a display number |
| Activity date | Required local calendar date selected by the jumper; exact exit time is optional, never invented for historical logs |
| DZ/location | Required canonical reference or private provisional name plus country; do not require the operator to register |
| Jump type/discipline | Required selection; include other/unspecified so lack of a category does not manufacture certainty |
| Jumper's jump number | Optional positive user-entered number; warn about a duplicate within the account, without treating it as a second internal identity or blocking legitimate corrections |
| Actual equipment used | Optional links to owned components, or a borrowed/rented/unknown description. Unknown gear never counts as use of the user's current rig |
| Exit/deployment altitude, freefall time | Optional values with explicit units; no zero-filled unknowns, eligibility claim, or estimated telemetry |
| Notes and external links | Optional and private; never copied wholesale into a shared card |
| Provenance | Manual/self-reported, creation/update times and relevant correction/restore identifiers recorded by the service |

Date-only entries stay date-only in the product; timestamp representation and time-zone rules are settled in #143. Different jumps on the same day are valid. Warn about likely duplicates rather than merging on date/DZ alone. Detailed counts derive from distinct personal entries, not jump numbers, publications, event saves or operator totals. An optional self-declared prior-history baseline uses a cutoff to avoid double-counting; show it separately from detailed records. The [baseline rules](beta-decisions.md) define the combined reported total. It never creates historical entries or automatic currency acceptance.

#### Implemented in #153 (beta)

Backend `backend/app/skydiver/logbook/` (`/api/skydiver/v1/jumps`); web `/jumps`, `/jumps/new` and `/jumps/{id}` under Records. Owner-only throughout.

- Required: activity DATE (up to the latest local date anywhere, UTC+14; entered in the browser's local day), a listed venue (stored merge-resolved) or the owner's private place, and a type (`unspecified` allowed). Everything else is optional and null when not given: jump number, local exit time with its IANA zone (both or neither), exit/deployment altitude with an explicit unit and a datum that defaults to "not stated", freefall seconds, other-equipment text, notes (2,000) and up to five http(s) links that are never fetched.
- Equipment actually used links only the owner's own components (archived ones stay linked). Nothing is preselected; unknown gear is no link. A component can be added from the jump form in the same submission, retry-safe. Deleting a component or private place a jump uses is refused (`component_in_use`, `place_in_use`); archive the component instead.
- Creates carry a client key with a receipt that outlives the jump: a repeat returns the same entry, different content under the same key is 409, and a replay after deletion answers 410 `jump_deleted` without recreating it. A refused or unconfirmed form keeps its key, so resending cannot create a second entry.
- Likely duplicate (same jump number, or the same date, place, type, time, altitudes, freefall and notes as an existing entry) answers 409 with the earlier entry; the jumper can view it or save a distinct jump. Edits are not blocked; the detail lists other entries with the same number.
- Edits and deletes compare-and-swap the jump version (409 `edit_conflict`). History records creation and corrections with earlier values for facts; notes, links and other-equipment text record only that they changed.
- The list shows the recorded total, labelled as entries recorded rather than a lifetime total. The prior-history baseline, summaries and gear-use counts belong to #154; publishing to #156.

Limits: the 2,000-jump cap is counted without a lock, so only the owner's own simultaneous saves could overshoot it slightly (the same accepted trade-off as gear). Measurements are stored as entered; no normalized value is derived yet. No offline drafts: leaving the form loses unsaved input.

#### Implemented in #154 (beta)

Backend `backend/app/skydiver/history/` (`/api/skydiver/v1/history`, `/history/baseline`, `/history/baseline/preview`); web `/history` and `/history/baseline` under Records. Owner-only throughout.

- Totals derive only from distinct detailed entries. Without a baseline only the recorded count is shown, labelled as recorded; the highest jump number is never used as a total.
- Optional baseline: B jumps (0–100,000) completed before date D (not after the latest local date anywhere). Lifetime total = B + entries dated on or after D. Entries before D are listed as already within B. If they outnumber B, the page flags it and shows no combined total; the jump is not rejected and B is not changed. Deleting an entry never rewrites B.
- Changing B/D goes through a read-only preview (now vs with the change) before saving. A declaration carries no version; a correction or removal carries the version it was based on, taken from the first preview, so an older tab's save answers 409 `edit_conflict` instead of overwriting. Declarations, corrections (from/to) and removals are kept as private provenance (latest 50 shown) and remain after removal.
- Summaries, read from one REPEATABLE READ snapshot so the figures agree: first/last recorded date, recorded jumps per calendar month for the last 12 months (ending with the month of the latest local date anywhere, so a not-yet-started month can briefly show 0), and counts by type, by place (venues merged since count under the venue that remains) and by component explicitly recorded on a jump, with its last use. The baseline adds no month, place, type or gear use.

Not built here: sharing anything (#156/#157). Nothing is used as currency or eligibility evidence. Export/restore of the baseline and its provenance: #155 below.

#### Implemented in #155 (beta)

Backend `backend/app/skydiver/records/` (`/api/skydiver/v1/records`, `/records/export`, `/records/restore/check`, `/records/restore`); web Profile → Your data (`/profile/data`). Format: [export-format.md](export-format.md).

- Export: free; owner's places, gear (rigs, stints, service, history), jumps with equipment used and history, baseline with provenance, saved listings and plans, plus snapshots of referenced public venues/listings; one REPEATABLE READ snapshot; instants in UTC; private attachment via a same-origin POST; 1 per account per 5 minutes. No credentials, email, roles, follows or other people's data (the schema cannot hold them).
- Restore: 8 MiB raw / 4 MiB normalised; full validation without writes (`check` previews counts, detached references and eligibility; 10 per hour); restore needs a confirmed email and the password (3 per account per day). Exact-file SHA-256 receipt per owner: a repeat answers already restored with no writes. Non-empty records (places, gear, jumps, baseline, saved, plans) are refused before any write, with no deletion advice. Everything is inserted under new IDs in one transaction; records are marked `restored` with a `from_export` history entry.
- Concurrency is compare-and-swap style, without a lock: emptiness is checked, the rows are inserted, and the managed collections are counted again before commit; any difference rolls the restore back (tested by interleaving a write). The `lock_owner` row lock that saves/plans/places still take is not used here (architecture A6 prefers compare-and-swap).

Limits: a write that commits between the final recount and the restore's commit (a sub-millisecond window) is not detected. Writes do not reserve the 4 MiB export budget, so an account with very long notes on many jumps could produce an export that restore refuses as too large; counts limits keep typical accounts far below it, but this is not enforced at write time. The web passes up to 8 MiB through the Worker in memory; CPU time on the Workers free plan for an 8 MiB upload is untested. Gear history shows the restore entry as "from export".

### Gear entry

Require component type and a user-readable label. Manufacturer, model, serial, manufacture date, acquisition date/method, and service dates are optional to support unknown/borrowed/older equipment. Serial text preserves case, leading zeros, punctuation, and the original value; it is not a public unique ownership key.

A user explicitly selects owned versus borrowed/rented when relevant. Keep acquisition and serial corrections attributable, but do not call that verified chain of ownership. Referenced gear can be archived so historical jumps keep their actual references; changing a rig's current components must not rewrite past use. Manual service dates show their source and do not certify airworthiness or determine eligibility.

### Attachments and provisional limits

Selected beta limits: no hosted photos, videos, receipts, credential documents, or flight files. Allow up to five external HTTP(S) media/reference URLs per private jump, each at most 2,048 characters; do not fetch previews or remote metadata automatically. Public publication selects links explicitly, warns that the destination is external, and creates no automatic embed.

Working text limits: private jump notes 2,000 characters, gear notes 1,000, profile bio 280, shared caption 280. These are design limits, not measured hosting capacity. Record counts, rate limits, batch restore sizes, and database/storage quotas must be measured and set in #143/#161 before beta data intake; do not claim unlimited storage. Quotas must not prevent export of records already held.

## Social audience and correction rules

- Profiles have a stable handle and display name, with optional bio/discipline. Do not publish real names, home DZ, account email, experience totals, or private records automatically. Profile discovery requires explicit opt-in; a non-discoverable user can still use personal records.
- Follow requests need acceptance. Follower audience means the current approved-follower set, including people approved later, can read existing follower-shared jump summaries; disclose that when choosing the audience. Follows are not credentials or access to the logbook. Users can manually share an opted-in profile URL/handle outside the service without contact imports or platform-sent invitations.
- Logging stays private. Publishing requires a separate preview and audience choice: approved followers or public. Publishing later is a manual action; scheduled publishing is deferred.
- A jump card shares activity date, selected type/summary and optional canonical venue/caption/link. No serials, service/acquisition information, private notes, full activity history, or unreviewed provisional venue is included.
- Feed order uses publication time and displays the activity date separately. Venue views query the same authorized posts; they do not count private jumpers or infer who is present now.
- Bookmarks and dated visit plans remain private. Shared future intentions are deferred; no plan appears in feeds, profiles or public venue activity.
- Edits confined to unshared private fields leave the selected summary unchanged. Editing fields actually included in the published summary withdraws that card before the relevant source change is committed; deletion also withdraws it. Republish only from a new preview. No new private field is copied automatically. Unpublishing does not remove the private jump or alter its count.
- Blocking removes both-direction follows and denies authenticated access to the other user's profile/activity across feed, venue, search and direct API routes. Already public content cannot be made secret from someone browsing anonymously or using another account; explain this limitation when selecting a public audience.
- Unpublish, audience narrowing, follow removal, and account deletion must revoke future service access across all views/caches. A service cannot retract screenshots, copied data, or external media. Keep private pages out of shared/public caches.
- Report profiles/posts from the relevant screen. The owner reviews the reported content and may hide public content or restrict publishing; this role does not grant routine access to private logs/gear. Publication stays disabled if moderation has no available owner.

#### Implemented in #156 (beta)

Backend `backend/app/skydiver/social/` (`/me/profile`, `/me/people/...`, `/people`, `/people/{handle}`, reviewer `/social/...`); web `/profile/public`, `/people`, public `/people/{handle}`, reviewer `/review/social`.

- Profile: opt-in and separate from the account. Handle (3–30 lowercase letters/digits/underscores, unique ignoring case, a few reserved names, fixed once created so links keep working), display name, optional bio (280), up to five disciplines and an optional listed home dropzone. Nothing is copied from the email, registration name, logbook, gear, totals or baseline.
- Visibility: the owner always; anyone else only while not hidden by a reviewer and, signed in, with no block either way; then if discoverable (also anonymously) or the viewer is an approved follower. Search finds discoverable profiles only and needs a session. Every refusal is the same 404 as an unknown handle; follow/block/report/unfollow on a profile the caller may not reach is also 404, so non-discoverable handles cannot be probed.
- Follows always need approval; asking needs your own profile (the person sees who asks). Approve, decline, cancel, unfollow and remove follower. A follow grants nothing in private records (tested against the logbook API); it only matters for follower-shared posts (#157).
- Block: removes both follows in the same transaction; approval is a conditional update that fails while a block exists; every read re-checks blocks. Unblocking does not restore follows. Public profiles stay visible to signed-out visitors; this is explained before blocking.
- Reports: reason and optional note, one open report per reporter and target (a repeat is acknowledged, not stacked), 10 per day. A separate reviewer queue (not listing corrections) shows the reported profile's public fields at report time and now; decisions are no action, hide profile or restrict publishing (a reason is required and shown to the owner; the reporter is never shown to the reported person). Reviewers can lift restrictions with a reason. Publishing restriction takes effect with #157.
- Limits: 500 follows/requests and 500 blocks per account; 50 follow requests per day; 120 searches per hour.

Not built here: shared jump posts and their audiences (#157), the feed and venue activity (#158); account deletion; notifications. Visit intentions (#159) are deferred outside V1. The reviewer sees the reporter's handle (needed to judge abuse of reporting); profile owners never do.

#### Implemented in #157 (beta)

Backend `backend/app/skydiver/posts/` (`/me/jumps/{id}/sharing`, `/me/jumps/{id}/post`, `/me/posts/{id}/audience`, `/me/posts/{id}`, `/posts/{id}`, `/people/{handle}/posts`, `/posts/{id}/reports`); web `/jumps/{id}/share`, public `/posts/{id}`, shared jumps on `/people/{handle}`, post reports in `/review/social`.

- Publishing is a separate action from the jump page: choose parts, preview, then publish exactly what was previewed from the jump version previewed (an edit in between is a conflict). The activity date is always shared; jump type, listed dropzone, exit altitude (with unit and reference) and freefall time are optional, with a caption (280) and one http(s) link. Never shared: notes, the jump's own links, equipment, serials, jump number, exit time, deployment altitude, a private place or a dropzone no longer listed. One post per jump; it does not count as a jump or change totals.
- Audience: approved followers (including people approved later) or public. Public needs a discoverable profile. Publishing needs a profile that is not hidden or publishing-restricted. Readers: the owner; anyone else only while the profile is not hidden and, signed in, no block exists either way; then a public post of a discoverable profile, or any post for an approved follower. One SQL rule serves the single post and profile list; anything else is the same 404 as an unknown id.
- Changes: audience can be narrowed or widened (widening re-checks publishing rights); unpublishing deletes the post and keeps the jump. Editing a shared value (date always; type, dropzone/place, altitude fields or freefall only if shared) deletes the post in the same transaction as the edit; other edits leave it unchanged. Deleting the jump deletes the post. Turning discoverability off deletes public posts in the same transaction; follower-only posts stay for approved followers. Each event is shown on the owner's jump history. Pages and API responses are `no-store`, so a removed post is not served from a shared cache.
- Concurrency without locks: publishing compare-and-swaps the jump version and conditionally touches the profile (not hidden, not restricted, discoverable for public), so a concurrent edit, moderation or discoverability change either commits first and the publish fails, or waits and then sees and withdraws the new post.
- Reports: posts can be reported from the post page into the same reviewer queue (one open report per reporter and post, separate from a profile report). The reviewer sees the card as reported and whether it is still published; "Remove the post" deletes it and shows the reason on the owner's jump history.
- Limits: 50 publications per day; report limits are shared with profile reports.

Not built here: the following feed and dropzone activity (#158); scheduled publishing; notifications. Export (#155) does not include posts and restore never republishes them. A profile lists 20 posts per page with a link to older ones.

#### Account deletion (implemented, architecture A9)

Backend `POST /auth/account/deletion`; web "Delete account" on `/profile`.

- Needs the current password (sharing the sign-in failure budget) and a ticked confirmation. One transaction deletes the account; its person, sessions, profile, follows both ways, blocks, posts, logbook, gear, places, history, saves, plans, restore receipts and reports by or about the person cascade with it. Public posts and the profile therefore disappear from every view on the next request.
- Kept without the link to the person (foreign keys set to null): suggestions, problem reports and feedback, including their text, until the retention purge deletes them 30 days later (below), and reviewer history: decisions on public records and on social reports (the decider column of social reports gained its foreign key in migration `c3e8a5f7d1b9`; earlier it kept a deleted reviewer's account id).
- The address can register again and starts empty. Tested (`test_account_deletion.py`): afterwards no row of any table contains the deleted person id or account id anywhere in its text, which covers JSON and columns without foreign keys; a suggestion the person sent stays without its author; a reviewer who deletes their account leaves their decisions in place with the decider cleared; other people's records and the public directory are unchanged. Not tested: a write by the same account racing the deletion (expected to fail with a server error rather than restore anything, by reading the code only).
- A restore from an older backup does not bring a deleted account back once the erasure ledger is replayed (see below and `recovery-runbook.md`). Until pruned, the ledger keeps the deleted account's ids, never its content.
- Not built: a grace period or undo (deletion is immediate). Known consequence: a hidden or restricted person can delete and register again with the same address, and reports about them are deleted with the account.

#### Privacy page and beta feedback (implemented, #162 in part)

Web `/privacy` (public, linked from the footer and the profile page); submission kind `feedback` (migration `f1c4e8a6b3d2`) on `/submit?kind=feedback`, reviewed in `/review/submissions`.

- The page states, from the current code: what stays private; what a profile and a shared jump can include and who can read them; that reviewers see a reporter's handle but reported people never see the reporter; what email and the session cookie are used for (seven-day fixed sign-in, five at most); export and restore; what account deletion removes and keeps unlinked; the backup targets (one a day, seven at most, not running yet) and what a restore re-applies or loses; known limits; how to send feedback.
- Feedback is a message about the beta with no listing target (`target_not_allowed` otherwise), sent signed in, subject to the same daily and open limits and the same intake switch (`SKYDIVER_SUBMISSIONS_OPEN`) as suggestions. Reviewers see it without the sender's name or email, and the sender sees the status and reviewer note on `/submit`.
- The outdated "sharing, feed and deletion come later" notice on `/profile` is replaced by links to the page and to feedback.
- Tested: backend `test_moderation.py` (feedback reaches the queue without the sender; target refused; empty message refused); e2e `privacy` (footer link, sections, sign-in redirect for feedback; a member sends feedback and a reviewer sees it without the sender's email).
- Not done here (#162, needs people): real listing coverage and maintainer ownership, a beta cohort and observed use. The page must be updated when backups start running or a limit changes; nothing checks that automatically.

#### Support page (implemented, #162)

Web `/support` (public, linked from the footer); data in `web/src/lib/support.ts`.

- Voluntary Ko-fi link (`rel="external noopener noreferrer"`); support unlocks nothing and gates no record or export.
- Running costs listed per item and month with a total. None are paid yet, so the page says so; `RUNNING_COSTS` must be updated by hand when a paid service starts or changes (#161). Nothing checks it.
- The site does not record whether anyone gave; Ko-fi handles payment under its own terms.
- Tested: e2e `privacy` (footer link, sections, the no-costs statement, link target and rel). Not tested: the table with costs, since the list is empty.

#### Submission retention after account deletion (implemented, #162)

`app/skydiver/moderation/retention.py`, migration `a8d2f6c4e1b7`; an operator command, no screen.

- A trigger sets `skydiver_submission.author_removed_at` when the author link is cleared, which happens through the person foreign key on every account deletion path. A check keeps exactly one of author and removal time. Rows already without an author got the migration time, so none is purged before 30 days from the migration.
- `python -m app.skydiver.moderation.retention purge [DAYS]` deletes those submissions once the time is more than DAYS (default 30, the architecture's target) in the past, reviewed or not. It is not scheduled: it runs with the backups once hosting exists (`recovery-runbook.md`).
- `GET /submissions/intake` tells a signed-in person whether new submissions are taken; `/submit` shows "Sending is paused" in place of the form when they are not. If that check fails the form is shown and sending reports the pause as before.
- Tested: `test_account_deletion.py` (deleting the account sets the removal time), `test_submission_retention.py` (only rows past the period are deleted; author and time cannot both be missing), `test_moderation.py` (intake reports open, then paused; needs a session). Not tested in a browser: the paused notice, because the end-to-end server runs with submissions open.

#### Erasure ledger (implemented, architecture A9)

`app/skydiver/recovery/ledger.py`, migration `d4f9b6a2e8c1`; operator commands only, no API or screen.

- Triggers record deletions, new blocks and changes to visibility and account state in `skydiver_erasure_ledger` in the same transaction; the identity store records new passwords. Entries hold keys and changed flags or times, no free text.
- `export` writes the ledger for storage outside the backup set; `apply` replays it on a restored database, forces a password reset where the password changed after the backup, and revokes every session and token; `prune` drops old entries.
- Tested: recording and refusal of malformed or unknown entries (`test_erasure_ledger.py`); the full backup, erase, export, restore and replay drill (`scripts/verify.sh recovery`).
- Not decided (needs accounts): where exports are kept and how often they run. Not built: recording of ordinary edits, which a restore still reverts.

#### Implemented in #158 (beta)

Backend `GET /me/feed` and `GET /venues/{id}/posts` in `backend/app/skydiver/posts/`; web `/activity` (replacing the placeholder) and "Shared jumps here" on `/dz/{id}`.

- Feed: posts of people the reader follows with an approved follow, through the same readability rule as single posts, newest publication first, 20 a page with an "older" link. No ranking, no own posts, no suggestions mixed in; each card shows the jump date and the publication date separately.
- Dropzone activity: posts that shared that listed dropzone, including posts saved under a listing later merged into it. Signed out: public posts of discoverable, visible profiles only. Signed in: audience, follow and block rules on every request. A jump logged at the dropzone whose venue was not shared does not appear. No counts, presence or "who is here" claims; the page says so.
- Revocation: both views query on every request with no cache (`no-store`), so unpublishing, narrowing, removing a follower, blocks and reviewer hides apply on the next load (tested for unpublish, follower removal, re-approval, block, narrowing and hidden profiles).
- Empty states: the feed links to people search, profile creation, discovery and the dropzone list; nothing is invented.

Not built here: notifications, reactions or comments; a feed of your own posts (they are on your profile); dropzone pages for unlisted or draft venues (404).

## European discovery inventory and sources

Europe is a coverage boundary, not a commitment to populate every country equally. Accept European suggestions from the start and show genuine gaps. Country inventory grows through reviewed sources; do not create fictional listings to fill a map or promise complete coverage. Personal logging outside maintained coverage remains usable.

Primary-source candidates checked on 2026-11-02:

| Source | Candidate use | Limitation |
| --- | --- | --- |
| [British Skydiving DZ directory](https://britishskydiving.org/find-drop-zone/) | Locate UK venue/operator references | Association directory presence does not establish current operating availability or permission for bulk reuse |
| [FFP structures directory](https://www.ffp.asso.fr/ou-pratiquer/liste-de-toutes-les-structures-ffp/) | Find French schools/structures and official identifiers | Structures include different organization types; do not turn every entry into a physical DZ |
| [DFV places and clubs](https://www.dfv.aero/Info/Pl%C3%A4tze%2BVereine) | Locate German venue/club references | A club and venue may differ; follow through to the appropriate official operator source |
| [Skydive Empuriabrava event calendar](https://skydiveempuriabrava.com/es/calendario-de-eventos/) | Example of an operator-maintained dated opportunity source | An example source, not an accepted feed, partner, or completeness claim for Spain |
| Original coach/school/organizer website, or a directly supplied submission | Confirm an offering and provide external contact/registration | Review each source and stated prerequisites; a submission is not automatically published |

These are research starting points, not imported inventory. No API/feed agreement, bulk-copy permission, affiliation, or partnership has been established. Manually record source-backed factual fields and an original summary only after reviewing applicable reuse conditions. Do not copy third-party descriptions/images or crawl restricted/social accounts by default. A public Facebook page may be cited as a source (owner decision 2026-11-09). Conflicting or insufficient sources leave an entry pending review. No contact messages have been sent.

For each candidate record, the maintainer records country, venue/provider identity, category, source URL, fields supported by that source, last check, lifecycle/status, reuse review, and next review date. A dated opportunity requires a title, organizer, date/range with venue time zone, location or explicit location status, original source, and contact/registration route. Prerequisites/capacity/price may be unknown and must be labeled as such. An undated school/coach profile cannot masquerade as a confirmed dated event.

## Maintenance cadence and release gate

Working operating routine, to be checked against the owner's actual workload:

1. Weekly: review corrections/reports, check opportunities starting within the next 30 days, and apply confirmed cancellations/postponements.
2. Every 60 days: review continuing coach/school/DZ profiles. After 90 days without a successful check, label the information as needing recheck and exclude stale continuing offers from default opportunity results. Historical venues remain usable in private logs.
3. Automatically remove ended dated opportunities from upcoming results using their recorded end/date precision/time zone. Unknown dates never receive an invented expiry or bookable status. Expiry does not claim the source was rechecked.
4. If the queue or inventory exceeds available maintenance time, pause new submissions/coverage expansion, show the limit, and keep existing personal records/export usable. Social publishing can be paused independently of private logging.

Before public beta, the owner completes a real manual review cycle and a sample user journey for each enabled listing category. Record actual country/category coverage, stale/missing fields, source/reuse issues, and time spent. Reduce the published inventory to what can be maintained. No inventory count, volunteer capacity, geographic completeness, or user demand is validated by this brief. #151/#162 own that release evidence.

## Explicit exclusions

Shared future intentions, standalone coach/school directories, restore merging/conflict selection, native/PWA/offline sync, push/email activity alerts, calendar exports, automated weather forecasts, FlySight/GPX/FIT/paper imports, USPA retrieval and verified progression, ownership transfers and theft matching, provider self-service, in-app bookings/payments/refunds, live tracking, DZ check-in/manifest, hosted media and advanced social features remain outside this beta. A voluntary support link is optional and does not gate records/export or establish a paid-service commitment.

## Planning completion and handoff

Scope is settled in [the decision sheet](beta-decisions.md). #141/#142 are complete as planning decisions under delegated expert product review. Neither closure is user research or device acceptance. #160/#151/#162 retain those release checks.

P0 architecture is selected in [architecture](architecture.md) and [data contracts](data-contracts.md). The [Claude Code handoff](claude-code-handoff.md) prepares #144; no application implementation starts in this planning thread. Pilot limits are design defaults, not measured capacity. Hosting/email/backup and user/device validation remain release gates.

Account UX follows the selected architecture: new accounts verify email before private writes/sharing, sessions expire after seven days, and restore/deletion/credential changes require fresh password confirmation. Turning off public discoverability withdraws public cards; explain that existing follower-only content may remain accessible to approved followers.
