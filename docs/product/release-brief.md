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

These are research starting points, not imported inventory. No API/feed agreement, bulk-copy permission, affiliation, or partnership has been established. Manually record source-backed factual fields and an original summary only after reviewing applicable reuse conditions. Do not copy third-party descriptions/images or crawl restricted/social accounts by default. Conflicting or insufficient sources leave an entry pending review. No contact messages have been sent.

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
