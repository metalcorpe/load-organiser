# Beta API boundary and authorization conventions (#146)

Status: implemented in `backend/app/main.py`, `backend/app/skydiver/access/` and enforced by
`backend/app/tests/skydiver/test_boundary.py` and `test_access.py`. Decisions come from
[architecture A10](architecture.md#a10--legacy-isolation-and-release-order), the
[data contracts](data-contracts.md) and the [handoff](claude-code-handoff.md).

## Served surface

| Configuration | Mounted |
| --- | --- |
| Default (`LEGACY_API_ENABLED=false`), any environment | `/api/skydiver/v1/*` only. Docs/OpenAPI (`/docs`, `/redoc`, `/api/v1/openapi.json`) only when `ENVIRONMENT=local`. No CORS middleware: the beta API is called server-to-server by the web app |
| `LEGACY_API_ENABLED=true` | Additionally the legacy `/api/v1` prototype and its CORS settings, for the reference React app and its tests. **Settings refuse this unless `ENVIRONMENT=local`** |

The legacy code, tables and React client stay in the repository as reference/rollback input. A
local developer running the legacy React stack sets `LEGACY_API_ENABLED=true` in their own
environment; nothing in this repository enables it.

## Legacy route inventory

Every route of the legacy app, with the authorization it applies when enabled locally. All are
absent (404) from the default application; `test_boundary.py` compares this table with the
routes the code actually defines and probes each one with and without a superuser token.

| Route | Legacy authorization | Beta treatment |
| --- | --- | --- |
| `POST /api/v1/login/access-token` | none (credentials) | Superseded by #145 sessions |
| `POST /api/v1/login/test-token` | any user | Superseded by #145 sessions |
| `POST /api/v1/password-recovery/{email}` | none | Superseded by #145 recovery |
| `POST /api/v1/reset-password/` | none (token) | Superseded by #145 recovery |
| `POST /api/v1/password-recovery-html-content/{email}` | superuser | Superseded by #145 recovery |
| `GET /api/v1/users/` | superuser | Blanket user list: excluded |
| `POST /api/v1/users/` | superuser | Blanket user administration: excluded |
| `PATCH /api/v1/users/me` | any user | Superseded by #145 account |
| `PATCH /api/v1/users/me/password` | any user | Superseded by #145 password change |
| `GET /api/v1/users/me` | any user | Superseded by #145 session viewer |
| `DELETE /api/v1/users/me` | any user | Account deletion is a later beta use case (A9) |
| `POST /api/v1/users/signup` | none | Superseded by #145 registration (bypassed its switch/cap) |
| `GET /api/v1/users/{user_id}` | any user (self or superuser in handler) | Blanket user administration: excluded |
| `PATCH /api/v1/users/{user_id}` | superuser | Blanket user administration: excluded |
| `DELETE /api/v1/users/{user_id}` | superuser | Blanket user administration: excluded |
| `POST /api/v1/utils/test-email/` | superuser | Excluded |
| `GET /api/v1/utils/health-check/` | none | Replaced by `GET /api/skydiver/v1/health` |
| `GET /api/v1/items/` | any user (owner-filtered) | Generic items: excluded |
| `GET /api/v1/items/{id}` | any user (owner-checked) | Generic items: excluded |
| `POST /api/v1/items/` | any user | Generic items: excluded |
| `PUT /api/v1/items/{id}` | any user (owner-checked) | Generic items: excluded |
| `DELETE /api/v1/items/{id}` | any user (owner-checked) | Generic items: excluded |
| `GET /api/v1/aircraft/` | any authenticated user; no operational role | Deferred operations (#166) |
| `GET /api/v1/aircraft/{id}` | any authenticated user; no operational role | Deferred operations (#166) |
| `POST /api/v1/aircraft/` | any authenticated user; no operational role | Deferred operations (#166) |
| `PUT /api/v1/aircraft/{id}` | any authenticated user; no operational role | Deferred operations (#166) |
| `DELETE /api/v1/aircraft/{id}` | any authenticated user; no operational role | Deferred operations (#166) |
| `GET /api/v1/instructors/` | any authenticated user; no operational role | Deferred operations (#166) |
| `GET /api/v1/instructors/{id}` | any authenticated user; no operational role | Deferred operations (#166) |
| `POST /api/v1/instructors/` | any authenticated user; no operational role | Deferred operations (#166) |
| `PUT /api/v1/instructors/{id}` | any authenticated user; no operational role | Deferred operations (#166) |
| `DELETE /api/v1/instructors/{id}` | any authenticated user; no operational role | Deferred operations (#166) |
| `GET /api/v1/instructors/tandem-certified/` | any authenticated user; no operational role | Deferred operations (#166) |
| `GET /api/v1/instructors/aff-certified/` | any authenticated user; no operational role | Deferred operations (#166) |
| `GET /api/v1/loads/` | any authenticated user; no operational role | Deferred operations (#166) |
| `GET /api/v1/loads/{id}` | any authenticated user; no operational role | Deferred operations (#166) |
| `POST /api/v1/loads/` | any authenticated user; no operational role | Deferred operations (#166) |
| `PUT /api/v1/loads/{id}` | any authenticated user; no operational role | Deferred operations (#166) |
| `DELETE /api/v1/loads/{id}` | any authenticated user; no operational role | Deferred operations (#166) |
| `GET /api/v1/loads/by-status/{status}` | any authenticated user; no operational role | Deferred operations (#166) |
| `GET /api/v1/loads/today/` | any authenticated user; no operational role | Deferred operations (#166) |
| `POST /api/v1/loads/{id}/add-jumper` | any authenticated user; no operational role | Deferred operations (#166) |
| `DELETE /api/v1/loads/{id}/remove-jumper/{jumper_id}` | any authenticated user; no operational role | Deferred operations (#166) |
| `GET /api/v1/loads/{id}/capacity` | any authenticated user; no operational role | Deferred operations (#166) |
| `GET /api/v1/jumps/` | any authenticated user; no operational role | Deferred operations (#166) |
| `GET /api/v1/jumps/{id}` | any authenticated user; no operational role | Deferred operations (#166) |
| `POST /api/v1/jumps/` | any authenticated user; no operational role | Deferred operations (#166) |
| `PUT /api/v1/jumps/{id}` | any authenticated user; no operational role | Deferred operations (#166) |
| `DELETE /api/v1/jumps/{id}` | any authenticated user; no operational role | Deferred operations (#166) |
| `GET /api/v1/jumps/by-type/{jump_type}` | any authenticated user; no operational role | Deferred operations (#166) |
| `GET /api/v1/jumps/by-load/{load_id}` | any authenticated user; no operational role | Deferred operations (#166) |
| `GET /api/v1/jumps/by-instructor/{instructor_id}` | any authenticated user; no operational role | Deferred operations (#166) |
| `GET /api/v1/jumps/tandems/` | any authenticated user; no operational role | Deferred operations (#166) |
| `GET /api/v1/jumps/aff/` | any authenticated user; no operational role | Deferred operations (#166) |
| `POST /api/v1/jumps/{id}/assign-instructor` | any authenticated user; no operational role | Deferred operations (#166) |
| `GET /api/v1/weather/` | any authenticated user; no operational role | Deferred operations (#166) |
| `GET /api/v1/weather/{id}` | any authenticated user; no operational role | Deferred operations (#166) |
| `POST /api/v1/weather/` | any authenticated user; no operational role | Deferred operations (#166) |
| `PUT /api/v1/weather/{id}` | any authenticated user; no operational role | Deferred operations (#166) |
| `DELETE /api/v1/weather/{id}` | any authenticated user; no operational role | Deferred operations (#166) |
| `GET /api/v1/weather/current/` | any authenticated user; no operational role | Deferred operations (#166) |
| `GET /api/v1/weather/today/` | any authenticated user; no operational role | Deferred operations (#166) |
| `GET /api/v1/weather/suitable-for-jumping/` | any authenticated user; no operational role | Deferred operations (#166) |
| `GET /api/v1/weather/tandem-suitable/` | any authenticated user; no operational role | Deferred operations (#166) |
| `GET /api/v1/weather/student-suitable/` | any authenticated user; no operational role | Deferred operations (#166) |
| `GET /api/v1/analytics/load-statistics` | any authenticated user; no operational role | Deferred operations (#166) |
| `GET /api/v1/analytics/revenue-estimate` | any authenticated user; no operational role | Deferred operations (#166) |
| `GET /api/v1/analytics/instructor-workload` | any authenticated user; no operational role | Deferred operations (#166) |
| `GET /api/v1/analytics/daily-capacity/{target_date}` | any authenticated user; no operational role | Deferred operations (#166) |
| `GET /api/v1/analytics/jump-type-distribution` | any authenticated user; no operational role | Deferred operations (#166) |
| `GET /api/v1/analytics/weather-impact` | any authenticated user; no operational role | Deferred operations (#166) |
| `POST /api/v1/private/users/` | none (ENVIRONMENT=local only) | Private test-user creation: excluded |

## Known legacy defects (not fixed; tracked in #166)

Excluding these routes does not fix them. From [implementation-assessment](implementation-assessment.md)
(static inspection and earlier isolated probes; not re-run by #146) plus one item checked here:

- Operational routes require only an authenticated user: no dropzone ownership or operational role.
  An ordinary user could change a load status.
- Create routes for loads, jumps, instructors and weather pass mismatched CRUD keywords.
- Several routes call missing or mismatched CRUD functions (add/remove jumper, load capacity,
  instructor assignment, revenue, instructor workload); earlier probes returned HTTP 500.
- Jump updates bypass validation (an instructor could be removed from a tandem jump); the capacity
  model ignores instructors and accepted duplicate exit orders.
- Legacy signup bypasses the beta registration switch, account cap and password policy; legacy JWT
  login has no per-session revocation. Superseded by #145, not repaired.
- Items answer 400 "Not enough permissions" for another user's ID but 404 for an absent one,
  disclosing existence (checked in `app/api/routes/items.py` for #146).

## Authorization conventions for beta features

Code: `backend/app/skydiver/access/`. Policy is plain Python (`policy.py`, no FastAPI/SQL
imports, checked by a test); HTTP and SQL adapters sit beside it.

| Concern | Convention |
| --- | --- |
| Caller | `AccessDependencies(service).actor` resolves the bearer session to an `Actor` (account, person, email-verified, roles) on every request: 401 `not_authenticated` otherwise. The web server forwards only the session secret |
| Private writes | `verified_actor`: 403 `email_unverified` until the account's email is confirmed. Reads are allowed |
| Ownership | Personal-record tables carry `owner_person_id` (FK `skydiver_person.id`). The owner is set from the `Actor`, never from a request body, archive or legacy passenger name/email |
| Owner-scoped reads/writes | `owned(model, actor)` / `get_owned(session, model, id, actor)` put the owner predicate and the ID in the same SQL query. Foreign and absent IDs both give 404 with the same body. Lists and counts use the same predicate |
| Owner serialization | `lock_owner(session, actor)` locks the person row for quota/restore-style mutations (row lock, not a session-level lock) |
| Roles | `skydiver_role_grant` rows, granted by an operator (no API). The only beta role is `reviewer`; unknown stored values grant nothing. `access.role(Role.REVIEWER)` gives 403 `forbidden`. Revocation applies on the next request |
| Privilege limits | No role, including `reviewer`, reads another person's private records; reviewer access is scoped to the review cases of #151/#162. Legacy `is_superuser` confers no beta role |
| Shared content | `may_view(viewer, owner, audience, active, relationship)`: owner always; otherwise active only. Public: anonymous and unblocked viewers. Followers: approved followers without a block in either direction. Private: owner only. Callers load relationship facts in the same transaction |

## Evidence and limits

- Tests run on disposable PostgreSQL 17 (`test_access.py` uses a test-only owned table, since no
  beta personal-record feature exists until #152): anonymous, invalid session, owner, other user,
  client-supplied owner, unverified account, reviewer, legacy superuser, revoked session and
  revoked role.
- `may_view` encodes the data-contract audience rules but has no production caller until #156–158;
  its relationship loading and locking are those issues' work.
- No deployment exists; "not mounted" is proven on the composed application in tests, not on a host.
