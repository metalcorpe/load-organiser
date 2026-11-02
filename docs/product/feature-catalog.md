# Proposed feature catalog

Status: discovery draft, 2026-11-02. Entries describe intended behavior, not delivered features. Sequencing is proposed in the [roadmap](roadmap.md).

Discovery emphasis: individual skydivers first, then dropzone adoption. Personal records, imports, equipment, and planning should be assessed for independent value; confirmed bookings, local acceptance, and live manifest functions require participation. See [adoption strategy](adoption-strategy.md). No feature bundle is an agreed MVP.

The [connected product model](product-model.md) reconciles responsibilities across these feature IDs. This catalog lists capabilities, not independent products or duplicate record stores.

## F01 — Shared identity, provider roles, and later dropzone membership

One jumper profile can be associated with multiple dropzones. Staff permissions are scoped to the organization where they act. A person may be a jumper at one location and an instructor or staff member elsewhere.

Personal identity does not require a dropzone membership. Provider/organizer roles can support schools, coaches, events, and services before operational dropzone adoption; control of a provider profile is separate from qualification verification.

Acceptance example: staff at A cannot list B's private bookings or loads; a jumper can explicitly share selected personal records with B. Account recovery and duplicate-person resolution must preserve record ownership and attribution.

## F02 — Portable logbook and statistics

Support manual entries, draft entries from completed operational records, and imports. Record location, activity time, aircraft, discipline, equipment, exit/deployment details where known, notes, participants, media, and verification. Statistics include activity over time and breakdowns by discipline, location, equipment, and aircraft.

Link jumps to a stable dropzone directory entry without requiring the operator to register. Missing locations can remain provisional pending review. Listed, claimed, and operationally participating venues are distinct; a later operator claim neither verifies historical entries nor exposes private logs. See [dropzone directory workflow](dropzone-directory.md).

Acceptance example: a device import enriches an existing entry without adding to the jump count. A brought-forward historical total is distinguishable from individually recorded jumps. Offline drafts and export support are proposed.

## F03 — Qualifications, progression, and currency

Record qualifications, issuer, evidence, expiry where applicable, training goals, sign-offs, and recent activity. A receiving dropzone evaluates its own configured requirements and can request review. Keep discipline-specific experience and tunnel activity distinct from total skydives.

Acceptance example: B sees the relevant activity window, data sources, and outstanding requirements. An instructor signs a specific objective; changing its supporting information preserves the original sign-off and triggers an explicit review policy.

Dependencies: F01 for identity/access; F02 supplies activity evidence and currency calculations. Storing an existing qualification or personal goal does not require a completed logbook or participating operator. Formal signatures, schemes, and acceptance policies need separate discovery; local eligibility decisions require the relevant provider/operator.

External credential opportunity: [USPA research](uspa-integration.md) identifies published approval precedents for membership-data and voluntary member-sharing APIs. Access for this application, supported fields, refresh behavior, student progression, and official logbook recognition remain unconfirmed. Personal functionality must remain useful without this integration.

## F04 — Gear passport and service records

Record rigs and components, serial numbers, documents, ownership history where shared, jump counts, inspections, reserve repacks, and AAD service dates. Authorized riggers can record attributable service work. Reminder rules must account for equipment and local requirements rather than a single hardcoded interval.

Proposed ownership extension: register each serialized component independently, retain optional acquisition evidence, and support sender/recipient-confirmed transfers. Initial registration is a self-declared claim; attaching evidence, checking a serial, and confirming a transfer are distinct events. Preserve corrections, handle duplicate/disputed claims privately, and keep full serials and owner identities private by default. See [gear ownership detail](gear-ownership.md).

Acceptance example: a jumper shares selected equipment records before arrival; receiving staff see the source and date of the service entry. Recorded service is evidence for local review, not blanket acceptance.

Extension: rigger discovery, appointment requests, rental equipment, and equipment allocation to operational loads.

Further discovery: manufacturer notices linked to specific equipment and references to existing lost/stolen reports. Public references do not imply an API, complete coverage, verified ownership, or airworthiness. See [connected-data opportunities](integration-opportunities.md).

## F05 — Forecasts and destination planning

Saved dropzones show hourly forecasts, surface winds and gusts, winds aloft, cloud information, visibility, and data timestamps where supplied by the provider. Show the forecast's source, units, altitude reference, and applicable time.

Display the dropzone's published operating status separately. Stale data must be visible. Do not translate a forecast into an unconditional clearance to jump. Initial work should use an external provider rather than developing a weather model.

Acceptance example: the jumper can distinguish a forecast for tomorrow from an observation and from a staff announcement that operations are on hold. Provider coverage, licensing, and cost are unverified.

## F06 — Bookings and cross-dropzone visits

Represent visit reservations, purchased products or jump packages, coaching sessions, event registrations, and specific load assignments distinctly. Support availability, prerequisite review, check-in readiness, waiting lists, cancellations, weather disruption, and booking changes.

Acceptance example: a weather cancellation can change the booking without creating completed jumps. If taking payment, cancellation and refund states remain reconcilable. A reservation does not silently guarantee a particular departure.

Dependencies: F01, local inventory, and an agreed booking policy. Payments, platform fees, merchant responsibility, taxes, and refund ownership remain product decisions; no financial-service design is approved.

## F07 — Manifest and daily operations

Create and revise loads, preserve groups, allocate all relevant occupants, assign instructors/camera flyers/equipment, and track operational status. Support a waiting queue, rapid transfers, public displays, and notifications. Validate assignments consistently across creation, edits, and transfers.

Acceptance example: two staff competing for the final available slot cannot both receive a successful reservation. Moving a group checks every affected constraint and either completes the move consistently or leaves the original assignment intact.

Account for staff turnaround, overlapping aircraft use, unavailable resources, history, and recovery from connectivity interruptions. Optimization remains a separate proposal and cannot substitute for trusted operational rules.

## F08 — Flight-record imports and debriefing

Start with FlySight 1 CSV and FlySight 2 `TRACK.CSV`, with optional `SENSOR.CSV`. Follow with GPX and a documented logbook CSV migration template. KML, FIT, other altimeter exports, and direct Bluetooth/device connections are candidate extensions, conditional on real samples and user demand.

Keep separate workflows for migrating logbook rows and importing telemetry tracks. Use format-specific importers to produce a common internal representation while preserving original files, units, timestamps, quality fields, device information where available, and parser version.

Proposed pipeline: upload → identify format → validate → preview → select segment/match jump → confirm → derive supported charts.

Acceptance examples:

- Reimporting the same file does not duplicate an entry.
- GPS height above mean sea level is not labeled height above the landing area without an explicit reference.
- Ground speed is not labeled airspeed.
- Missing timestamps, accuracy problems, or unsupported measurements appear as limitations; missing data is not fabricated.
- User corrections to suggested exit/deployment segmentation remain possible and attributable.

Initial debriefing: map, altitude/time and available speed charts, notes, and coach sharing. Advanced canopy/wingsuit analysis and synchronized video are later candidates. Compatibility is untested in this repository.

## F09 — Paper-logbook migration

Photograph or upload pages, extract candidate rows, review them beside the original image, resolve ambiguous fields, identify duplicates, and confirm imports. Retain transcription provenance. Allow rollback of an import batch without deleting preexisting entries.

Acceptance example: an uncertain date is flagged for review. A scanned signature remains a source image and is not represented as a new digital instructor signature.

## F10 — Discovery board: events, boogies, coaching, and schools

Discover events, boogies, camps, courses, coaching, and schools by discipline, experience, place, date, and language. Proposed list/calendar/map views support saved listings, source links, calendar export, and optional change alerts. Keep persistent provider/school profiles separate from dated courses/events and venue records.

An initial discovery board can work through sourced listings and external contact/registration links without participating dropzones. Distinguish community-submitted from organizer-managed information; track source, last check, duplicates, cancellation/postponement, and moderation. See [discovery board detail](discovery-board.md).

Later provider-dependent scope: experience summaries, requests, prerequisite review, acceptance/waitlists, registration, schedules, participant groups, and post-event feedback.

Acceptance example: a coach accepts a session request and the booking records its state; acceptance does not allocate aircraft capacity until the local operational workflow assigns it.

A listing is not a confirmed booking, a saved event is not registration, and an organizer-managed profile is not qualification verification. For transactional workflows, future provider participation, supply, cancellation responsibilities, and commercial terms need validation.

## F11 — Training and personal progression

Connect goals, instructor-assigned exercises, learning material, coaching sessions, debriefs, and signed objectives. Support configurable training programs rather than assuming a single national qualification scheme.

Use original, licensed, or linked educational content. Content governance, authorship, and review matter before presenting instructional material as authoritative. Acceptance example: users can distinguish a personal practice goal from a formally signed training requirement.

## F12 — Formation planning and group briefings

Attach diagrams, dive-pool references, group rosters, aircraft slots, briefing versions, and debrief notes to planned jumps. Start with attachments and links; evaluate a native editor after organizer research.

Acceptance example: participants can identify the current approved briefing version for their group. An operational roster change does not silently imply that a formation plan was reviewed.

## F13 — Media and coaching review

Attach photos, video links, or delivered media to jumps, with audience controls and coach comments. Investigate vendor integrations before building automated editing or commercial media delivery.

Acceptance example: buying a tandem media package links the delivered media to the right customer without exposing unrelated participants' private recordings. Storage, retention, consent, and delivery costs require design.

## F14 — Competitions and team practice

Candidate initial scope: participant/team registration, schedules, practice draws, external results, and personal competition history. Integrate specialist scoring when interfaces and agreements allow it.

Official judging, discipline rules, measurement requirements, and approval are separate work. Do not represent internal practice scores as certified competition results.

## F15 — Social activity, community, services, and later marketplace

Proposed small social scope: follow jumpers, chronological permitted-activity feed, explicitly published jump cards, recent shared activity on DZ pages, and optional visit intentions. Logging and saving stay private by default. Audience controls, blocking/reporting, and moderation are prerequisites. See [social activity](social-activity.md) and the proposed [V1 revision](version-one.md).

Later candidates include comments/reactions, consent-based participant tagging, team groups, rigger directories, used-equipment listings, chat, and richer media. No automatic live presence or global algorithmic feed is proposed. Equipment listings and inspection history must not become automatic suitability recommendations.

## Cross-cutting requirements

- Clear source, ownership, permissions, and correction history for shared records.
- Tenant isolation and role checks for all private operational data.
- Import/export and user access to personal history.
- Explicit units, timestamps, local time zones, and altitude references.
- Useful behavior with unavailable networks, interrupted uploads, duplicate submissions, and concurrent edits.
- Avoid public rankings that encourage risky behavior or equate measured performance with competence.
- Integrations remain proposals until access, terms, sample files, and end-to-end behavior are verified.
