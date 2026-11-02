# Version one — proposed scope

Status: scope proposal for review, not an approved implementation commitment. Skydivers first; no participating dropzones assumed. This proposal combines discovery value with personal recordkeeping, following the product owner's concern that a logbook and gear inventory alone might not justify adoption.

Planning update: phased GitHub tracking is authorized. Use the [delivery plan](delivery-plan.md) and its P0 decisions to finalize the first cut before implementation; issue creation does not mark this entire proposal as approved or delivered.

## Promise

Find opportunities and people to jump with, keep your personal records, and choose what activity to share.

Proposed social revision: following jumpers, explicitly shared jump cards, audience-scoped venue activity, and optional shared visit intentions. See [social activity](social-activity.md). This extends the earlier discovery/recordkeeping proposal; the exact first-cut bundle still needs agreement and should not expand into a full social platform.

The application must be useful before a user has entered a substantial personal history. Public discovery supplies something to browse; personal records provide continuity after activity. Useful listing coverage and the audience/region still need to be established.

## Included capabilities

Delivery direction: a mobile-friendly responsive website with public shareable links and desktop access. No installation is required. PWA installation, offline drafts, push notifications, and native-device integrations are later options rather than initial commitments; see [mobile strategy](mobile-strategy.md).

Frontend selection: SvelteKit with TypeScript, keeping FastAPI/PostgreSQL. This records the product owner's preference; the current React app has not been migrated. See [transition plan](svelte-transition.md).

| Area | Initial scope | Boundary |
| --- | --- | --- |
| Public discovery | Browse/search sourced events, boogies, camps/courses, coaches, and schools; filter by category, place, dates where applicable, and discipline | Provider profiles and dated opportunities remain distinct; no live availability or booking guarantee |
| Dropzone directory | Find/select a DZ, view sourced location information and related listings; retain closed/historical locations | Operator account not required; no endorsement implied |
| Personal account | Basic profile, account recovery, private records, saved opportunities, and planned visits | Saving/visiting does not share credentials or private history with providers |
| Social connections | Follow/request-follow, chronological following feed, selected jump summaries, explicit visit intentions | Private logs/plans by default; audience enforcement, block/report, and moderation required |
| Jump logbook | Manual add/edit, DZ reference, activity time, discipline, equipment selection, notes, basic totals and recent activity | No automated eligibility decision, issuer verification, or completed-jump assertion from event attendance |
| Gear inventory | Separate container/main/reserve/AAD records, manufacturer/model, serial, optional manufacture/acquisition details, user-entered servicing/due dates | Ownership and servicing are self-reported; no verified title or automatic manufacturer applicability claim |
| Connections | Jump-to-DZ/gear, listing-to-venue/provider, saved opportunity-to-plan, shared card-to-jump/venue | Reuse records; venue views show only deliberately shared activity permitted to the viewer, never inferred presence |
| Portability and recovery | Versioned personal-record export and tested restore/import of that export; transparent limits | Not a promise to import every third-party format; export must not require payment |
| Sustainability | Optional external contribution link and clear cost/support information | No ads, paid membership, in-app payments, or automatic paid infrastructure assumed |

Browsing public information should not require an account. Recordkeeping and private saving do. A missing DZ can be provisional so the user finishes logging; public directory publication waits for review.

Keep attachments lightweight initially: links to externally hosted media and structured text records. Label manual service dates and experience information with their source. No unlimited media or document hosting is promised.

## Listing and directory maintenance

Include a minimal maintainer workflow to add/edit/retire sourced listings, review submissions, consolidate duplicates, and record source/last-check time. Community suggestions can start with a simple submission/report route rather than a full public publishing system.

Contact and registration links lead to the original provider. Display cancellation/postponement and missing information clearly. Expired dated opportunities leave upcoming results. The directory and board need useful real inventory; a populated-looking demo must not imply real offerings or partnership.

An automatic organizer-claim system is deferred. If someone requests control, preserve the venue identity and handle the request through an explicit manual authority-review policy before granting scoped permissions. Historical logs remain private and unverified by that claim.

## First complete journeys

### Discover and plan

Open the public board → find a relevant activity → inspect source and prerequisites → save to a personal plan after signing in → contact/register externally. Display clearly that an external link or saved plan is not registration confirmation.

### Record a jump anywhere

Select a listed or provisional DZ → enter actual jump details → select equipment actually used → save → view it in the personal logbook, DZ-filtered history, and recorded component-use view.

Count once. Recorded component uses are not assumed lifetime totals when older history is missing. Public DZ pages do not reveal private personal records or claim official operational totals. Users may separately publish selected summaries; these are not extra jumps.

### Follow and coordinate

Find a person → follow/request access → view permitted activity → inspect a linked venue/event → optionally share a visit intention. After a jump, preview a summary and explicitly choose whether to publish. No background GPS tracking, automatic live presence, or booking guarantee is involved.

### Keep records portable

Export personal logs, gear, and relevant references → restore into a clean test account/store → verify relationships and dates. Restoring repeatedly must not duplicate entries. Recovery must work before inviting users to keep their sole copy of important records in the app.

## Deferred capabilities

- FlySight/GPX/FIT imports, advanced debriefing, and direct device connections.
- Paper-logbook recognition and broad third-party log migrations.
- Live forecast integration; external weather-resource links can be used without claiming synchronized conditions.
- USPA/Aspire credential retrieval, formal progression/signatures, and automated currency acceptance.
- Mutually confirmed ownership transfers, disputed claims, automated lost/stolen matching, and manufacturer notice matching.
- Provider self-service portals, live calendars, accepted coaching/event bookings, waitlists, payments, and refunds.
- DZ check-in, manifest, staff/aircraft allocation, and verified completion feeds.
- Global algorithmic feeds, comments/reactions, participant tagging, direct/group chat, live presence maps, public visitor totals, marketplaces, paid placements, and hosted video processing. The proposed small following feed and deliberate sharing are separate from these extensions.

These remain in the [feature catalog](feature-catalog.md). Deferral does not delete the longer-term ecosystem vision. Which comes next should depend on actual use and feedback.

## Release conditions

- Usable, sourced discovery inventory in a defined initial area or discipline; scope and maintenance ownership agreed before launch.
- Clear private/public separation, account permissions, recovery, and basic abuse/submission controls.
- If social scope is included: server-enforced audiences/blocking, unpublish behavior across views, post moderation, and no location disclosure from private records.
- Accurate identity/reference handling, corrections, duplicate prevention, time/units, and personal exports/restores.
- Durable storage and tested backup/restore process; browser-only data must not silently be the only copy.
- Bounded usage and hosting verified against the chosen free plan; cost and availability limitations communicated.
- Existing prototype defects are fixed for routes actually used, or broken operational features are excluded from the release and their backend permissions constrained. Merely hiding a menu is insufficient.
- Browser and persistence checks cover the actual journeys. No deployment or release validation has yet been performed for this proposal.

## Unresolved scope choices

The initial geography/discipline, listing sources, personal attachment allowances, exact mandatory log fields, whether calendar export fits the first cut, and hosting choice remain open. FastAPI Cloud/Neon are candidates, not deployed services. This document is the proposed user-facing scope; the [roadmap](roadmap.md) remains the broader opportunity sequence.
