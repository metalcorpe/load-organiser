# Needs and discovery backlog

Status: discovery inventory. No participating dropzones, validated customer requirements, or agreed first-release scope are assumed.

## Purpose

Collect the problems the ecosystem might solve before deciding which features to build. The product owner's stated direction is established intent; the user needs below are hypotheses to investigate. Competitor offerings provide examples, not confirmation that our intended users need the same functionality.

The working audience direction is individual skydivers first, with dropzone adoption later. Investigate personal logging, equipment, import/debriefing, and planning needs first while continuing to inventory operator needs for the eventual ecosystem. The initial skydiver segment and MVP are not selected. See [adoption strategy](adoption-strategy.md) for participation dependencies.

## Needs by user

| User | Need hypothesis | Relevant catalog items | Detail still needed |
| --- | --- | --- | --- |
| Traveling jumper | Avoid repeatedly entering identity, experience, and equipment records | F01–F04, F06 | What destinations request, what is reusable, and who accepts it |
| Regular jumper | Keep an accessible history and understand recent activity | F02, F03, F08, F09 | Essential entry fields, summaries, corrections, offline use, and migration |
| Jumper planning a visit | Understand conditions, available activities, and arrival requirements | F05, F06, F10 | Forecast coverage, local updates, reservation commitments, and disruption handling |
| Jumper seeking an activity or school | Find relevant events, boogies, courses, and coaches by date, place, discipline, and level | F10, F11 | [Board categories](discovery-board.md), source quality, current listings, school profiles, notifications, and external registration |
| Student or progressing jumper | Retain goals, feedback, evidence, and attributable sign-offs | F03, F11 | Different training schemes, instructors' responsibilities, and evidence expectations |
| Equipment owner | Identify owned components, preserve acquisition/transfer history, and know what service is due | F04 | Serial matching, ownership evidence, disputes, sharing, service intervals, and rigger workflow; see [gear ownership](gear-ownership.md) |
| Coach or instructor | Understand a participant's experience and connect sessions to progress | F03, F10, F11, F13 | Availability, prerequisites, assessment, sign-offs, and sharing boundaries |
| Rigger | Record completed work and return useful evidence to an equipment owner | F04, F15 | Service details, authorization, corrections, appointments, and record portability |
| Manifest staff | Allocate people, groups, staff, and resources with less repeated work | F01, F06, F07 | Actual constraints, exceptions, concurrent work, public displays, and outages |
| Dropzone owner | Understand operating activity and control local information | F01, F06, F07 | Reports, access roles, existing-system coexistence, cost, and support |
| Event organizer | Coordinate registrations, prerequisites, groups, and changes | F10, F12, F14 | Camp versus boogie versus competition workflows and commercial responsibilities |
| Team or load organizer | Share a jump plan and retain a useful debrief | F08, F12–F14 | Versioning, roster changes, diagrams, media, practice results, and specialist integrations |

Feature IDs refer to the [feature catalog](feature-catalog.md).

## Documentation work to continue now

1. Expand each need into a scenario: trigger, actor, desired outcome, current workaround, and common exceptions. Label unobserved workarounds as hypotheses.
2. Describe feature inputs, outputs, ownership, dependencies, and behavior when information is missing or disputed.
3. Compare competing approaches and distinguish available features from advertised future features.
4. Record candidate import formats and data-provider requirements; avoid promising compatibility without samples and testing.
5. Define terms that could hide different workflows: currency, booking, slot, jump completion, qualification, verification, and credit.
6. Inventory nonfunctional needs: offline use, accessibility, units/languages, record export, correction history, sharing, and operational recovery.
7. Keep alternatives and unanswered questions visible. Do not convert an interesting idea or competitor feature into a mandatory requirement without a decision.

## Suggested structure for future feature detail

- User and problem to investigate.
- Scenario and desired outcome.
- Existing workaround and evidence, if known.
- Candidate behavior and alternative approaches.
- Required data, its source, and who can change or verify it.
- Dependencies and usefulness without a participating dropzone.
- Exceptions, failure cases, and offline behavior.
- Related products and supporting sources.
- Open questions and what would validate the need.

## Later validation options

Interviews, observation, sample-file evaluation, prototypes, and partner pilots can strengthen or reject these hypotheses when access becomes available. None is assumed arranged. The [delivery plan](delivery-plan.md) now tracks immediate scope/UX/technical decisions and conditional implementation issues; no partner participation is a prerequisite for the personal/discovery paths.
