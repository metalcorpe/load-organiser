# Initial beta release brief

Status: concrete working proposal for P0 issue [#141](https://github.com/metalcorpe/load-organiser/issues/141). Preparing this specification is authorized; the detailed defaults below are recommendations, not claims of user validation, delivered features, or explicit owner approval of every field. No application code is changed by this brief.

## Confirmed direction and responsibilities

- Individual skydivers first, with dropzone adoption later. No participating DZ is required.
- Public discovery starts in Europe. Personal accounts, gear, logs, and provisional DZ references work worldwide.
- The product owner maintains the initial DZ/opportunity listings, handles corrections, and reviews shared-post/profile reports during the small beta.
- Mobile-friendly responsive SvelteKit/TypeScript website; FastAPI/PostgreSQL retained. Native apps are deferred.
- Initial objective is expense coverage plus contingency, without personal income. A funding provider, paid hosting, or recurring subsidy is not selected.
- Product work remains analysis, documentation, and implementation handoff preparation. The separately authorized dependency refresh is [PR #170](https://github.com/metalcorpe/load-organiser/pull/170); it does not implement the proposed product.

## Audience and first-use value

Recommended first audience: active recreational skydivers who want to find European opportunities, keep personal records across venues, and follow a few people they know. No discipline-specific restriction. Students can browse and record personal activity, but formal training progression/sign-offs are deferred. English is the proposed initial interface language; retain original names, languages, prerequisites, and source links instead of presenting machine translations as official information.

A visitor should find a useful real listing before creating an account or entering historical jumps. Empty discovery results show the actual coverage and a suggestion route. An empty following feed offers people search and separately labeled discovery links, without fabricated posts or automatic contact uploads.

## Included release bundle

| Capability | First cut | Limit |
| --- | --- | --- |
| Discovery | List/search real DZs, events/boogies, camps/courses, coaches, and schools; filter by country/place, category, discipline, and applicable dates | No map, calendar view, distance calculation, live inventory, ranking, or native registration needed for beta |
| Provider and venue detail | Identity, source, last check, location, related offerings, original contact/registration link | A provider and a physical venue remain separate; directory presence does not imply partnership |
| Accounts and saves | Account/recovery, private saved opportunities and simple destination/event/date plans | A save/plan is not registration, payment, check-in, or a reservation |
| Personal logbook | Manual completed jumps, edits/deletion, DZ/gear references, recorded totals and recent activity | Separate from manifest loads; no jump is created from a plan or social post |
| Private gear | Container/harness, main, reserve, AAD; identifiers, acquisition details and manually entered service dates | Self-declared inventory/history; no verified title, transfers, applicability engine, or service certification |
| Social | Minimal discoverable profiles, approved follows, selected shared jump summaries, chronological following feed, authorized DZ activity, explicit shared visit intentions | No comments, reactions, messaging, tagging, global feed, or live presence |
| Portability | Versioned structured export and duplicate-safe restore of the app's own personal-record export | No third-party/device import promise; export remains available without payment |
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

Date-only entries stay date-only in the product; timestamp representation and time-zone rules are settled in #143. Different jumps on the same day are valid. Warn about likely duplicates rather than merging on date/DZ alone. Counts derive from distinct personal entries, not jump numbers, publications, event saves, or operator totals. Label totals as recorded in this app; no invented pre-app history or automatic currency acceptance.

### Gear entry

Require component type and a user-readable label. Manufacturer, model, serial, manufacture date, acquisition date/method, and service dates are optional to support unknown/borrowed/older equipment. Serial text preserves case, leading zeros, punctuation, and the original value; it is not a public unique ownership key.

A user explicitly selects owned versus borrowed/rented when relevant. Keep acquisition and serial corrections attributable, but do not call that verified chain of ownership. Referenced gear can be archived so historical jumps keep their actual references; changing a rig's current components must not rewrite past use. Manual service dates show their source and do not certify airworthiness or determine eligibility.

### Attachments and provisional limits

Recommended beta limits: no hosted photos, videos, receipts, credential documents, or flight files. Allow up to five external HTTP(S) media/reference URLs per private jump, each at most 2,048 characters; do not fetch previews or remote metadata automatically. Public publication selects links explicitly, warns that the destination is external, and creates no automatic embed.

Proposed text limits: private jump notes 2,000 characters, gear notes 1,000, profile bio 280, shared caption 280. These are design limits, not measured hosting capacity. Record counts, rate limits, batch restore sizes, and database/storage quotas must be measured and set in #143/#161 before beta data intake; do not claim unlimited storage. Quotas must not prevent export of records already held.

## Social audience and correction rules

- Profiles have a stable handle and display name, with optional bio/discipline. Do not publish real names, home DZ, account email, experience totals, or private records automatically. Profile discovery requires explicit opt-in; a non-discoverable user can still use personal records.
- Follow requests need acceptance. Following grants access only to explicitly follower-shared summaries and intentions. Follows are not credentials or access to the logbook.
- Logging stays private. Publishing requires a separate preview and audience choice: approved followers or public. Publishing later is a manual action; scheduled publishing is deferred.
- A jump card shares activity date, selected type/summary and optional canonical venue/caption/link. No serials, service/acquisition information, private notes, full activity history, or unreviewed provisional venue is included.
- Feed order uses publication time and displays the activity date separately. Venue views query the same authorized posts; they do not count private jumpers or infer who is present now.
- Saved visits remain private until separately shared as an intention. Show destination/event, planned date and audience. Editing/cancelling an intention changes the same record; it never confirms presence or registration.
- Editing or deleting a jump unpublishes its linked card before the change becomes visible. Republish only from a new preview. Unpublishing does not remove the private jump or alter its count.
- Blocking removes both-direction follows and denies authenticated access to the other user's profile/activity across feed, venue, search and direct API routes. Already public content cannot be made secret from someone browsing anonymously or using another account; explain this limitation when selecting a public audience.
- Unpublish, audience narrowing, follow removal, and account deletion must revoke future service access across all views/caches. A service cannot retract screenshots, copied data, or external media. Keep private pages out of shared/public caches.
- Report profiles/posts from the relevant screen. The owner reviews the reported content and may hide public content or restrict publishing; this role does not grant routine access to private logs/gear. Publication stays disabled if moderation has no available owner.

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

Recommended operating routine, to be checked against the owner's actual workload:

1. Weekly: review corrections/reports, check opportunities starting within the next 30 days, and apply confirmed cancellations/postponements.
2. Every 60 days: review continuing coach/school/DZ profiles. After 90 days without a successful check, label the information as needing recheck and exclude stale continuing offers from default opportunity results. Historical venues remain usable in private logs.
3. Automatically remove ended dated opportunities from upcoming results using their recorded end/date precision/time zone. Unknown dates never receive an invented expiry or bookable status. Expiry does not claim the source was rechecked.
4. If the queue or inventory exceeds available maintenance time, pause new submissions/coverage expansion, show the limit, and keep existing personal records/export usable. Social publishing can be paused independently of private logging.

Before public beta, the owner completes a real manual review cycle and a sample user journey for each enabled listing category. Record actual country/category coverage, stale/missing fields, source/reuse issues, and time spent. Reduce the published inventory to what can be maintained. No inventory count, volunteer capacity, geographic completeness, or user demand is validated by this brief. #151/#162 own that release evidence.

## Explicit exclusions

Native/PWA/offline sync, push/email activity alerts, calendar exports, automated weather forecasts, FlySight/GPX/FIT/paper imports, USPA retrieval and verified progression, ownership transfers and theft matching, provider self-service, in-app bookings/payments/refunds, live tracking, DZ check-in/manifest, hosted media and advanced social features remain outside this beta. A voluntary support link is optional and does not gate records/export or establish a paid-service commitment.

## Planning completion and handoff

This brief supplies recommended field rules, limits, source policy, social behavior and maintenance cadence. #141 remains open while these defaults are reviewed; confirmed decisions are distinguished above. Preparing UX/architecture drafts against this baseline is useful, but no feature implementation is authorized by this document.

Next planning outputs:

- #142: phone-sized discovery/save/login-return, manual log/gear, follow/share/intention, reporting/blocking, and export/recovery walkthroughs, including empty/error/privacy states.
- #143: rendering/hosting adapter options, server-enforced identity/audiences, date/units policy, provenance/corrections/deletion, export/restore contract and measured service limits. Record options/trade-offs before selecting hosting.
- Claude Code handoff: each accepted task identifies inputs, expected behavior, exclusions, dependencies and validation. Keep unresolved product assumptions visible and prohibit invented inventory, credentials, partnerships, payment accounts, or uncontrolled paid infrastructure.

Acceptance evidence for the future release must cover both a successful connected journey and forbidden cross-user access. Documentation checks establish consistency and working links; they do not establish product behavior, user acceptance, or a validated maintenance workload.
