# Beta data and boundary contracts

Status: selected implementation contracts for [architecture #143](architecture.md). They describe required behavior, not existing tables/endpoints or executed tests. FastAPI use cases own these rules. The [product decisions](beta-decisions.md) remain authoritative for scope.

## Records and ownership

Use random internal UUIDs. Owner identity comes from the verified backend session, never a writable owner/role field in a browser or archive. Distinguish internal identity from a jumper's display jump number, equipment serial, provider name or external source ID.

| Record | Identity/access and invariants |
| --- | --- |
| Account/person/profile | Existing account identity may be reused; one stable person identity per account. Email/credentials/private settings separate from opted-in public handle/display name/bio. Roles server-granted, not registration input |
| Session and recovery token | Hashed random secret, account, creation/expiry/revocation. Raw value is never a database field, response after browser session establishment, export or log value |
| Public venue | Stable canonical identity, aliases, country/location/source/status and checked time; retain historical/closed attribution. No operator participation implied |
| Private provisional place | Owner-scoped ID/name/country; usable immediately. Public suggestion is a separate reviewed submission |
| Provider and dated opportunity | Provider identity differs from venue. Opportunity links provider and optional confirmed venue, sourced schedule/time zone/status and original registration/contact URL. Draft until publication fields/provenance are sufficient |
| Personal jump | Owner, activity DATE, venue or provisional reference, type/unspecified, optional jump number/measurements/notes/links and revision/provenance. Never the legacy operational passenger/load row |
| Gear component and recorded use | Owner-scoped type/label/raw optional serial and acquisition/service declarations. Unique component use per jump; referenced component must belong to the owner. Borrowed/rented/unknown descriptions need no other user's private component ID |
| Prior-history baseline | One current owner-scoped B/cutoff D plus correction provenance; never a synthetic jump or gear use |
| Bookmark and private plan | Unique bookmark per owner/opportunity. Dated plans separate, owner-only, optionally linked to a public opportunity/venue or private place; dates ordered and not attendance assertions |
| Published jump summary | Owner/source jump, selected allowed snapshot/fingerprint, audience, publication time and active/moderation state. No future plan publication in beta |
| Follow and block | Unique ordered follow pair; pending/approved. No self-follow. A block in either direction denies authenticated profile/post access and cancels both-direction follows |
| Report and review action | Target/reference/relevant selected snapshot, reason, scoped reporter/maintainer access, decision/time. Not a window into unrelated private logs or gear |
| Mutation/restore receipt | Owner + operation key/hash, request fingerprint, result identity/counts/version/status. Minimal private metadata; cannot replay another owner's operation or resurrect deleted content |

Before returning any personal record, filter by authenticated owner and requested ID together. Before returning any post/profile, evaluate audience, active/discoverable state and both-direction blocks. Pagination/counts/metadata use that same visibility rule; do not fetch all rows and hide unauthorized ones in the browser.

## Dates, measurements and provenance

- Jump activity date, prior-history cutoff and private visit dates are calendar DATE values. Never interpret a historical date as midnight UTC or shift it with the viewer's browser time zone.
- Optional exact activity time requires its IANA time zone; retain the declared local representation/precision and derive UTC only when enough information exists. Creation/edit/publication/session/recovery/operation instants are UTC-aware timestamps independent from activity date.
- A published dated opportunity requires a reviewed schedule and IANA zone for its venue/schedule interpretation; source or sourced-location inference is identified. If the necessary location/time information is unknown, keep it pending instead of inventing it. Date-only end dates are inclusive in that schedule's zone. Cancellation/postponement is source state, not a forecast or availability guarantee.
- Optional manufacture dates retain year/month/day precision. Unknown amounts are null, not zero. Keep entered measurement value/unit/reference and a deterministic normalized value where needed; altitude datum (AGL/MSL/unspecified) is not silently invented. No operational clearance is derived from altitude/service-date fields.
- Current value, source kind (manual, source-backed, restored), author and update revision are distinct. Preserve relevant serial/baseline correction provenance privately. Do not retain full old notes/passwords in a generic audit event store merely to track edits.

## Prior-history calculation

Let B be declared jumps completed before D. Let R be distinct current detailed entries, and A be those dated on/after D. Without a baseline, expose only count(R) as recorded history. With a consistent baseline, reported lifetime total is B + count(A). Detailed pre-D entries remain records and can supply explicitly known gear uses, but are already represented in B.

If count(pre-D detailed entries) exceeds B, keep the entries/baseline and return an inconsistency flag with no combined lifetime total until corrected. Do not reject a saved jump or silently change B. A baseline edit previews the changed total; no signed qualification/currency evidence is generated. Repeated submits, posts, bookmarks/plans and receipts do not change these counts.

## Publication and access transitions

A summary stores only allowed selected values, not a live serialization of the personal jump. Compare the **selected publication projection**, not every source revision: an unshared note/gear edit leaves the card active. An edit changing actually selected fields withdraws the card and commits the relevant source change atomically; deletion removes access too. A fresh preview is required for later republishing. An unrelated private-field addition is never copied into the card.

Follower audience means the current approved set, including later approvals. Explicit removal/block revokes that audience access. Public audience remains anonymously viewable while active; authenticated blocks cannot stop anonymous copies. Turning off public discoverability removes search/public-profile availability and withdraws public cards; existing authorized follower-only content may remain for approved followers. Explain this transition, rather than implying profile hiding automatically hides already shared content from approved followers.

Concurrent publish/edit/delete, follow approval/block, and audience narrowing/read must not bypass the policy through different routes. Use compare-and-swap on a version of the relevant owner or relationship record (row locks in a stable order only where that cannot express the rule), recheck inside the transaction and use database constraints. No route-specific privacy implementation or process-local permission cache. A generic unavailable response must not disclose whether another person's missing item is private, blocked, withdrawn or absent.

## Mutations, revisions and uncertain responses

- Every create/publish/restore action carries a client-generated operation identity preserved for that submission/retry. Backend uniqueness is scoped to the verified owner/action; store a fingerprint of its validated payload.
- A repeat with the same identity and payload returns the completed receipt without another record/count. Reusing the identity for different content is a conflict. Editing an unsent/rejected form creates a fresh submission identity when appropriate.
- Receipt and writes commit in one transaction. A timeout or missing status receipt does not prove the original request failed; the frontend says Save not confirmed and retries/reconciles with the same identity.
- Updates/deletes require the expected revision and fail on a conflict without silent overwrite. Relevant baseline/quota, post-withdrawal and reference changes are in the same transaction.
- Replaying a create after its source was deleted must not resurrect it or return the deleted payload. Return minimal completed/gone status to its authorized owner only.
- Error family: validation 422; malformed format 400; authentication 401; known role denial 403; inaccessible/absent private object 404; revision/identity/nonempty-restore conflict 409; body/byte cap 413; throttling 429 with Retry-After; unavailable/backpressure 503. No SQL trace, private context or credential in an error.

Operation/status endpoints are owner-scoped even if the caller guesses the UUID. Business receipts and counts are not public analytics. Dates/revisions in the response use the documented contract; the browser never supplies an authoritative publication timestamp or effective owner.

## Export format v1 and restore

The logical export envelope identifies the app/format version, UTC export time, owner-scoped personal records, baseline/cutoff, component-use relationships, required public/private location references, bookmarks/plans and relevant provenance. Auth secrets, password hashes, roles, recovery tokens, other people's private records and follow approvals are excluded. Own summary captions/projections may be included as **private historical data**, never instructions to recreate active publications or access grants.

If such historical social data is included, preserve it in a bounded private archive section on restore/re-export; it is not a live post. This does not introduce an archive-sharing UI, new feed activity or moderation-case access. Validate its allowlisted schema and count it in the same personal byte budget. Do not treat an arbitrary whole-account dump as this format.

Export one consistent database snapshot so jumps, gear links, baseline and references agree. The complete canonical compact JSON must fit the architecture's 4 MiB personal-export budget; normal growth checks reserve/enforce that budget instead of discovering at export time that recovery is impossible. Use an authenticated private attachment response with a neutral filename, no public download token or account email in the URL. This personal-record export is not asserted to fulfill every legal data-access obligation.

Restore sequence:

1. Bound the uncompressed raw JSON input to 8 MiB at the web and API boundaries. Do not accept zip/pickle/executable formats, fetch media/source URLs, follow remote references or parse arbitrary log formats.
2. Validate format/version, IDs, record shape/counts, dates/units, reference closure and normalized output byte budget without writes. Provide a count preview and restore eligibility, not a general merge UI. Prior preview is advisory; all conditions are rechecked at commit.
3. Use a raw-file SHA-256 fingerprint plus target owner for exact completed-repeat receipts. Claimed IDs/owner/roles/provenance in the file do not establish authority or verification. Equivalent content reformatted into another file is a different input and cannot bypass empty-record checks.
4. Acquire the owner's transaction lock; all record mutations use the same serialization boundary. Recheck session/reauthentication, existing completed receipt, quotas and emptiness of all restore-managed personal collections. Profile/auth/follow settings do not make records nonempty; logs, components, baseline, saved items/plans and live authored cards do.
5. A completed exact repeat returns Already restored with **no writes**, even if the user later edited/deleted entries. Otherwise a nonempty target is rejected without mutation; never suggest deleting records as a workaround.
6. Allocate target-owned internal identities and map archive references. Never overwrite another account's objects. Resolve only valid current public references; missing/stale/private locations become target-private provisional references or detached private saved-source snapshots, not newly published directory/provider entries.
7. Insert the bounded dataset, private history section, provenance/quota usage and completed receipt in **one database transaction**. No auth roles, approved follows, active cards, verified ownership/credentials or global public entities are imported. A failure rolls back the full mutation/receipt.
8. Return actual counts/receipt; an uncertain response is reconciled by the same owner/fingerprint. A foreign ID collision is not permission to attach or disclose a foreign record.

The database backup recovery process is separate and is governed by architecture A9, including deletion/revocation replay. No browser/file workflow is allowed to replace the entire shared database.

## Account and browser contract

New passwords use a minimum of 15 and maximum of 128 characters, allow Unicode/password-manager paste and have no arbitrary composition rule. Do not trim or normalize passwords into a different secret. Existing shorter credentials remain verifiable at login through the tested legacy adapter; new signup/reset/password-change policy does not invalidate stored accounts automatically. Backend hashing stays on the API process, never the Workers edge.

Browser page data may contain minimal authenticated identity needed for rendering, never the session secret. Auth cookies are HttpOnly; unsafe same-origin actions validate Origin. Explicit account switch/logout clears old private in-memory data, while a safe relative return path can retain a public listing action. Private drafts/serials/restore files never go in URLs, shared caches or server-global clients. No durable offline promise is added.

## Migration and contract verification

Use additive Alembic migrations for the beta modules and explicit public API schemas in `/api/skydiver/v1`. SQLModel/SQLAlchemy objects are persistence adapters, not the policy API. Do not change old operational dates or infer personal records from passenger names. Directory merges must preserve private reference identity/attribution without granting visibility; provider/venue claims do not verify historical activity.

Meaningful checks belong to the implementing tasks: pure-policy baseline/projection/audience tests; owner/foreign-object API probes; PostgreSQL constraints/races/atomic rollback; production-built session/Origin/cookie tests; export round-trip and rejection checks; and real mobile/operator release evidence. No such beta tests were executed to create this document.

Password-policy reference: [OWASP authentication guidance](https://cheatsheetseries.owasp.org/cheatsheets/Authentication_Cheat_Sheet.html). Our session/cutoff/restore/retention numbers are selected beta design defaults, not vendor guarantees or measured service capacity.
