# Claude Code implementation handoff

Status: ready for a separate implementation dispatch. This document does not start Claude Code or authorize application implementation in the current planning session. P0 scope/design/architecture preparation is complete; public beta readiness is not.

## Read in this order

1. [Beta decisions](beta-decisions.md): authoritative selected scope and exclusions.
2. [Architecture](architecture.md) and [data contracts](data-contracts.md): selected boundaries, session design, runtime targets and transaction rules.
3. [Mobile journeys](mobile-journeys.md), [release brief](release-brief.md) and [clickable walkthrough](mockups/mobile-walkthrough.html): intended behavior and fields. The mockup has no real auth/storage and is not production UI code.
4. [Delivery plan](delivery-plan.md) and the assigned GitHub issue: implement one bounded issue, rather than the whole feature catalog.

Broader research documents contain future options. If they conflict with the selected beta, follow the decision sheet. Record an actual technical incompatibility with evidence before adjusting architecture; do not silently add shared plans, generic imports, payments or a second backend.

## Repository inputs and boundaries

- Work only on an implementation feature branch. Do not reset others' changes or write directly to main/master.
- Planning is in draft [PR #168](https://github.com/metalcorpe/load-organiser/pull/168), branch `docs/product-ecosystem`. Dependency maintenance is separate draft [PR #170](https://github.com/metalcorpe/load-organiser/pull/170), inspected head `4c4af41`. Read their current heads/statuses before choosing a base. Reconcile the accepted inputs on a feature branch; neither PR is assumed merged or approved merely by this handoff.
- The documentation branch still contains the older React application. #170's recorded 59 backend/41 Chromium passes concern that dependency upgrade, not the new Svelte or session architecture. Existing type/lint debt is documented there; do not call it a clean baseline or fix unrelated debt silently.
- Preserve #170's tested Argon2id/new-hash and legacy bcrypt verification semantics, including legacy truncation compatibility. Do not copy the old Passlib integration back into new auth.
- Do not read, print, source, overwrite or commit the untracked root `.env`. Use explicit disposable test settings/credentials and an isolated database. Inspect test bootstrapping before running fixtures: the existing frontend test configuration loads that file automatically. Avoid real mail, production migrations and unknown database URLs.
- GitHub Actions is disabled at repository level; the inherited project workflow is also disabled. Writing correct CI configuration in #147 does not authorize enabling workflows or production deployment. Use local checks meanwhile.
- No application/provider provisioning, card, paid plan, domain purchase, production data intake, public deployment or messages to third parties are needed for the first task. Remove temporary scripts/data when finished; retain intentional source, lockfiles and review artifacts.

## First dispatch: #144 only

Implement [#144 — SvelteKit foundation](https://github.com/metalcorpe/load-organiser/issues/144), after reconciling the inputs above.

1. Create `web/` with compatible stable Svelte 5, Kit 3, TypeScript 6 and the official Cloudflare adapter. Inspect current peers/engines and lock exact resolved dependencies. Use current Kit Vite configuration. Leave `frontend/` as the reference/rollback input.
2. Establish an accessible mobile shell, navigation, public route layout and explicit unavailable/not-yet-implemented states. Match the selected walkthrough's information architecture. Fixture examples must be labeled and isolated from real discovery; do not seed fabricated European listings as live content.
3. Establish server-only request-local native-fetch transport to a fixed allowlisted FastAPI origin and generated public-safe OpenAPI types. Browser bundles contain no credentials, server configuration or mutable SDK token. Add only the minimal real unauthenticated beta health/read contract needed to prove this connection; do not port legacy operations to manufacture a data flow.
4. Add private-route guard scaffolding that denies anonymous access without fabricating login or sessions. Real accounts/sessions are #145. Default dynamic responses to no-store and expose no private records in HTML, page data, errors or share metadata.
5. Build and exercise the actual adapter in a local Workers-compatible preview. Prove deep links, missing/upstream error/loading states and one real API flow against the isolated backend. Record any adapter/runtime incompatibility; a Node dev-server pass alone is insufficient.
6. Publish a reviewable feature PR with route inventory, changed files, commands/results and limitations. Stop at the issue boundary; do not represent static placeholder screens as completed discovery/logbook/social features.

Completion evidence: dependency lock/build, relevant type checks, adapter preview result, API contract/transport check, mobile navigation/deep-link/error checks and absence of secrets/private payloads. Do not require production hosting to complete the shell. If deployment credentials are unavailable, say so; actual free-host feasibility remains #161.

## Route and behavior inventory

Paths below describe route families, not a demand to create empty API endpoints for all future work.

| Surface | Beta treatment / issue |
| --- | --- |
| Discover, dated opportunity, DZ and related provider detail | Public SSR from curated published records; external original registration link, not in-app booking; #148–150 |
| Register, verify, login, logout, recovery and account | Revocable backend session, same-origin cookie/actions, safe return and account switching; #145 |
| Records, gear, jump editor, prior history | Owner-only, optional equipment and private missing venue; #152–154 |
| Saved items and dated plans | Owner-only; bookmark is not attendance, no shared future intentions; #150 |
| Export and restore | Own export, empty-record atomic restore, exact completed repeats do nothing; #155 |
| Person, follow requests, selected cards, activity and venue activity | Opt-in profiles, approved follows, explicit completed-jump projection and backend visibility; #156–158 |
| Listing corrections and reports | Owner as initial maintainer; narrow reviewer access; #151/#162 |
| Aircraft, instructor, manifest/load operations, operational jump/weather/analytics, generic items, blanket user administration and private test-user creation | Excluded from beta router, not ported or presented as working skydiver features; #146. Preserve reference code/tables |

Place new Python feature/use-case modules under `backend/app/skydiver/`, with plain policy and role-sized ports where needed, HTTP/persistence adapters outside, and composition at the application edge. Do not perform a whole-repository architecture rewrite. Use additive migrations and `/api/skydiver/v1`; do not infer personal ownership from an old passenger name/email.

## Subsequent implementation slices

| Issue(s) | Required outcome / decisive evidence |
| --- | --- |
| #145 | Sessions, persistent person identity, verified registration/recovery, expiry/logout/reset revocation, safe account switching. Production-built Origin/cookie checks and two-account isolation; real sender remains a release gate |
| #146 | Backend owner/role/visibility enforcement and explicit beta router. Foreign-ID and direct-API probes, no unsupported legacy exposure; no browser-only authorization |
| #147 | Reproducible isolated build/test/configuration and repository-scoped CI definitions. Document disabled automation; do not silently enable it |
| #148–151 | Canonical/provisional venue separation, dated opportunities/basic providers, private saves/plans and reviewed corrections. Real inventory/source permission and maintenance exercise required before launch |
| #152–154 | Private gear/serials, manual logs and B-before-D history. No gear onboarding prerequisite or verified ownership/currency claim. Test B=200 plus three post-cutoff entries =203; a pre-cutoff detail does not increase it |
| #155 | Consistent versioned export, bounded validation, owner lock, one transaction, reference remap and receipt. Test round-trip, repeat after later edit/delete, nonempty rejection, foreign refs and rollback. Never restore active sharing/roles/follow approvals |
| #156–158 | Opt-in profiles/follows and selected completed-jump cards. Test dynamic follower audience, public anonymous access, both-direction block, unpublish and source-projection withdrawal; private-only edits leave a posted snapshot unchanged |
| #160 | Integrated privacy/recovery/browser regression plus representative mobile/user evidence. Mockups, unit tests and old React test passes do not substitute for real user/device checks |
| #161 | Actual Workers/FastAPI Cloud/Neon compatibility, free-account limits, memory/cold start, email, quotas, migration/rollback and encrypted backup/restore/deletion replay. Record evidence and costs before real data intake |
| #162 | Owner's actual listing/report review cycle, feedback path and bounded beta operating decision; no invented demand or maintenance capacity |

Honor native issue dependencies; this table does not authorize skipping blockers. #159 shared future intentions and #163–167 broader ecosystem features remain future work. Module dependency on gear does not require a user to register gear before logging.

## Cross-cutting acceptance rules

- Policy tests cover dates/units, baseline inconsistency, exact recorded gear use, selected publication projection and audiences. Use a real disposable PostgreSQL database for constraints, ownership, concurrent mutation/restore and rollback checks. SQLite-only evidence cannot establish PostgreSQL transaction behavior.
- Browser tests run the production build for session/Origin behavior and use separate users. Test direct links, anonymous response HTML/metadata, account switch/back navigation and revocation through direct API requests. Include navigation at small mobile widths and keyboard/focus/error behavior; real device/assistive checks remain #160.
- Never imply network timeout means failure. Preserve operation identity for uncertain save retries and expected revision for edits. Reject conflicting writes without silently overwriting.
- Keep calendar dates independent of UTC timestamps. Baseline and serial provenance are private self-reports; activity does not establish clearance, attendance or verified legal ownership.
- Disabling public discoverability withdraws public cards; explain any remaining follower-only audience. Source changes to selected shared fields withdraw atomically before commit and require fresh preview to republish.
- Enforce the architecture's configurable pilot/body/export/storage limits on the backend. These numbers are conservative design defaults, not measured capacity. Reads/export/shrinking edits and recovery must remain possible at growth limits.
- Test deletion, backup recovery and revocation together before production. A personal JSON export is not an operator database backup. Unproven free email or backup storage keeps launch gated, without requiring another planning round for the shell.

Each issue PR should explain the concrete behavior changed, evidence executed, relevant untested limits and follow-ups. Keep product/docs and issue/project status consistent with delivered behavior. Do not mark a phase complete because its UI placeholder exists.
