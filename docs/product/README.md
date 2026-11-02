# Load Organiser product documentation

Status: selected beta planning baseline, 2026-11-02. The implementation assessment describes the earlier prototype at `1f805de`; subsequent dependency maintenance is separate.

Load Organiser is intended to become a shared skydiving ecosystem: participating dropzones use the same application, while jumpers carry their identity, logbook, statistics, and recent-activity records between locations and book jumping opportunities.

The repository currently contains an early load-management prototype. The intended ecosystem and most capabilities below are not implemented.

Selected frontend direction: a mobile-friendly SvelteKit/TypeScript website, retaining FastAPI and PostgreSQL. The repository still implements React; see the [transition document](svelte-transition.md). Architecture and hosting targets are selected in the [architecture decisions](architecture.md); implementation and deployment remain untested.

## Current discovery scope

The product owner confirmed that no dropzones are ready to participate and selected the skydiver-first audience direction, followed by later dropzone adoption. Demand remains unvalidated; first-beta product decisions are now selected under delegated expert judgment. Work has progressed from discovery documentation to an authorized phased roadmap and GitHub issue breakdown; implementation and partner recruitment have not started. P0 planning is complete; the first implementation slice is #144 in the [Claude Code handoff](claude-code-handoff.md).

Keep collecting evidence while narrowing the release scope explicitly. Proposed pilot journeys remain future options; no participating operators or paid services are assumed.

Confirmed discovery coverage is Europe first, with initial DZ/opportunity listing maintenance and corrections handled by the product owner. Personal logging is not geographically restricted. Current product work is planning and documentation only; implementation will be delegated to Claude Code separately. The separately authorized dependency refresh is tracked in [PR #170](https://github.com/metalcorpe/load-organiser/pull/170), not as delivery of these product features.

## Reading guide

Start with the [connected product model](product-model.md) to understand how features fit together, which records they share, and where their responsibilities differ. Feature-detail documents expand that model; the roadmap remains conditional.

For the selected initial beta cut, read the [release brief](release-brief.md): concrete fields, social rules, attachment limits, European source candidates, owner responsibilities, and maintenance/release gates. The [decision sheet](beta-decisions.md) settles product scope; measured operating limits and release evidence remain outstanding.

Review the [mobile journeys and clickable mockup](mobile-journeys.md) for navigation, private/public choices, recovery and error states. It is a design artifact, not a running product.

For actionable next work, use the [Claude Code handoff](claude-code-handoff.md), [architecture](architecture.md), [data contracts](data-contracts.md) and [delivery plan and GitHub backlog](delivery-plan.md). It separates six V1 planning/delivery phases from future ecosystem investigations.

| Document | Purpose |
| --- | --- |
| [Architecture decisions](architecture.md) | Selected runtime, hosting, session, boundary, quota and recovery design; feasibility gates |
| [Data contracts](data-contracts.md) | Ownership, dates, history, publication, concurrency and bounded restore invariants |
| [Claude Code handoff](claude-code-handoff.md) | First implementation dispatch, route inventory, repository inputs and evidence by issue |
| [Connected product model](product-model.md) | Feature ownership, shared concepts, integration flows, journeys, and reconciled dependencies |
| [Delivery plan and GitHub backlog](delivery-plan.md) | Phase epics/milestones, scoped issues, dependencies, and the immediate next actions |
| [First-beta decisions](beta-decisions.md) | Selected scope, prior-history and restore rules, deferred features and planning completion |
| [Two-pass product review](product-review.md) | Value/adoption risks, corrected journey friction and unresolved product decisions |
| [Mobile journeys and walkthrough](mobile-journeys.md) | Seven phone journeys, clickable design mockup, error/accessibility matrix and review tasks |
| [Initial beta release brief](release-brief.md) | Concrete recommended first cut, confirmed decisions, source policy and planning handoff |
| [Proposed first version](version-one.md) | Discovery plus personal jump/gear records, explicit exclusions, and release conditions; current selection in the decision sheet |
| [Vision and user journeys](vision.md) | Product direction, users, shared records, and local control |
| [Skydiver-first adoption](adoption-strategy.md) | Independent user value, participation dependencies, and the later path to dropzones |
| [Sustainability and community support](sustainability.md) | Free-core proposal, voluntary support, sponsorship, advertising trade-offs, and operating costs |
| [Stack and cost options](stack-cost-options.md) | Existing stack versus serverless/local-first options, migration costs, and unresolved compatibility |
| [Svelte transition assessment](svelte-transition.md) | Frontend migration boundaries, reusable code, rendering/auth choices, and proposed sequence |
| [Mobile strategy](mobile-strategy.md) | Responsive mobile-friendly website first; PWA, offline, push, and native apps as later options |
| [Feature catalog](feature-catalog.md) | Proposed capabilities, scope, dependencies, and acceptance examples |
| [Discovery board](discovery-board.md) | Events, boogies, coaching, schools, listing sources, freshness, and later registration |
| [Social activity](social-activity.md) | Following jumpers, shared jump cards, venue activity, visit intentions, and privacy |
| [Dropzone directory and jump attribution](dropzone-directory.md) | Logging at unregistered DZs, provisional venues, duplicates, later claims, and privacy |
| [Gear ownership](gear-ownership.md) | Serial-number inventory, ownership claims, supporting evidence, transfers, and privacy |
| [USPA integration research](uspa-integration.md) | Approved API precedents, member-sharing opportunities, access limits, and unresolved questions |
| [Other integration opportunities](integration-opportunities.md) | Device formats, weather, equipment notices, lost/stolen references, and personal workflow connections |
| [Needs and discovery backlog](needs-discovery.md) | Needs to investigate, missing detail, and further documentation work |
| [Market research](market-research.md) | Competing platforms, standalone products, and source links |
| [Implementation assessment](implementation-assessment.md) | Code findings, earlier validation results, and limitations |
| [Roadmap and validation](roadmap.md) | Proposed delivery sequence, pilot experiments, and open decisions |

## Evidence and decision labels

- **Established intent:** explicitly requested by the product owner in the discovery conversation.
- **Observed:** supported by repository code or an executed check described in the assessment.
- **Vendor claim:** published by a product provider; not independently tested here.
- **Proposal:** a suggested design, feature, or delivery sequence requiring product decisions.
- **Hypothesis:** an assumption requiring evidence from users or operators.

Established intent includes the shared dropzone ecosystem, portable jumper statistics and logbook, currency records, booking, forecasts, flight-record imports, and exploring additional standalone-product capabilities. Suggested priorities, business models, data entities, and acceptance examples are proposals.

## Working interpretation of currency

Currency means recent jumping activity relevant to a receiving dropzone's eligibility review. This interpretation has not been explicitly confirmed. Financial balances or transferable jump credits are a separate, unresolved scope; do not silently combine them with activity currency.

## How to maintain these documents

Update implementation status when behavior changes, preserving the distinction between proposals and delivered functionality. Date external research and verify prices again before commercial decisions. A listed competitor capability demonstrates a published offering, not market demand, adoption, or willingness to pay.
