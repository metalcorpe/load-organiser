# Vision and user journeys

Status: discovery draft, 2026-11-02.

Current context: no dropzones are ready to participate. The working direction is to target individual skydivers first and seek dropzone adoption later. This document describes the intended ecosystem and hypothetical journeys while feature and needs discovery continues. It does not establish partner commitments or a selected first release.

## Product promise

Initial proposed promise: keep your jumping history, equipment records, and flight data useful wherever you jump, without requiring your dropzone to adopt the application. See [skydiver-first adoption](adoption-strategy.md).

Longer-term ecosystem promise:

Register once, maintain your jumping history, and arrive prepared to jump at participating dropzones.

The application connects personal planning, booking, dropzone operations, completed jumps, and subsequent progression. Load management supplies local operational value; portable records and booking supply value across locations.

## Users and their jobs

| User | Job to support |
| --- | --- |
| Traveling jumper | Reuse personal records and understand what a new dropzone requires |
| Regular jumper | Plan visits, book, follow loads, log jumps, maintain equipment records, and review progress |
| Student | Keep training goals, instructor feedback, and signed progression together |
| Manifest staff | Check readiness, allocate occupants and staff, move groups, and communicate changes |
| Dropzone owner | Run local operations and evaluate whether the software reduces work or improves bookings |
| Instructor or coach | Publish availability, review experience, assign goals, and confirm completed training |
| Rigger | Record service work and supply attributable equipment records |
| Event organizer | Manage prerequisites, registrations, groups, schedules, and waiting lists |

## Connected experience

See the [connected product model](product-model.md) for shared records, feature boundaries, and independent/professional/operator paths. The full journey below is the longer-term ecosystem; individuals can already be served conceptually through external registration and manual/imported activity records without an adopted operator.

1. Discover a dropzone, coach, course, or event.
2. Review forecasts, published operating information, availability, and prerequisites.
3. Book a visit, product, course, or event.
4. Share relevant records and complete the destination's outstanding requirements.
5. Check in and receive an operational load assignment.
6. Complete the jump and review a suggested logbook entry.
7. Attach telemetry, media, feedback, and verification.
8. Reuse the resulting history on a future visit elsewhere.

A booking, an aircraft departure, an individual completed jump, and a logbook entry represent different things. Cancellation or departure must not automatically be treated as proof that every listed participant completed a jump.

## Shared network and local control

Proposal: a common application with isolated dropzone operations and permission-based access to portable personal records.

| Portable record | Local decision or private record |
| --- | --- |
| Jumper identity and selected contact information | Staff roles and operational permissions |
| Logbook and recent activity | Acceptance of experience and eligibility to jump locally |
| Qualifications with issuer and verification history | Local briefings, waivers, and outstanding check-in requirements |
| Gear details and recorded service work | Aircraft, staff, equipment allocation, and load decisions |
| Personal goals, statistics, and selected coaching history | Prices, booking inventory, refunds, and internal reporting |

Each dropzone controls acceptance of records. Shared information is not automatic clearance. Private staff notes and commercial information should not become network-wide merely because a jumper visits another location.

Sharing needs a defined audience, purpose, scope, and duration. Revoking future sharing and retaining an operational record already relied upon are different requirements; their detailed policy remains open.

## Representative journeys

### Travel between two dropzones

A jumper completes jumps at A. A confirms the operational facts recorded there. The jumper books at B and authorizes access to relevant history and documents. B reviews recent activity, requests its local briefing or other missing requirements, and decides whether to accept the jumper. B's completed jumps can subsequently contribute to the same personal history.

### Join a course or camp

A jumper finds an event and submits their discipline experience and equipment records. The organizer reviews prerequisites and accepts or waitlists them. Accepted participants receive briefing information and group allocations. Actual jumps and instructor feedback are attached to their personal history after completion.

### Use the app without a participating home dropzone

A jumper records jumps manually, imports history or device files, tracks gear, and saves destinations. These functions should provide useful standalone value. Imported or self-reported data retains its provenance and does not acquire a dropzone confirmation automatically.

### Review a flight

A jumper uploads a recording, previews recognized data, identifies the relevant segment, and links it to an existing or new draft logbook entry. They review charts and share selected material with a coach. Uploading the same recording again must not duplicate the jump.

## Trust model

Record source and verification separately. A record may be self-reported, transcribed from paper, imported from a device, confirmed by a dropzone, or signed by an instructor. These labels describe different evidence, not a single universal ranking.

Store who confirmed which facts and when. Preserve corrections and distinguish coaching comments from formal sign-offs. A device recording cannot establish the identity of its wearer or completion of a training objective on its own.

## Product hypotheses

- Jumpers will use portable records even before their home dropzone joins.
- Receiving dropzones will find attributable history useful enough to reduce repeated verification work.
- Local operational value will motivate dropzones to adopt before the network is large.
- Coaches and events can connect individual adoption to operator adoption.
- Integration between these workflows will matter more than the number of unrelated features.

These hypotheses are unvalidated. The ecosystem is not yet shown to improve retention, revenue, safety, or operating costs.
