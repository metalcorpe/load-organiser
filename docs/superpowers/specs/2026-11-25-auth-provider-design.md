# Passwordless sign-in through Neon's Managed Better Auth — design

Status: **draft v4 for owner approval** (2026-11-26). Supersedes v1–v3 (same file, git history). Facts
about Neon were read from its documentation, its CLI and the staging instance on 2026-11-25; anything not
stated there is a **gate** (section 9) that must pass before the switch. Reviewed by Codex four times
(read-only); its findings are folded in.

## 1. Decisions (all settled by the owner)

| Topic | Decision |
|---|---|
| Provider | Neon's **Managed Better Auth** (Better Auth 1.7.12 as run by Neon), on the existing Neon project `rough-paper-15304455` (aws-eu-central-1). |
| Independence | The web app is a standard **OIDC client**; the API is an **OAuth resource server** using **RFC 7662 introspection**. Provider-specific code only in two small adapters (sign-in page calls, account administration). |
| Sign-in | **Passwordless**: Google, or a **code by email** (Email OTP). Password sign-in and sign-up switched off at Neon. |
| Pages | **Our own** sign-in page (our look, our tests, works without JavaScript where the flow allows); no consent screen (first-party client, `skip_consent`). |
| Cut-over | **Clean break**: no feature flag, no old and new auth side by side, no separate Neon branch for the live app. One deploy. (The gates use a throwaway instance that is deleted afterwards, section 9.) |
| Revocation | **Immediate for anything that changes data** (introspect on every mutating API call, no cache); reads may reuse an introspection result for at most **30 s**. Accepted trade-off: after a sign-out elsewhere, a revoked token can still *read* that person's private pages for up to 30 s (today the API rejects it on the next call). |
| Email change | **Not supported in the beta** (the account's email is its identity at Neon). |
| Lost inbox | Recovery through a **linked Google identity**, plus a documented **operator recovery** (section 7). |
| Accounts | The owner's person, profile, data and reviewer role are **kept** and re-linked; test accounts are **recreated**. |
| First social provider | **Google**, with **Neon's shared development credentials** while we are developing (owner, 2026-11-26): Google's screen shows Neon's name and logo. The owner's own Google OAuth client is a **production step** (section 12, P1). |
| Code emails | **Neon sends them** from its shared sender (`auth@mail.myneon.app`, Neon's template) while we are developing (owner, 2026-11-26). Sending them ourselves through the `send.otp` hook is a **production step** (P4). |
| Exit | Settled before starting (section 10). |

## 2. What Neon provides (verified 2026-11-25)

- Instance `base_url` (= issuer): `https://ep-winter-math-b9muy5c8.neonauth.c-7.eu-central-1.aws.neon.tech/neondb/auth`,
  same region as the database. Data in our database, schema `neon_auth`.
- OAuth server **enabled** (by Claude, owner-approved): trusted domain `https://load-organiser.metalcorpe.workers.dev`,
  login page `…/sign-in`, consent page `…/oauth/consent`, protected resource `https://load-organiser.fastapicloud.dev`.
- Discovery (`<issuer>/.well-known/openid-configuration`, 200): authorize, token, **introspection**
  (`/oauth2/introspect`), revocation, end-session, userinfo, JWKS (EdDSA/Ed25519), PKCE, DPoP; back-channel
  logout advertised.
- **Not usable in the managed service:** registering a back-channel logout URI, post-logout redirect URIs or
  end-session per client (no CLI flag, no API field; only self-hosted Better Auth has them). So revocation rests
  on introspection, not logout notifications.
- Clients: `neon neon-auth oauth-client create --name --type confidential|public --redirect-uris --resources
  [--skip-consent]`; confidential clients authenticate with `client_secret_basic` (secret shown once); redirect
  URIs match exactly.
- Our login page receives the authorization request as a **signed, expiring query**; it resumes the flow by
  passing it back as `oauth_query`: in the sign-in request, or for an already signed-in user with
  `POST <issuer>/oauth2/continue {selected: true, oauth_query}` and navigating to the returned `url`.
  `prompt=login` / `max_age=0` loop back to the login page (fresh re-authentication needs another way).
- Email OTP: `emailOtp.sendVerificationOtp({email, type: 'sign-in'})`, `signIn.emailOtp({email, otp})`,
  `emailOtp.checkVerificationOtp(...)`; codes "time-limited and rate-limited", `TOO_MANY_ATTEMPTS` on excess.
  Length, expiry, attempt count and whether a first sign-in creates the user are **not stated** (gates).
- Email: shared sender is development-only. Webhooks (`user.before_create`, `user.created`, `send.otp`,
  `send.magic_link`) let us send the codes ourselves through our existing SMTP account.
- Settings switchable by CLI: `config email-password update --enabled false` (password sign-in off),
  `--disable-sign-up`.
- Pricing: included in the Neon plan; Free up to 60,000 monthly active users.

## 3. Architecture

```
Browser ── HttpOnly cookie: encrypted token set ──► Web server (SvelteKit Worker) = confidential OIDC client (BFF)
                                                     │ authorization code + PKCE + state + nonce
                                                     │ refreshes tokens; never exposes them to the browser
                                                     ▼ Authorization: Bearer <access token>  + proxy key
                                            API (FastAPI) = resource server
                                              introspects the token (RFC 7662), maps iss+sub → person,
                                              enforces reviewer grants and all data access as today
                                                     │
                                                     ▼ standards only: discovery, authorize, token, introspect, revoke, JWKS
                                            Neon Managed Better Auth (issuer)
                                              Google / email code, accounts, sessions, tokens
```

### 3.1 Sign-in sequence

1. The browser asks for a private page without a session → web server starts authorization: redirect to
   `<issuer>/oauth2/authorize` (client id, redirect URI `…/auth/callback`, PKCE S256, `state`, `nonce`,
   `resource=<API>`, scopes `openid email profile offline_access`), storing `state`/`nonce`/verifier and the
   return path in a short-lived signed, HttpOnly cookie.
2. Neon redirects to **our `/sign-in`** with the signed authorization query.
3. **Our page** shows two choices: *Continue with Google* and *Email me a code*.
   - Email code: our server action calls Neon's `sendVerificationOtp(type: sign-in)`; the next screen takes
     the code; our server action calls `signIn.emailOtp` **with `oauth_query`**; Neon answers with the next
     URL (consent skipped → the callback with a code).
   - Google: the button starts Neon's social sign-in with `oauth_query`; **Google shows its own screens**;
     Neon returns the browser to our `/sign-in` with the same query; the page then continues
     (`/oauth2/continue`).
   - Whether these calls run **server-side** (our server holds Neon's session cookie for the duration) or in
     the browser (cross-site cookie to Neon's domain, blocked by Safari's tracking prevention) is **gate G1**.
     Server-side is the target: no third-party cookies, our own throttling, and the email path works without
     JavaScript.
4. `/auth/callback`: check `state`, exchange the code at the token endpoint (client secret), validate the ID
   token (issuer, audience, nonce, signature via JWKS), set our session cookie (below), redirect to the return
   path (validated with `safeReturnPath`).
5. `/sign-in` while already signed in: today it redirects at once
   (`web/src/routes/sign-in/+page.server.ts:20`); with a pending `oauth_query` it must continue the
   authorization instead (no loop).

### 3.2 Our session cookie (web server)

- One HttpOnly, Secure, SameSite=Lax cookie (`__Host-` prefix in production, as today's session cookie)
  holding the **access token, refresh token, their expiries, `sid` and the sign-in time**, so no server-side
  store is needed. Envelope: `v1.<key id>.<nonce>.<ciphertext>`, AES-256-GCM under a Worker secret
  (`SESSION_ENCRYPTION_KEY`, with the previous key accepted during rotation), the cookie name and version as
  associated data. Rejected and cleared if it fails to decrypt, has an unknown version or key, or is past
  **7 days from sign-in** (absolute, whatever the tokens say). A copied old cookie is only as good as the tokens
  inside it, which revocation ends (introspection). G2 measures the full encoded size.
- **Refresh protocol** (a per-isolate lock cannot coordinate other isolates or tabs):
  - **any** request the web server handles (document, SvelteKit data request `isDataRequest`, form action)
    refreshes when the access token has less than **5 minutes** left. Client-side navigations are data
    requests, so they refresh too;
  - because refresh starts 5 minutes early, a request that **loses** a refresh race (its refresh token was
    already used by another tab or isolate) still holds a **valid** access token: it carries on with it and does
    not touch the cookie. The browser keeps the winner's cookie;
  - only when the access token has **fully expired** and the refresh fails does the request end: a page or data
    request shows signed-out (`/sign-in?returnTo=…`, data requests through SvelteKit's redirect payload as in
    `hooks.server.ts:51`); a **form action** returns `fail(401)` with the submitted values kept in the form and
    the notice "Your session ended. Sign in again, then send the form again." — input is never silently lost;
  - **G3 pass criteria** (executable, against Neon): (a) two concurrent refreshes with the same refresh token
    leave the winner's new tokens valid (introspection `active`); (b) a loser with a still-valid access token
    completes its request; (c) a client navigation, a form post and a document load each refresh near expiry;
    (d) an expired session's form post keeps its values. If (a) fails because Neon revokes the whole session on
    reuse, the fallback is a single-writer refresh per session in a Durable Object (free plan, owner approval
    for the extra infrastructure), and **the same four criteria are re-run against the fallback** before phase 2.
- Kept, with the same tests: `Cache-Control: no-store`; `Clear-Site-Data` on sign-out and deletion **and on
  account switch** (a callback that replaces a different person's cookie, as `sign-in/+page.server.ts:54` does
  today); exact unsafe-origin rejection (`hooks.server.ts:25,71`) for every POST including the code step;
  `sessionUnconfirmed` (3.3).
- The 30-second viewer cache (`viewer-cache.ts`) becomes the 30-second **read** introspection cache in the API
  (3.3); the web server no longer confirms sessions itself.

### 3.3 API token validation

- Every API call carries the proxy key (as today, `backend/app/skydiver/web_only.py`) and the access token.
- The API introspects at `<issuer>/oauth2/introspect` with its own confidential credentials:
  - **mutating requests** (POST/PUT/PATCH/DELETE): always live, no cache;
  - **reads**: an introspection result may be reused for `min(30 s, token expiry − now)` (keyed by a SHA-256 of
    the token, per process, at most 1,000 entries). Only `active`, `sub`, `client_id` and `exp` are cached;
    person status, deletion intent and reviewer grants are read from our database on every request, as today.
- Introspection call: 2 s timeout (inside the web server's 5 s API budget, `web/src/lib/api-timeouts.ts:2`), at
  most 8 concurrent calls per process. On timeout, error or 429: mutations answer `503` "unavailable, try
  again" (never allowed through); reads use a cached result if one is still valid, else the same `503`.
- Accept only `active: true`, the expected issuer, our API as audience/resource, and the expected client.
- Map `(iss, sub)` → `person` through a new `identity_link` table; reviewer grants stay **app grants on the
  person**, checked per request (`backend/app/skydiver/access/http.py:85`); provider roles are never trusted.
- A subject with a pending or completed deletion intent, or an unlinked (relinked away) subject, gets `401`
  even with an active token.
- Every request, **including introspection cache hits**, reads from our database: person status,
  `deletion_intent`, `unlinked_subject` and reviewer grants.
- The 2 s budget includes any wait for one of the 8 concurrent slots. Introspection `503` is **never** turned
  into anonymous: the optional-viewer dependency today swallows every `HTTPException`
  (`backend/app/skydiver/access/http.py:67`); it will swallow only "no or invalid token" and re-raise `503`.
- In the web server: a `503` while resolving the viewer keeps today's behaviour (cookie kept, rendered
  signed-out with the "service unavailable" notice, `sessionUnconfirmed`, `web/src/lib/server/viewer.ts:42-47`);
  a `503` on any later API call of the same request is shown as that page's or form's "service unavailable"
  error, as API timeouts are today. Neither clears the cookie.

### 3.4 Sign-out, sign out everywhere, deletion

- **Sign out (this device):** web server revokes the refresh and access tokens (`/oauth2/revoke`), ends the
  Neon browser session it holds (gate G1), clears our cookie, sends `Clear-Site-Data`.
- **Sign out everywhere:** confirmed with a **fresh email code** (or Google re-authentication, gate G4); the
  API's account adapter revokes all of the user's Neon sessions through Neon's management API (key held by the
  API only), then this device signs out as above. Introspection then reports every token inactive (gate G5).
- **Fresh confirmation contract** (sign-out everywhere, deletion, records restore): the web server asks the
  API to send a code to the signed-in person's address; the API stores a hash of the code bound to the
  **person and the current token's `sid`**, with the operation name, valid for **10 minutes**, at most 5 checks.
  The operation's API call carries the code; the API checks binding, age and operation, and **consumes** it in
  the same transaction as the operation (one use; a replay fails). Wrong codes count against the code-check
  throttle (section 6). This replaces today's password re-check (`records/api.py:320`), which also happens in
  the API immediately before the operation.
- **Account deletion:** fresh email code, then:
  1. **one transaction:** insert `deletion_intent(issuer, subject, created_at, attempts, last_error,
     provider_deleted_at)` (no foreign key to `person`, so it outlives it), write the erasure-ledger entry,
     delete our data as today (retained history with cleared references, `identity/service.py:510`) and the
     `identity_link` row;
  2. **after commit:** revoke the subject's Neon sessions and delete the Neon user through the adapter;
     success sets `provider_deleted_at`, failure records `attempts`/`last_error`;
  3. **retries:** at API start-up and on every request presenting that subject, at most once per minute per
     intent, until done; `scripts/staging.sh deletion-intents` lists unfinished ones.
  While an intent exists (pending or done), that subject is refused at the API (3.3) and at linking, so a
  cached token or a fresh sign-in cannot re-create the person. Intent rows are kept indefinitely (a few bytes
  each), like the erasure ledger.

## 4. Pages and API changes

| Today | After |
|---|---|
| `/sign-in` (email + password) | Google + email code (3.1); continues pending authorizations. |
| `/register` | Removed: the first sign-in by code or Google is the sign-up. **Identity linking** for an unknown subject keeps today's compare-and-swap (`identity/service.py:325`): read the registration version, check open and under the ceiling, insert person and `identity_link` in one transaction that commits only if the version is unchanged, else re-read and retry. Duplicate callbacks: person and link are inserted in one transaction; if the link insert hits the unique `(issuer, subject)` key, the **whole transaction rolls back** (the losing person row with it) and the request re-reads the winner's link, so both get the same person. Denied (closed or full): the API answers "registration closed", no person is created, and the adapter deletes the Neon user it just made (retried like deletion). The owner's link (`link-owner`, section 8) is an operator action and works while registration is closed. |
| `/verify-email` | Removed: an email code proves the address. |
| `/forgot-password`, `/reset-password` | Removed (no passwords); old links redirect to `/sign-in`. |
| Account page: change password, sign out everywhere (password), delete (password) | No password section; sign out everywhere and delete confirm with a fresh email code. Linked Google shown, with *Link Google* for recovery. |
| API identity endpoints (sessions, register, verify, reset, change password; `identity/api.py`) | Removed; replaced by token validation (3.3) and an account-admin adapter. Contract regenerated. |
| Records restore asks for the password (`records/api.py:320`, `PASSWORD_HEADER`) | Asks for a fresh email code instead, like sign-out-everywhere and deletion. |
| New | `/auth/callback`, `/sign-in` code step, `/oauth/consent` (exists only because Neon requires the setting; with `skip_consent` it redirects to `/sign-in`). |

## 5. Emails

Only one kind of email remains: the **sign-in code** (also used for the fresh-code confirmations). Neon
creates, stores, checks and expires the codes in every case; the only question is who delivers the email.

- **While developing (now):** Neon emails the code itself from its shared sender (`auth@mail.myneon.app`) with
  its own template. Neon documents this sender as rate-limited and meant for development; codes work with it.
  Our app sends no auth email; the API's SMTP account is not used for sign-in.
- **Production step P4:** Neon's `send.otp` webhook calls **the API directly**
  (`/api/skydiver/v1/auth-hooks/send-otp`, not behind Cloudflare Access), and the API sends the code through
  our existing SMTP account with our plain wording. That one path is exempt from the proxy-key check
  (`backend/app/skydiver/web_only.py`), like `/health`, and instead requires a valid Neon signature with a
  timestamp no older than 5 minutes; replays of a seen delivery id are ignored. Gate G6 runs then, against the
  hosted API (no tunnel needed). The API only delivers codes; it never checks them.

Removed: verification links, password reset, "sign-in help" (no separate registration exists that could hit
an existing address).

## 6. Security properties to keep

- **Account existence stays private:** sending a code answers the same for known and unknown addresses (gate
  G7 also confirms Neon does not reveal it).
- **Throttling** in our server actions, in the existing database buckets (atomic, shared by all isolates and
  API processes; IPv6 by /64 as today, `identity/policy.py:80`):
  - code send: 3 per address per hour, 10 per IP per hour (today's reset limits, `policy.py:35-36`); an address
    over its limit gets the **same neutral answer** as a sent code (no existence or limit signal);
  - code check: 10 per **IP and address pair** per 15 minutes, 50 per IP per 15 minutes (today's login limits,
    `policy.py:33-34`, keyed as `identity/service.py:692`); each wrong code is one hit, a correct one none;
  - addresses normalised with `policy.normalize_email` before counting;
  - the Worker's server actions **reserve** a slot through one new API endpoint
    (`POST /api/skydiver/v1/auth/throttle`, proxy key required) before calling Neon, because the buckets live
    in the database the API owns;
  - new person (identity linking): 10 per IP per hour (today's registration limit, `policy.py:37`).
  These do not stop someone calling Neon's endpoints directly, bypassing our pages; against that, only Neon's own
  limits apply. **G8** measures them, and the owner accepts them or the switch waits.
- **Sessions:** 7-day absolute lifetime and at most 5 active sessions per person, enforced by the token
  lifetimes and session handling Neon offers or by our account adapter (gate G9).
- **No tokens in HTML, page data, logs or browser storage;** state/nonce/PKCE, exact redirect URIs, callback
  replay rejected (gate G10).

## 7. Recovery

- **Linked Google:** a person with a linked Google identity can sign in with it when their email is
  unavailable (both identities link to the same person).
- **Operator recovery** (`docs/product/auth-recovery-runbook.md`): the owner verifies the person out of band,
  then runs `scripts/staging.sh relink <person> <new-email>`. In one transaction it removes the old
  `identity_link` and records the old subject as **unlinked** (refused at the API and at linking, 3.3), then
  links the new identity; after commit the adapter revokes the old subject's Neon sessions and deletes or
  disables that Neon user (retried like deletion). Refused if the new identity is already linked to another
  person (the operator must resolve that person first) or if either person has a pending deletion intent; the
  transaction locks both persons' rows (`SELECT … FOR UPDATE`, the documented fallback to compare-and-swap for
  this rare operator command) so a concurrent sign-in or deletion waits. Never automatic: a new address never silently takes over a
  person.
- Email change itself is out of scope for the beta.

## 8. Data and migration

- New tables `identity_link(issuer, subject, person_id, email_at_link, linked_at)`, unique on `(issuer,
  subject)`; `deletion_intent` (3.4); `unlinked_subject(issuer, subject, unlinked_at)` (section 7).
- **Re-rooting:** today `person` and reviewer grants hang off `user.id` with cascading deletes
  (`identity/tables.py:25,49,133`) and deletion starts at `user` (`identity/store.py:310`). The migration makes
  `person` the root: grants reference `person.id`, deletion deletes the person and its owned data explicitly in
  the 3.4 transaction. Migration check: person count, grant count and each grant's person are identical before
  and after; a migration test asserts it on a seeded database.
- Removed after the switch, by the second migration (b) once the owner is linked (section 12, phase 3): legacy
  `user` credentials, sessions, verification and reset tokens, password-only throttle buckets. The code that
  used them is removed in the switch itself.
- **Owner:** signs in once with an email code on staging; `scripts/staging.sh link-owner <email>` links that
  subject to the existing person (profile, jumps, reviewer grant kept). **Test accounts:** recreated by the
  owner signing in with test addresses, or discarded.
- **Erasure ledger:** entries record the person and `(issuer, subject)`. Replay after a restore
  (`recovery/ledger.py:57,371,378` today targets `user`, sessions and tokens) instead deletes the person's data,
  removes the `identity_link`, and re-creates the `deletion_intent` so the Neon user is deleted again if the
  restore brought it back. As today (`recovery/ledger.py:368`), every restore also ends **all** sessions:
  replay revokes every Neon session through the adapter, so everyone signs in again. Legacy-schema entries written before the switch are replayed by the old rules, so a
  restore from before the switch still works. A restore drill (deletion, restore, replay) is part of the
  switch's checks.
- **Tooling:** `scripts/staging.sh create-account` and `identity/operator.py` (passwords) replaced by
  `link-owner`, `relink` and `grant-reviewer <person>`. `scripts/dev.sh` and `scripts/verify.sh` run a local
  **test identity provider** (section 11) so dev and e2e never touch Neon.

## 9. Gates (must pass before the switch merges)

**Where they run:** not on staging. A throwaway **gate instance** with its own Auth, and the spike web app on
the owner's machine at `http://localhost:5181`, so staging, its Cloudflare Access and today's password
sign-in are untouched until the switch (preview URLs are off, `web/wrangler.jsonc:14`, and stay off).
Isolation checklist for the gate branch: (1) a **schema-only** child branch, or a data branch whose
inherited people, emails and `neon_auth` rows are deleted before any test, so no real person can be emailed or
signed in; (2) only test addresses the owner controls, since Neon's shared sender emails the codes for real;
(3) no webhook is configured on the gate instance (G6 runs at P4); (4) local configuration: `APP_ORIGIN=http://localhost:5181`,
`API_ORIGIN` the local API, `SESSION_COOKIE_MODE=localhost-dev` (`web/src/lib/server/session-config.ts:40`),
resource/audience the local API URL, Neon issuer and client from the gate instance; the same values with the
tunnel's origin if a tunnel is used.
Rollback is deleting the gate instance. G0 decides which instance; Neon's docs say each branch has its own
Auth base URL and its own OAuth settings, so a child branch is expected to suffice.

| Gate | Proves (pass condition) |
|---|---|
| G0 | A gate instance exists with its own OAuth server settings (login page, trusted domain, clients): first choice a Neon **child branch** of the staging database with Auth on it; if branches share or cannot carry these settings, a throwaway **Free Neon project** in aws-eu-central-1. Neon accepts `http://localhost:5181` as trusted domain and redirect URI; if not, a Cloudflare quick tunnel (no account, no cost). |
| G1 | Email-code sign-in completes end to end with our own `/sign-in`, in Chromium **and** WebKit, with every Neon call server-side and no third-party cookie; the Neon browser session can be ended. (Google moves to G14.) |
| G2 | The full encoded cookie is under 4,096 bytes with real tokens; key rotation works (old key accepted, new key written); tampered, unknown-version and over-7-days cookies are rejected. |
| G3 | Refresh rotation and reuse: two tabs, two isolates, reversed response order; pass = the session survives every ordering, or the Durable Object fallback (3.2) is approved. |
| G4 | Fresh re-authentication by email code for sign-out-everywhere, deletion and records restore. |
| G5 | After sign-out, token revocation, sign-out-everywhere and user deletion: introspection returns `active: false` at once, **and refresh with the old refresh token fails** (no new tokens issued). |
| G6 | (At production step P4, against the hosted API.) Webhook signature and timestamp verified at the API path; Neon's retry behaviour on a failed delivery; a replayed delivery is ignored. |
| G7 | Code requests do not reveal account existence (same answer and timing class for known and unknown addresses), including when calling Neon directly. |
| G8 | Neon's limits for code sends, code checks and `/oauth2/introspect` (rate, scope, 429 behaviour); from the API's region, introspection adds at most 150 ms at p95 over 200 calls; the owner accepts the direct-call limits. |
| G9 | Token lifetimes and session caps achievable (7 days absolute, 5 sessions) or a documented deviation approved by the owner. |
| G10 | state/nonce/PKCE enforced; redirect URI exact; replayed callback rejected; wrong issuer/audience/client rejected; JWKS rotation handled. |
| G11 | Password sign-in and sign-up are off at Neon (direct calls to the password endpoints fail). |
| G12 | Whether the first email-code sign-in creates a Neon user, and that identity linking applies the registration switch and ceiling. |
| G13 | Exit export: the `neon_auth` tables read back (users, accounts) with a test account present; re-run on staging after the switch with the owner's account. |
| G14 | Google sign-in with Neon's shared credentials (phase 1), re-run with the owner's client at production step P1, in Chromium and WebKit, returning through our `/sign-in` and `/oauth2/continue`; Google linked to an existing person for recovery; fresh Google re-authentication for deletion despite Neon's `prompt=login` loop, or deletion stays code-only. |

## 10. Exit strategy

All auth data is in our database (`neon_auth`): `user` (id, email, verified), `account` (provider links:
`google`, email), `session`, `verification`. Passwordless means **no password hashes to move**.

1. **Self-hosted Better Auth** against the same tables: change the issuer in configuration; users sign in as
   before.
2. **Any other OIDC provider:** export users and Google links with SQL; import or let users sign in again by
   email code or Google; re-link `identity_link` by verified email (operator-run, logged).
3. **Google** keeps working on another provider only with the owner's own Google OAuth client (production step
   P1); while Neon's shared credentials are in use, Google sign-ins belong to Neon's app. Whether Google
   identities keep the same subject when the client changes from Neon's to ours is **untested** (checked at P1).
4. Our data never leaves our tables; `identity_link` is the only thing re-pointed.

`docs/product/auth-exit-runbook.md` (written with the switch): export queries, Google client ownership, relink
procedure. G13 proves the export.

## 11. Tests

- **Test identity provider** for dev and e2e: a small local OIDC server (discovery, authorize, token,
  introspect, revoke, JWKS, email-code issuing to the local mail outbox) started by `scripts/dev.sh` and
  `scripts/verify.sh`. It covers the standards-only part, so that code cannot tell it from Neon.
- **Adapter doubles:** the Neon-specific code sits behind three small interfaces — sign-in page calls
  (send code, check code with `oauth_query`, `/oauth2/continue`, end Neon session), account admin (revoke
  sessions, delete user) and the `send.otp` webhook payload. Dev and e2e use in-process doubles served by the
  test provider; the real adapters get contract tests that run against the gate instance (phase 1) and are
  re-run against staging at the switch.
- Rewritten: auth, account, privacy, boundaries and social suites' sign-in helpers (`web/tests/support/accounts.ts`)
  sign in through the test provider; the privacy and boundary assertions themselves stay unchanged.
- New: callback replay, wrong issuer/audience, expired and revoked tokens rejected at the API, introspection
  outage/timeout/429 (mutations 503, reads cached or 503, `sessionUnconfirmed` shown), read cache ≤ 30 s and ≤
  token expiry, mutations always live, encrypted cookie tampering/expiry/key rotation, refresh races (two
  requests, reversed order), account switch clears the site cache, unsafe-origin POSTs rejected, account
  existence privacy for code requests, each throttle's limit, duplicate callbacks and concurrent linking at the
  ceiling, deletion intent retries and refusal of the deleted subject, relink refusal of the old subject,
  records restore needs a fresh code, migration counts, restore replay of new and legacy ledger entries.

## 12. Phases

1. **Gates on the gate instance (G0–G14, G14 with Neon's shared Google credentials):** create the gate instance (G0); on it, register a confidential
   client for `http://localhost:5181`, switch password sign-in off (G11), leave code emails to Neon's shared sender,
   apply the isolation checklist (section 9); run the gates (all but G6)
   with a throwaway spike branch of the web app on the owner's machine (never merged); record results here;
   delete the gate instance. The owner approves the results. Staging is not changed.
2. **Build the switch** on one git branch: sections 3–8 and 11, old auth removed in the same change, full
   verify gate green, Codex review.
3. **Switch-over (one deploy):** on the staging instance: register the staging client, switch password sign-in off — immediately before merging, since that ends today's password
   sign-in on staging. Merge and deploy; owner signs in by code and runs `link-owner`; adapter contract tests
   against staging; restore drill; G13 re-run with the owner's account. Rollback: migrations run before the deploy
   (`scripts/staging.sh migrate`) and remove legacy credentials, so the old code cannot simply return. The
   migration therefore runs in two parts: **(a)** before the deploy, additive only (new tables, person re-rooted,
   legacy tables untouched), so reverting the merge and switching password sign-in back on restores today's
   sign-in; **(b)** dropping legacy credentials, sessions and tokens, run only after the owner has signed in and
   linked, in a later migration. A Neon branch snapshot is taken before (a).
4. **Google:** *Continue with Google* enabled with Neon's shared credentials; G14 already passed in phase 1
   on the gate instance and is re-run on staging after the switch.

**Production steps** (before the beta opens beyond test users; recorded here so they are not forgotten):

- **P1 — own Google client:** the owner creates a Google Cloud project, an External consent screen (app name,
  support email, scopes `openid email profile` only, so no Google review), and a *Web application* OAuth
  client with redirect URI `<issuer>/callback/google`; the owner enters the ID and secret in Neon (never
  pasted into chat or the repository). Re-run G14; check existing Google-linked people still sign in.
- **P2 — Allow Localhost off** on the staging/production Auth instance (Neon's production checklist).
- **P3 — application name** set to *Load Organiser* (Neon's default is the project name).
- **P4 — our own code emails:** build the `send.otp` hook endpoint (section 5), set the webhook on the
  staging/production Auth instance to the hosted API, run G6, then Neon's shared sender is no longer used.

## 13. Risks

- Neon's OAuth server is labelled **beta** in one Neon FAQ; behaviour can change. Mitigation: standards-only
  code, the test provider, and the exit strategy.
- **Cross-site cookies (G1)** are the most likely blocker: if Neon's sign-in cannot run server-side, the email
  path depends on third-party cookies, which Safari blocks.
- **Refresh races (G3):** if Neon's reuse detection ends the session on a lost race, the fix (a Durable Object)
  adds infrastructure.
- **Direct calls to Neon** bypass our throttles; only Neon's limits apply (G8).
- Managed service limits: no custom hooks or plugins; back-channel logout and end-session not configurable.
- Introspection on every mutation adds one call per write to Neon (same region as the database; the API is
  still in us-east-1 until it moves to Europe).
- Clean break: no fallback after merging; fixed forward or reverted as a whole.

## Sources (checked 2026-11-25)

- Neon: [OAuth Provider](https://neon.com/docs/auth/guides/plugins/oauth-provider), [Email OTP](https://neon.com/docs/auth/guides/plugins/email-otp),
  [CLI: neon-auth](https://neon.com/docs/cli/neon-auth), [Managed Better Auth overview](https://neon.com/docs/auth/overview),
  [About](https://neon.com/docs/auth/about), [Plugins](https://neon.com/docs/auth/guides/plugins), [JWT](https://neon.com/docs/auth/guides/plugins/jwt),
  [Customize emails](https://neon.com/docs/auth/guides/customize-emails), [Webhooks](https://neon.com/docs/auth/guides/webhooks),
  [Production checklist](https://neon.com/docs/auth/production-checklist), [neon-auth agent skill](https://neon.com/docs/ai/skills/neon-auth/SKILL.md),
  [Free up to 60,000 MAU](https://neon.com/faqs/free-auth-service-60000-monthly-active-users)
- Better Auth: [OAuth 2.1 Provider](https://better-auth.com/docs/plugins/oauth-provider),
  [OpenID Connect and logout](https://better-auth.com/docs/plugins/oauth-provider/openid-connect),
  [Session management](https://better-auth.com/docs/concepts/session-management)
- Staging instance: discovery document and `neon neon-auth` CLI output, 2026-11-25.
