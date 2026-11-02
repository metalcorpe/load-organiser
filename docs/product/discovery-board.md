# Events, boogies, coaching, and schools board

Status: feature proposal raised by the product owner. Discovery only; no implementation, participating organizers, accepted listings, or MVP commitment assumed.

Confirmed coverage: Europe first. The product owner will maintain the initial DZ and opportunity listings and handle corrections. Exact country inventory, sources, and review cadence are still to be planned; comprehensive European coverage is not assumed. Personal logging remains available for locations worldwide.

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
