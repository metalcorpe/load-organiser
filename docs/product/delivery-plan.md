# Delivery plan and GitHub backlog

Status: planning and issue organization authorized by the product owner. Implementation has not started. This plan operationalizes the discovery documents without treating every explored feature as committed V1 scope. Scope decisions come first; dates and effort estimates remain unassigned.

Current product boundary: analysis, planning, documentation, and issue preparation only. The separately authorized dependency refresh is prepared in [PR #170](https://github.com/metalcorpe/load-organiser/pull/170); it does not deliver these product features. Implementation will be delegated to Claude Code separately; the implementation issues below are future work, not authorization to begin coding now.

P0 decisions recorded: public discovery starts in Europe, and the product owner will maintain initial DZ/opportunity listings and corrections. Personal records can reference DZs worldwide. The product owner also confirmed responsibility for post/profile reports. The [release brief](release-brief.md) supplies recommended scope, fields, limits, source candidates and cadence for #141 review; actual inventory and maintenance capacity are not validated.

## Tracking

- [Master roadmap #134](https://github.com/metalcorpe/load-organiser/issues/134)
- [GitHub Project](https://github.com/users/metalcorpe/projects/4) (owner-private; repository issues remain public)
- [Milestones](https://github.com/metalcorpe/load-organiser/milestones)

Project fields: **Phase**, **Readiness** (Next / Blocked / Future), and **Status** (Todo / In Progress / Done). Readiness is the planning snapshot, not a substitute for the issue dependency graph. No tasks are marked implemented or done. Unblocking/readiness updates are manual until an explicit automation is configured.

## Phase outcomes

| Phase | Epic | Milestone | Exit evidence |
| --- | --- | --- | --- |
| P0 — Scope and UX | [#135](https://github.com/metalcorpe/load-organiser/issues/135) | [P0 — Scope and UX](https://github.com/metalcorpe/load-organiser/milestone/1) | A bounded release brief, phone-sized walkthrough, and rendering/auth/data decisions are recorded. |
| P1 — Svelte foundation | [#136](https://github.com/metalcorpe/load-organiser/issues/136) | [P1 — Svelte foundation](https://github.com/metalcorpe/load-organiser/milestone/2) | A tested mobile shell and account journey run against an isolated backend; supported routes and legacy exposure are explicit. |
| P2 — Public discovery | [#137](https://github.com/metalcorpe/load-organiser/issues/137) | [P2 — Public discovery](https://github.com/metalcorpe/load-organiser/milestone/3) | A guest can find a real opportunity, inspect its source, and follow an external contact/registration link; missing DZs and stale listings have a usable workflow. |
| P3 — Personal records | [#138](https://github.com/metalcorpe/load-organiser/issues/138) | [P3 — Personal records](https://github.com/metalcorpe/load-organiser/milestone/4) | A user can log a jump at an unregistered DZ with actual equipment, see accurate personal totals, and restore a record export without duplication. |
| P4 — Social activity | [#139](https://github.com/metalcorpe/load-organiser/issues/139) | [P4 — Social activity](https://github.com/metalcorpe/load-organiser/milestone/5) | Two users can follow, share selected activity, and coordinate an intention; private logs and inferred location never leak through feeds, venue pages, or direct API reads. |
| P5 — Beta readiness | [#140](https://github.com/metalcorpe/load-organiser/issues/140) | [P5 — Beta readiness](https://github.com/metalcorpe/load-organiser/milestone/6) | Browser/access-control/restore checks pass, hosting limits and costs are understood, maintenance responsibilities are named, and a small beta has a feedback/rollback route. |

## Scoped tasks

### P0 — Scope and UX

| Task | Depends on |
| --- | --- |
| [#141 — Agree V1 boundaries and initial discovery coverage](https://github.com/metalcorpe/load-organiser/issues/141) | None — initial next action |
| [#142 — Design mobile discovery, logging, sharing and recovery journeys](https://github.com/metalcorpe/load-organiser/issues/142) | [#141](https://github.com/metalcorpe/load-organiser/issues/141) |
| [#143 — Decide rendering, authentication and record boundaries for SvelteKit](https://github.com/metalcorpe/load-organiser/issues/143) | [#141](https://github.com/metalcorpe/load-organiser/issues/141) |

### P1 — Svelte foundation

| Task | Depends on |
| --- | --- |
| [#144 — Establish the mobile SvelteKit shell and reusable API client](https://github.com/metalcorpe/load-organiser/issues/144) | [#142](https://github.com/metalcorpe/load-organiser/issues/142), [#143](https://github.com/metalcorpe/load-organiser/issues/143) |
| [#145 — Port account flows and establish persistent jumper identity](https://github.com/metalcorpe/load-organiser/issues/145) | [#144](https://github.com/metalcorpe/load-organiser/issues/144), [#143](https://github.com/metalcorpe/load-organiser/issues/143) |
| [#146 — Enforce private-record access and isolate unsupported legacy APIs](https://github.com/metalcorpe/load-organiser/issues/146) | [#145](https://github.com/metalcorpe/load-organiser/issues/145), [#143](https://github.com/metalcorpe/load-organiser/issues/143) |
| [#147 — Update CI and repository workflows for Svelte and isolated testing](https://github.com/metalcorpe/load-organiser/issues/147) | [#144](https://github.com/metalcorpe/load-organiser/issues/144), [#146](https://github.com/metalcorpe/load-organiser/issues/146) |

### P2 — Public discovery

| Task | Depends on |
| --- | --- |
| [#148 — Implement canonical DZ directory and provisional locations](https://github.com/metalcorpe/load-organiser/issues/148) | [#147](https://github.com/metalcorpe/load-organiser/issues/147) |
| [#149 — Implement providers and sourced opportunity listings](https://github.com/metalcorpe/load-organiser/issues/149) | [#148](https://github.com/metalcorpe/load-organiser/issues/148) |
| [#150 — Build public discovery pages and private saved opportunities](https://github.com/metalcorpe/load-organiser/issues/150) | [#149](https://github.com/metalcorpe/load-organiser/issues/149) |
| [#151 — Deliver listing and directory maintenance and submission review](https://github.com/metalcorpe/load-organiser/issues/151) | [#149](https://github.com/metalcorpe/load-organiser/issues/149), [#146](https://github.com/metalcorpe/load-organiser/issues/146) |

### P3 — Personal records

| Task | Depends on |
| --- | --- |
| [#152 — Implement private component-level gear inventory](https://github.com/metalcorpe/load-organiser/issues/152) | [#146](https://github.com/metalcorpe/load-organiser/issues/146), [#148](https://github.com/metalcorpe/load-organiser/issues/148) |
| [#153 — Implement personal manual jumps linked to DZ and actual gear](https://github.com/metalcorpe/load-organiser/issues/153) | [#152](https://github.com/metalcorpe/load-organiser/issues/152), [#148](https://github.com/metalcorpe/load-organiser/issues/148) |
| [#154 — Derive accurate personal history and equipment-use summaries](https://github.com/metalcorpe/load-organiser/issues/154) | [#153](https://github.com/metalcorpe/load-organiser/issues/153) |
| [#155 — Implement versioned export and duplicate-safe personal restore](https://github.com/metalcorpe/load-organiser/issues/155) | [#153](https://github.com/metalcorpe/load-organiser/issues/153), [#154](https://github.com/metalcorpe/load-organiser/issues/154) |

### P4 — Social activity

| Task | Depends on |
| --- | --- |
| [#156 — Implement public profile summaries and approved follows](https://github.com/metalcorpe/load-organiser/issues/156) | [#141](https://github.com/metalcorpe/load-organiser/issues/141), [#146](https://github.com/metalcorpe/load-organiser/issues/146), [#153](https://github.com/metalcorpe/load-organiser/issues/153) |
| [#157 — Publish selected jump summaries with audience and unpublish controls](https://github.com/metalcorpe/load-organiser/issues/157) | [#156](https://github.com/metalcorpe/load-organiser/issues/156), [#153](https://github.com/metalcorpe/load-organiser/issues/153) |
| [#158 — Build authorized chronological feed and recent DZ activity](https://github.com/metalcorpe/load-organiser/issues/158) | [#157](https://github.com/metalcorpe/load-organiser/issues/157), [#150](https://github.com/metalcorpe/load-organiser/issues/150) |
| [#159 — Connect saved visits to explicitly shared future intentions](https://github.com/metalcorpe/load-organiser/issues/159) | [#156](https://github.com/metalcorpe/load-organiser/issues/156), [#157](https://github.com/metalcorpe/load-organiser/issues/157), [#150](https://github.com/metalcorpe/load-organiser/issues/150) |

### P5 — Beta readiness

| Task | Depends on |
| --- | --- |
| [#160 — Verify complete beta journeys on mobile and enforce privacy boundaries](https://github.com/metalcorpe/load-organiser/issues/160) | [#155](https://github.com/metalcorpe/load-organiser/issues/155), [#158](https://github.com/metalcorpe/load-organiser/issues/158), [#159](https://github.com/metalcorpe/load-organiser/issues/159), [#151](https://github.com/metalcorpe/load-organiser/issues/151) |
| [#161 — Validate bounded hosting, migrations and backup/restore before beta](https://github.com/metalcorpe/load-organiser/issues/161) | [#160](https://github.com/metalcorpe/load-organiser/issues/160), [#143](https://github.com/metalcorpe/load-organiser/issues/143) |
| [#162 — Prepare community-supported beta content, moderation and feedback](https://github.com/metalcorpe/load-organiser/issues/162) | [#161](https://github.com/metalcorpe/load-organiser/issues/161), [#160](https://github.com/metalcorpe/load-organiser/issues/160) |

## Future investigations — not V1

- [#163 — Device imports, debriefing, forecasts and offline capabilities](https://github.com/metalcorpe/load-organiser/issues/163)
- [#164 — USPA/Aspire credentials, training and verified gear-service workflows](https://github.com/metalcorpe/load-organiser/issues/164)
- [#165 — Provider self-service, course/event registration and payments](https://github.com/metalcorpe/load-organiser/issues/165)
- [#166 — Dropzone adoption and reliable multi-tenant operations](https://github.com/metalcorpe/load-organiser/issues/166)
- [#167 — Advanced community, media, formation planning and competition tools](https://github.com/metalcorpe/load-organiser/issues/167)

## Immediate sequence

1. Resolve [#141](https://github.com/metalcorpe/load-organiser/issues/141): first-release boundaries and useful real discovery coverage.
2. Review the drafted [mobile journeys and mockup](mobile-journeys.md), then accept/update the [mobile walkthrough #142](https://github.com/metalcorpe/load-organiser/issues/142) and [rendering/auth/data decisions #143](https://github.com/metalcorpe/load-organiser/issues/143).
3. Start the [Svelte foundation #144](https://github.com/metalcorpe/load-organiser/issues/144) after those decisions.

Directory/listing and personal-record work can overlap once their actual dependencies are complete. Social publishing requires personal activity and backend audience enforcement. Hosting exploration need not wait to be researched, but public beta data intake must wait for the release/recovery checks.

## Repository and automation notes

The repository initially had no issues or milestones. Existing product documentation is being published on the `docs/product-ecosystem` feature branch for review. The inherited `add-to-project.yml` workflow targeted FastAPI's upstream project and was disabled in GitHub during setup. Other workflows were left unchanged. Repository-specific templates/automation are tracked in the P1 CI task.

Issues have native parent/sub-issue relationships and native blocked-by relationships, plus readable acceptance criteria and documentation links. Future umbrella issues intentionally have no V1 milestone and require re-scoping before implementation.

Related: [V1 scope](version-one.md), [connected model](product-model.md), [adoption strategy](adoption-strategy.md), and [longer-term discovery roadmap](roadmap.md).
