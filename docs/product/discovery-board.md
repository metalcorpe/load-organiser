# Events, boogies, coaching, and schools board

Status: feature proposal raised by the product owner. The provider and dated-opportunity backend is implemented by #149 and the public board, detail pages, private saves and visit plans by #150 (see [Implemented in #149](#implemented-in-149) and [Implemented in #150](#implemented-in-150)); maintenance tools and submissions by #151 (see [Implemented in #151](#implemented-in-151)); real inventory is not. No participating organizers or accepted listings are assumed.

Confirmed coverage: Europe first. The product owner will maintain the initial DZ and opportunity listings and handle corrections. The [release brief](release-brief.md) proposes primary-source candidates and a review cadence. Real country inventory, reuse permissions and maintenance capacity remain unvalidated; comprehensive European coverage is not assumed. Personal logging remains available for locations worldwide.

First beta follows [the selected decisions](beta-decisions.md): dated events/boogies/camps/courses and related DZ/basic provider information. Standalone coach/school directories remain later scope; the broader category catalogue below is retained for the ecosystem vision.

## Purpose and fit

Help skydivers discover where to jump, learn, and train. The board can provide value through clearly sourced listings and external registration/contact links before venues adopt the full application. It is a potential route for coaches, schools, and organizers to participate in a smaller workflow first.

Hypothesis: a searchable board organized around date, place, discipline, and prerequisites will help users find relevant activities and return to the app. This is not validated demand. Existing alternatives are noted in [market research](market-research.md).

## Board categories

| Category | Listing type | Important fields |
| --- | --- | --- |
| Events and boogies | Dated gathering, competition, festival, or organized jumping event | Dates, venue, disciplines, organizer, fees, prerequisites, registration link |
| Camps and courses | Structured training with a curriculum or learning objective | Level, objectives, prerequisites, dates, instructors, participant limit |
| Coaching | Ongoing profile and optionally dated availability/offerings | Sky/tunnel, disciplines, levels taught, locations, languages, rate basis, request/contact route |
| Schools | Persistent provider profile linked to specific courses | Training methods/programs, location, instructors where confirmed, languages, contact, sourced affiliation claims |

School profiles and recurring coaching offerings are not single dated events. A coach can teach at several venues; a venue is not necessarily the organizer. Keep provider, venue, event, and individual course/session records distinct.

## Discovery experience

Proposed views: list, calendar, and map. Filter by date range, distance/country, sky versus tunnel, category, discipline, experience level, training language, and known price/currency. Include a beginner/student path and a way to find activities during a planned trip.

A listing shows source, organizer, venue, dates/time zone, intended audience, stated prerequisites, price basis, registration/contact route, status, last source check, and whether the organizer manages it. Missing or unconfirmed information is visible. A venue association alone must not imply endorsement.

Users can save listings, follow a provider, export calendar entries, and optionally subscribe to changes or filtered alerts. Notification preferences need scope/frequency controls. Adding to a calendar or selecting “interested” does not register the person.

## Initial listing sources and publication

- A user may submit a sourced discovery listing for moderation, even if the organizer is not a user.
- An organizer may create a listing or request control of an existing listing through an identity/authority review.
- External material can be summarized with attribution and a source link where permitted; third-party images, descriptions, contact data, and feeds are not assumed reusable.
- Retain source identifiers, publication attribution, and corrections; consolidate duplicates rather than publish competing copies as separate activities.
- An organizer claim confirms management authority, not coaching qualifications, federation recognition, or quality of instruction. Represent each separately if checked.

Documented source-backed listings should be labeled separately from organizer-maintained listings. Do not label an external venue as a participating dropzone merely because its events appear.

## Listing freshness and lifecycle

Proposed states: draft, pending review, published, postponed, cancelled, and archived. Track schedule revisions and distinguish an unknown date from a confirmed date. Date-limited activities leave upcoming views after their end; school profiles and ongoing offers need a separate review/reminder policy.

Capacity indicators should show their source and check time. “Available,” “full,” or “waitlist” must not be inferred from stale external information. Subscribe interested users to confirmed changes only under their notification preferences. Maintain a report/correction route for outdated, fraudulent, or misleading listings and a process for disputed organizer claims.

## Discovery versus transactions

Initial candidate scope: browse → inspect source and prerequisites → save/share → contact or register externally. This needs no live slot inventory, payment collection, or manifest integration.

Optional later scope: organizer-managed inquiries, applications, approval, waitlists, paid registration, and booking. Those depend on participating providers and defined responsibilities. An inquiry is not acceptance, an RSVP is not a booking, and a purchased course place is not an aircraft load assignment.

Personal profile data can help suggest relevant activities or prepare an application. Do not automatically disclose private logbook, equipment, qualifications, or contact details to an organizer when the user browses, follows, or saves a listing. Eligibility suggestions are not organizer acceptance.

## Connection to other features

- Saved destinations and forecasts support trip planning; forecasts do not predict whether an event will operate.
- Logbook experience and personal goals can support transparent filters without claiming automatic qualification.
- An accepted course may later connect to coaching feedback and attributable progression records.
- Completed participation may suggest a logbook link, but an event attendance record must not manufacture completed skydives.
- Provider profiles and limited organizer tools offer a possible adoption route before full dropzone operations.

## Acceptance examples for later design

- A student can find an introductory course without interpreting a high-experience camp as suitable.
- A jumper can save a boogie at a nonparticipating location, open the official registration link, and see that the app has not registered them.
- A travelling coach has one provider identity linked to several dated offerings without duplicate profiles.
- Two submissions of the same event are reviewed and consolidated with their source history preserved.
- An event postponed across time zones produces the correct calendar revision, with change notifications only to subscribed users.
- A school profile distinguishes a provider's self-declared affiliation from a specifically checked credential.
- A listing with unknown current availability shows “check with organizer,” not bookable inventory.

## Open discovery questions

- Which initial audience needs this most: local regulars, traveling jumpers, students, or specialist disciplines?
- Is demand mainly for dated events, nearby coaches, or finding a school?
- Which countries within Europe, disciplines, and languages make a useful initial inventory?
- How much freshness/moderation work can the product owner maintain, and what review cadence is practical?
- What evidence is enough to allow organizer control, credential labels, or affiliation labels?
- Are source-linked listings sufficient, or do users need a response/registration workflow?
- How should recurring courses, uncertain dates, weather disruption, and cancelled providers be represented?
- Could sponsorship fund the board without obscuring relevance? Any promoted placement would need clear labeling; no revenue model is selected.

Related: [F10 in the feature catalog](feature-catalog.md), [adoption strategy](adoption-strategy.md), and [needs discovery](needs-discovery.md).

## Implemented in #149

Backend only: `backend/app/skydiver/opportunities/`, API under `/api/skydiver/v1`. The board, detail pages and saves are #150.

| Area | Behaviour |
| --- | --- |
| Provider | Person or organization offering an activity; distinct from venues. Name, kind, optional country and website, `source_url` + `checked_on` (required to publish). States `draft`, `published`, `archived`; `merged` only through a reviewed merge, which moves its listings to the survivor and keeps the old ID resolving. No account link, contact person, credential, affiliation or claim fields |
| Opportunity | Category `event`, `boogie`, `camp` or `course` with one provider (organizer) and an optional public venue (merge-resolved when read; a venue filter also finds listings attached to venues merged into it). Country, optional location note, disciplines, audience (`students`, `licensed`, `experienced`), ISO 639-1 languages, summary, prerequisites as stated, optional price (amount + currency + basis `per_person`/`per_jump`/`per_day`, plus note) |
| Schedule | Inclusive start/end calendar dates with an IANA location zone (`Europe/Madrid`, not `UTC` or offsets). Expiry is the end of the end date in that zone; ended listings leave search but stay readable by ID marked `ended`. Unknown dates are allowed only while postponed; they never expire and sort last. Postponing clears the announced dates (kept in history), so a postponed listing never expires on its old schedule |
| Lifecycle | `draft` → `review` → `published` → `postponed`/`cancelled` → `archived`; archived can return to draft. Public: published, postponed, cancelled. Publishing requires source + last check, external registration/contact URL, a published provider, a public venue or location note, and dates (except postponed) |
| Duplicates | A reviewer marks one listing a duplicate of another (final). Its ID resolves to the kept listing with `replaced_id`; the duplicate's source URL is recorded in the kept listing's history. A public listing cannot be consolidated into a non-public one. Nothing is merged automatically |
| History | Every change is a reviewer-only event (`created`, `updated`, `rescheduled`, `status_changed`, `duplicate_of`, `provider_merged`, …) with the acting account. Public responses have a fixed field set with no account, history or internal state (tested). An ended listing whose organizer is no longer published shows no organizer |
| Not represented | Capacity, availability, waitlists, acceptance, bookings or payments; ongoing coach/school offers (beta decisions); organizer self-service; calendar export. A listing links out to `registration_url` only |

No provider or opportunity data is shipped. Real inventory, source reuse review and maintenance effort are #151/#162 evidence.


## Implemented in #150

Web: `/` (board), `/events/{id}`, `/organizers/{id}`, upcoming listings on `/dz/{id}`; private `/saved` and `/plans` under Records. Backend: `backend/app/skydiver/saves/` (`/saved`, `/plans`).

| Area | Behaviour |
| --- | --- |
| Board | Server-rendered list with title/organizer search and type, country, discipline, audience and date filters held in the URL (shareable, back-button safe). Unknown filter values are dropped. Empty results say coverage is limited and offer Clear filters; they never widen the search. Upstream failure shows an error, not an empty board |
| Detail | Organizer and venue shown separately; dates with their local zone or “Dates not announced”; prerequisites quoted as stated by the source; price or “Not stated”; “Availability is not tracked here”; source link and last check. Postponed, cancelled and ended listings say so. The primary action opens the organizer's registration page; the page states registration happens there |
| Save | Guests see “Sign in to save this privately”, which returns to the listing with `?save=1`; the listing and its current status are shown again and the save happens only when the person presses Save privately. Saving is idempotent (`PUT`), needs a confirmed email, and shows “Saved privately — you are not registered.” A withdrawn listing stays in the saved list under its saved title as “No longer published”; a consolidated duplicate shows the kept listing |
| Plans | Separate from saves. Title, first/last day (calendar dates, at most a year), optional private note, and at most one link: a public listing, a public dropzone or the person's own private place. A plan keeps its own dates; when the linked listing's dates differ, both are shown. Deleting a private place keeps the plan |
| Privacy | Saves and plans are owner-only (`owner_person_id` predicate in SQL, 404 for foreign IDs) and never appear in public responses, counts or organizer/reviewer views. All responses and pages are `no-store` |
| Limits | 200 saves and 100 plans per person (working defaults, not measured). The web transport accepts up to 4 MB for these lists and 1 MB for a board page (20 listings requested) |

Not built here: calendar export, alerts/subscriptions, following providers, map/calendar views, Report a correction (#151), and any shared intention (#159).

## Implemented in #151

Web: `/review` (reviewer dashboard, linked from Profile for reviewers only; others get 404), editors at `/review/listings/{id|new}`, `/review/organizers/{id|new}`, `/review/dropzones/{id|new}`, the queue at `/review/submissions`, and `/submit` for members. Backend: reviewer queues `GET /directory/{venues,providers,opportunities}`, `app/skydiver/moderation/` (`/submissions`, `/directory/submissions`).

| Area | Behaviour |
| --- | --- |
| Maintenance | Reviewers create, edit, publish, postpone, cancel, archive and consolidate listings; create, publish, archive and merge organizers; create, rename, alias, close and merge dropzones. Every change is a history event with the reviewer account |
| Concurrent edits | Each record has a `version`. Editors send the version they loaded; if someone saved in between, the change is refused (`edit_conflict`) and the form keeps the typed values to copy. No row locks: archiving or merging an organizer and publishing one of its listings cannot both succeed (`listings_version`) |
| Review cadence | Dashboard "due" lists: public listings starting within 30 days not checked for 7; postponed listings not checked for 7; published organizers and listed dropzones not checked for 60. Ended listings leave public results automatically; expiry is not a source check |
| Submissions | Signed-in, confirmed members send a listing or dropzone suggestion, or a correction/report about a public listing, organizer or dropzone (linked from each public page). Limits: 10 a day and 20 waiting per account; a retry of the same form is not a duplicate. Intake is off unless `SKYDIVER_SUBMISSIONS_OPEN=true`, so the owner can pause it. Reviewers see content, not the sender; the sender sees status and the reviewer's note. A submission never edits a record by itself |

### Maintenance and claim policy (beta)

- **Ownership.** The product owner holds the `reviewer` role and is the only maintainer. The cadence above is an operating default; record actual time spent per cycle for #162 and reduce published coverage if it does not fit. If the queue outgrows the time available, pause submissions (`SKYDIVER_SUBMISSIONS_OPEN=false`) and stop adding coverage; existing listings, saves and private records stay usable.
- **Source checks.** `checked_on` is updated only after the reviewer has looked at the source. Automatic expiry of ended listings never counts as a check.
- **Representative claims (manual).** There is no claim feature or organizer account in the beta. Someone who says they represent an organizer or dropzone uses a correction submission. The reviewer confirms authority through an independent channel (the contact published on the organizer's or dropzone's own site) before relying on it, then applies the change themselves with that source noted. A confirmed representative gains no account permissions and no access to anyone's saves, plans, private places, logbook, submissions or the identity of who saved, planned or reported anything.
- **Demo data.** None is shipped. Any record created for a demonstration must have a title starting with `[Demo]`, must not be published on a public deployment, and must never name a real organizer or dropzone as a partner.
- **Initial coverage.** Populating real European listings from permitted sources is owner work outside this code change: record the countries, categories, sources, reuse terms checked and time spent before launch (#162).

Not built: automated source fetching or imports, organizer self-service, claim workflow, per-field diffs on conflict, and pagination beyond the first 50 items in the editor's organizer/dropzone pickers (search narrows them).
