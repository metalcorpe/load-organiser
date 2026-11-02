# Product review — two passes

Status: review of the [release brief](release-brief.md), [mobile journeys](mobile-journeys.md), [mockup](mockups/mobile-walkthrough.html) and adoption assumptions. Two analytical passes by the same reviewer, not two independent reviewers or user research. Findings are judgments grounded in those artifacts; no measured demand, usability result or competitor superiority is claimed.

## Verdict

The skydiver-first direction is coherent: discover an opportunity, keep a private plan, log an actual jump at any DZ, and optionally share a selected summary. The proposed relationships support that loop without requiring operator participation.

The current beta bundle is too broad to treat as one validated launch promise. It combines a maintained directory, five opportunity/provider categories, a personal record system, a small social network, ownership/service records and restore-conflict tooling. Connecting those records is useful, but the connection itself is not evidence that users will switch or return. The next product decision should establish which part of the loop earns initial and repeated use, rather than adding another feature.

## Pass 1 — value, adoption and sustainable scope

| Priority | Finding and artifact evidence | Product consequence | Recommendation and status |
| --- | --- | --- | --- |
| High | The release brief gives discovery, logging and social activity equal launch weight; the adoption strategy explicitly calls return reasons hypotheses | Different users can enter for different reasons, but the product has no demonstrated primary reason to return | Use discovery → private log → selected sharing as the working loop. Validate independent discovery/record value and optional social value separately. This is an evaluation framework, not a deletion of agreed features |
| High | Discovery depends on real maintained content; the empty feed depends on approved connections and deliberate publishing | A new user can see two empty experiences before doing anything useful | Do not force a feed-first home. Offer useful discovery plus direct logging; test whether a small connected group can use existing profile links and selected summaries. Seed only real permitted listings, never fabricated community activity |
| High | Manual logs start with recorded totals; external-history import is deferred and no prior-history bridge exists | An experienced jumper may feel asked to start over, even if the new log works correctly | Decide whether to add a self-declared prior-jump baseline, or a genuinely needed importer later. Recommendation only: a baseline must have a cutoff, avoid double-counting older entries, stay separate from detailed recorded history, and never claim verified currency. Do not fabricate historical jump entries |
| High | The owner maintains Europe-wide listings and handles social reports; the proposed cadence has no measured time budget | Coverage expansion could consume the only maintainer's capacity and produce stale content | Keep Europe as the boundary, but publish actual country/category coverage. Before launch, rehearse sourcing and review with the owner, record time and unresolved items, and limit enabled coverage accordingly. Do not treat weekly/60-day defaults as validated staffing capacity |
| Medium | The same beta includes public intentions, follower history and a full restore merge/conflict interface | These add release obligations beyond finding and recording a jump | Candidate sequencing: preserve private saves/plans, basic export and tested recovery; evaluate shared intentions and rich restore-conflict choices after the core loop. No backlog task is removed or dependency changed by this recommendation |
| Medium | Hosted media is deliberately excluded; the social proposition therefore relies on text and external links | A usable private log may still be too weak a reason to maintain another social feed | Test selected summaries with the intended small group before investing in reactions, video, algorithms or media hosting. Keep the cost boundary unless evidence supports changing it |
| Medium | Offline use is deferred, but failed-save handling retains input only in the current page | A logging product can lose trust if its actual users cannot reliably finish a log in their normal environment | Test the real logging context/connectivity before asking users to rely on it. Clear uncertain-save behavior and duplicate protection are required. Durable drafts remain a decision if observed failures justify them, not an automatic PWA/native commitment |

No country inventory, activation target, maintenance-time budget, willingness to pay or retention rate has been invented. Those need evidence, not additional planning detail.

## Pass 2 — journey friction and rule consistency

| Priority | Finding | Resolution in this revision |
| --- | --- | --- |
| High | J2 and the guided mockup journey lead with Add gear, although the release brief says equipment is optional (the Add jump tab already skipped that step) | Corrected: the guided journey now starts with the minimal log too. Gear is reached from Records or an optional Add component branch; no owned rig, serial or gear record is required |
| High | Every private jump edit unpublishes its shared card, including an unrelated note/gear correction | Corrected: changes confined to unshared fields leave the selected summary unchanged. Changes to fields actually included in the summary withdraw it before committing the relevant source change; deletion also withdraws it. Republish from a fresh preview |
| Medium | Save is styled as the event's main action and is labeled a private plan, despite no date/intention being chosen | Corrected: the external organizer action is directly available and visually primary. Save creates a private bookmark; a separate Plan a visit action creates a dated private plan. Account creation is not a prerequisite for opening the organizer link |
| Medium | Activity/Records/Profile mockup tabs substitute guided scenarios for actual section destinations | Corrected in the design: Records gets a small logbook/gear/saves hub; Profile gets private account controls; Add jump stays direct. Guided Previous/Next controls are explicitly reviewer controls, not the product's primary navigation |
| Medium | Opt-in profiles and follow approval protect privacy, but people search alone is a weak route to an existing friend | Clarified: a user may manually copy/share their opted-in profile URL or handle outside the application. No platform invitation sending, contact upload, direct messaging or discoverability bypass is introduced |
| Medium | Approved-followers audience does not explain access for people approved later | Clarified proposed behavior: the current approved-follower set can read existing follower summaries, including newly approved followers. Removing/blocking a follower revokes that audience access. Explain this when choosing the audience; a public summary is independently public |
| Medium | Product copy exposes terms such as canonical venue and component-use counting before describing the user's outcome | Simplified mockup wording: listed dropzone, equipment used, saved opportunity. Keep technical identity and audience constraints in implementation/design notes, with short contextual explanations in the actual flow |
| Medium | A provisional venue may be saved privately but cannot yet appear in a venue-linked shared card | Clarified: save the private jump immediately, optionally share without the venue, and separately suggest the venue for review. Public directory review never becomes a condition for keeping the personal log |
| Medium | Browser-based mockup checks can be mistaken for proof that the product works | Retained explicit limits: illustrative data, guided transitions, no real accounts/storage/API permissions, no task-acceptance result. Screen traversal does not validate user motivation, form completion, accessibility or backend privacy |

## Recommendation before implementation handoff

1. Review the corrected minimum logging and discovery flows first. Ask a jumper to explain what they gain without any friends or DZ operators joining.
2. Ask an experienced jumper how much history they would need to carry over. Decide the baseline/import bridge before investing in elaborate profile or statistics screens.
3. Run a real maintainer sourcing/review exercise for the intended discovery queries. Narrow the visible inventory/categories if the owner cannot maintain them; do not quietly narrow the confirmed Europe-wide eligibility for listings.
4. Review the smallest useful social group and its sharing behavior. Decide explicitly whether shared future intentions belong in the first beta; keep the existing tasks conditional until that choice is accepted.
5. Test the corrected journeys with representative users. Record misunderstanding, missing value and abandonment reasons before interpreting task completion as a success metric. Ask whether they would use the product again and why; stated intent is still not measured retention.

#141 owns audience, history-bridge and sequencing decisions. #142 owns the revised walkthrough and actual owner/user acceptance. #143 must preserve the corrected private-versus-shared edit boundary and audience semantics. #151/#162 own actual coverage/maintenance evidence; #153/#157 carry the logging/sharing corrections. Existing phase/dependency assignments are unchanged.

## What this review does not establish

No interviews, user recruitment, operator participation, maintenance rehearsal, network-context observation, prototype task acceptance or market experiment has been completed. Recommendations about narrower sequencing, historical baselines and social value remain proposals. Architecture should respond to the accepted product choices; it should not silently settle them through implementation.
