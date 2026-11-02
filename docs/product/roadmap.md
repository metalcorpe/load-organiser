# Proposed roadmap and validation

Status: proposal, 2026-11-02. No delivery dates, effort estimates, or commercial commitments have been approved. Stages express dependencies rather than fixed release promises.

## Execution tracking

The product owner has authorized a phased action breakdown and GitHub issue organization. The [delivery plan](delivery-plan.md) is the actionable sequence for the proposed V1: scope/UX → Svelte foundation → public discovery → personal records → social activity → beta readiness. Its phase numbering supersedes the conceptual stage numbering below for implementation tracking. This document retains the broader discovery/validation context; later integrations remain outside V1 and no code has been implemented by creating issues.

## Current phase — Collect needs and document opportunities

No dropzones are ready to participate. Current work is expanding and organizing the feature and needs inventory, comparing existing products, recording assumptions, and describing workflows and dependencies. See [needs and discovery backlog](needs-discovery.md).

The detailed release cut is a P0 decision, with planning and issue organization now authorized. The stages and experiments below remain broader future possibilities; partner-dependent work is conditional on future participation, not an immediate action item. Do not use these conceptual stages to override the delivery plan's issue dependencies.

The product owner's working direction is to target skydivers first and seek dropzone adoption later. The proposed sequence below replaces the earlier operations-first sequence. See [adoption strategy](adoption-strategy.md).

The [connected product model](product-model.md) clarifies dependencies: discovery and personal records can work independently, and provider participation can precede a dropzone's adoption. These stages are conceptual; basic goals, media links, and shared plans need not wait for advanced tools.

## Stage 1 — Personal records with independent value

Explore portable jumper identity, manual logbook, statistics, personal qualification/document storage, gear records/reminders, history migration, and export. Offline drafts are a candidate requirement. Self-reported and imported facts retain their provenance without assuming a participating verifier.

Future evidence: individuals can maintain and export useful records at nonparticipating locations, understand their sources, and find a reason to return. The first bundle remains undecided.

## Stage 2 — Imports, debriefing, and planning

Evaluate FlySight upload with preview/deduplication and supported charts, forecast information through an external provider, and personal visit preparation. Evaluate paper-logbook scanning if migration effort is a demonstrated blocker.

Also investigate a source-linked [events, boogies, coaching, and schools board](discovery-board.md) as an independent discovery utility. Organizer-managed availability, acceptance, and registration are separate later capabilities; listing and saving opportunities do not depend on a full booking integration.

These functions should work without a partner manifest. Advanced analysis and direct Bluetooth connectivity remain candidate extensions pending user needs and file compatibility evidence.

Future evidence: representative files import accurately, derived metrics expose limitations, and users distinguish forecasts and personal plans from local operating decisions or confirmed bookings.

## Stage 3 — Optional sharing and professional participation

Provide readable summaries, exports, scoped sharing, and opportunities for attributable coach/instructor/rigger confirmations. Personal goals and debrief notes can exist independently; formal sign-offs require a participating verifier.

Also explore provider-managed listings, coaching/school inquiries, course/event acceptance, and feedback where providers choose to participate. These do not inherently require dropzone manifest adoption. Capacity-backed transactions and any payments still need explicit inventory and commercial policies.

Future evidence: users and recipients find shared information useful without needing the recipient to adopt a complete operations platform. Verification, acceptance, and corrections remain distinguishable.

## Stage 4 — Dropzone intake, booking, and operations

Conditional on future operator interest, introduce isolated dropzone workspaces, memberships and staff roles, shared-record intake, local check-in review, and agreed booking workflows. Adoption could begin with one of these workflows rather than requiring immediate manifest replacement.

Before operational use, make the existing load workflow dependable:

Repair creation and missing-function failures. Complete jumper scheduling/editing. Define all-occupant capacity and staff assignment rules. Enforce constraints on every mutation path. Establish operational permissions, change history, and a meaningful isolated domain test suite.

Introduce payment processing only after commercial responsibilities and cancellation/refund policies are agreed. Future evidence: accepted records, bookings, operational assignments, and actual completions remain distinct and traceable; access is isolated; disruptions can be reconciled. PostgreSQL and browser validation are required before real operational use.

## Stage 5 — Deeper event coordination and specialist extensions

Extend earlier discovery, registration, and coaching workflows with coordinated group allocation, briefing versions, operational links, and attributable completion/progression evidence. Link actual jumps into the logbook without counting attendance as skydives. This deep coordination is distinct from the basic provider tools possible in Stage 3.

Exit evidence: an organizer and a visiting participant complete the entire course/event journey without reentering the same core records in separate tools.

Candidate extensions: shared formation plans, media delivery integrations, team practice tools, advanced flight analysis, competition results/scoring integrations, rigger booking, and equipment listings. A global algorithmic social feed and marketplace remain optional; the [small following/activity proposal](social-activity.md) is a separate candidate in the [V1 scope](version-one.md) and does not depend on operator adoption.

Use partner interfaces, attachments, and exports where they solve the job. No external integration is assumed available or authorized merely because the vendor is listed in research.

## Pilot experiments

| Experiment | Evidence to collect | What it tests |
| --- | --- | --- |
| Observe manifest operations | Repeated entry, assignment corrections, conflict resolution, external tools, interruptions | Which local job is worth replacing software for |
| Interview owners and staff separately | Purchase authority, required functions, switching triggers, budget and support expectations | Buyer/user alignment and adoption feasibility |
| Two-dropzone travel pilot | Repeated fields, staff review time, disputed records, privacy misunderstandings | Whether portability reduces real work |
| Independent jumper pilot | Actual return use, migration completion, import corrections, export requests | Whether personal tools supply value before network adoption |
| Coach/event pilot | Requests, acceptance, attendance, feedback, repeated entry, organizer workload | Whether discovery connects to useful participation |
| Paid pilot with explicit scope | Signed willingness to pay, onboarding effort, support demand, continuation decisions | Commercial interest rather than feature enthusiasm |

Define baselines and success thresholds with participants before measuring. No numerical targets have been validated. Observe whether costs merely move from one person or tool to another.

Empty seats alone are an unreliable success metric because demand, weather, and aircraft availability affect them. Avoid treating faster check-in as proof of better safety or shared logbook activity as proof of competence.

## Business-model hypotheses

The product owner is exploring support-oriented funding, free access, community contributions, ads, and Buy Me a Coffee. The [sustainability proposal](sustainability.md) recommends evaluating a useful free personal core, voluntary support, optional later sponsorship, and separately funded professional services. This is not an approved pricing model; dropzone adoption should not be assumed to fund initial operation.

Clarified objective: initially cover operating cash expenses plus contingency and a reserve, without personal income. Funding targets should follow measured costs and net receipts rather than assumed user growth or future dropzone revenue.

- Dropzone subscription for local operations and shared-record workflows.
- Optional paid personal analysis, storage, or convenience tools.
- Booking or event-service fees where accepted by partners and users.
- Coach/rigger service tools if providers demonstrate willingness to pay.

No model is selected. Keep basic record access/export useful; assess whether charging individuals impedes network adoption. Shared monetary balances, multi-dropzone credits, settlement, and foreign exchange require a separate discovery track if requested.

## Open decisions

| Decision | Current working position | Evidence or answer needed |
| --- | --- | --- |
| Meaning of currency | Recent activity; financial credits separate | Product-owner confirmation |
| First audience | Individual skydivers first; subsegment undecided | Compare regular, traveling, progressing, and device-using jumpers' needs |
| Adoption model | Personal value first, professional participation and dropzone adoption later | Independent usefulness, record-sharing value, and later operator interest |
| Trust and acceptance | Record provenance plus receiving-dropzone review | What evidence partner staff accept |
| Booking commitment | Visit/product/event distinct from specific load | Inventory, guarantees, and disruption policies |
| Qualifications | Support multiple issuers/schemes in principle | Initial countries, programs, sign-off requirements |
| Shared data | Purpose-scoped sharing with local operational privacy | Field-level needs, retention, correction/revocation policy |
| Device formats | FlySight 1/2 first; GPX and migration CSV next proposed | Representative files, device mix, desired charts |
| Weather | External provider and separate local operating status | Coverage, licensing, timestamps, cost |
| Payments | Undecided | Merchant role, fee model, cancellation/refund ownership |
| Offline use | Offline personal drafts and operational recovery proposed | Partner connectivity and required outage behavior |
| Integrations | Investigate specialist integrations before rebuilding | Published access, terms, partner agreement, test evidence |

## Current documentation outcome and later validation

Build a connected inventory of needs, candidate features, user journeys, evidence, dependencies, and open decisions. Preserve both standalone jumper capabilities and the longer-term dropzone ecosystem vision without committing to release scope yet.

If partners become available later, one candidate pilot journey is: jump at A → receive an attributable entry → book at B → authorize relevant records → complete local check-in → jump and update history. Independent jumper research is another option; neither is currently arranged.

These experiments should determine the next release scope. The complete feature catalog is an inventory of opportunities, not a commitment to build every item.
