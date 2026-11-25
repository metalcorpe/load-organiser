# Passwordless sign-in through Neon's Managed Better Auth — design

Status: **draft v2 for owner approval** (2026-11-25). Supersedes v1 (same file, git history). Facts about Neon
were read from its documentation, its CLI and the staging instance on 2026-11-25; anything not stated there is
a **gate** (section 9) that must pass on staging before the switch. Reviewed by Codex twice (read-only); its
findings are folded in.

## 1. Decisions (all settled by the owner)

| Topic | Decision |
|---|---|
| Provider | Neon's **Managed Better Auth** (Better Auth 1.7.12 as run by Neon), on the existing Neon project `rough-paper-15304455` (aws-eu-central-1). |
| Independence | The web app is a standard **OIDC client**; the API is an **OAuth resource server** using **RFC 7662 introspection**. Provider-specific code only in two small adapters (sign-in page calls, account administration). |
| Sign-in | **Passwordless**: Google, or a **code by email** (Email OTP). Password sign-in and sign-up switched off at Neon. |
| Pages | **Our own** sign-in page (our look, our tests, works without JavaScript where the flow allows); no consent screen (first-party client, `skip_consent`). |
| Cut-over | **Clean break**: no feature flag, no old and new auth side by side, no separate Neon branch. One deploy. |
| Revocation | **Immediate for anything that changes data** (introspect on every mutating API call, no cache); reads may reuse an introspection result for at most **30 s**. |
| Email change | **Not supported in the beta** (the account's email is its identity at Neon). |
| Lost inbox | Recovery through a **linked Google identity**, plus a documented **operator recovery** (section 7). |
| Accounts | The owner's person, profile, data and reviewer role are **kept** and re-linked; test accounts are **recreated**. |
| First social provider | **Google**, with the owner's **own** Google OAuth client (never Neon's shared credentials). |
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
  holding the **access token, refresh token, expiries and `sid`**, encrypted with AES-GCM under a Worker secret
  (`SESSION_ENCRYPTION_KEY`), so no server-side store is needed. Size and rotation of the key are part of
  gate G2.
- Refresh when the access token is within 60 s of expiry; concurrent requests must not both refresh with a
  rotating refresh token (gate G3: Neon's rotation and reuse detection, and a per-isolate refresh lock).
- `Cache-Control: no-store`, `Clear-Site-Data` on sign-out/deletion, origin checks and account-switch isolation
  stay as in `web/src/hooks.server.ts`.
- The 30-second viewer cache (`viewer-cache.ts`) becomes the 30-second **read** introspection cache in the API
  (3.3); the web server no longer confirms sessions itself.

### 3.3 API token validation

- Every API call carries the proxy key (as today, `backend/app/skydiver/web_only.py`) and the access token.
- The API introspects at `<issuer>/oauth2/introspect` with its own confidential credentials:
  - **mutating requests** (POST/PUT/PATCH/DELETE): always live, no cache;
  - **reads**: an introspection result may be reused for at most 30 s (keyed by a SHA-256 of the token).
- Accept only `active: true`, the expected issuer, our API as audience/resource, and the expected client.
- Map `(iss, sub)` → `person` through a new `identity_link` table; reviewer grants stay **app grants on the
  person**, checked per request (`backend/app/skydiver/access/http.py:85`); provider roles are never trusted.
- Introspection outage: reads with a cached result continue up to its 30 s; otherwise the API answers
  "unavailable" and the web server keeps the cookie but renders signed-out (today's `sessionUnconfirmed`
  behaviour, `web/src/lib/server/viewer.ts:47`).

### 3.4 Sign-out, sign out everywhere, deletion

- **Sign out (this device):** web server revokes the refresh and access tokens (`/oauth2/revoke`), ends the
  Neon browser session it holds (gate G1), clears our cookie, sends `Clear-Site-Data`.
- **Sign out everywhere:** confirmed with a **fresh email code** (or Google re-authentication, gate G4); the
  API's account adapter revokes all of the user's Neon sessions through Neon's management API (key held by the
  API only), then this device signs out as above. Introspection then reports every token inactive (gate G5).
- **Account deletion:** fresh email code; the API records a **durable deletion intent**, deletes our data in
  one transaction as today (retained history with cleared references, `identity/service.py:510`), then deletes
  the Neon user through the adapter with retries until done; while pending, the identity link refuses sign-in
  (no re-provisioning). The erasure ledger records the person and the provider subject so a database restore
  re-applies both (section 8).

## 4. Pages and API changes

| Today | After |
|---|---|
| `/sign-in` (email + password) | Google + email code (3.1); continues pending authorizations. |
| `/register` | Removed: the first sign-in by code or Google is the sign-up; registration open/closed and the account ceiling (`identity/service.py:320`) enforced at **identity linking** (an unknown subject gets a person only while registration is open and under the ceiling). |
| `/verify-email` | Removed: an email code proves the address. |
| `/forgot-password`, `/reset-password` | Removed (no passwords); old links redirect to `/sign-in`. |
| Account page: change password, sign out everywhere (password), delete (password) | No password section; sign out everywhere and delete confirm with a fresh email code. Linked Google shown, with *Link Google* for recovery. |
| API identity endpoints (sessions, register, verify, reset, change password; `identity/api.py`) | Removed; replaced by token validation (3.3) and an account-admin adapter. Contract regenerated. |
| New | `/auth/callback`, `/sign-in` code step, `/oauth/consent` (exists only because Neon requires the setting; with `skip_consent` it redirects to `/sign-in`). |

## 5. Emails

Only one kind of email remains: the **sign-in code** (also used for the fresh-code confirmations). Neon's
`send.otp` webhook calls our API; the API sends it through our existing SMTP account with our plain wording.
The webhook endpoint verifies Neon's signature (gate G6) and is exempt from the cross-origin check
(`hooks.server.ts:25`) only on that path. Removed: verification links, password reset, "sign-in help" (no
separate registration exists that could hit an existing address).

## 6. Security properties to keep

- **Account existence stays private:** sending a code answers the same for known and unknown addresses (gate
  G7 also confirms Neon does not reveal it).
- **Throttling** at least as strict as today for the email path (code sends per address and per IP; code
  checks), applied in our server actions; Neon's own limits on top (gate G8 measures them).
- **Sessions:** 7-day absolute lifetime and at most 5 active sessions per person, enforced by the token
  lifetimes and session handling Neon offers or by our account adapter (gate G9).
- **No tokens in HTML, page data, logs or browser storage;** state/nonce/PKCE, exact redirect URIs, callback
  replay rejected (gate G10).

## 7. Recovery

- **Linked Google:** a person with a linked Google identity can sign in with it when their email is
  unavailable (both identities link to the same person).
- **Operator recovery** (`docs/product/auth-recovery-runbook.md`): the owner verifies the person out of band,
  then runs `scripts/staging.sh relink <person> <new-email>` which creates/links the new identity and revokes
  the old one's sessions. Never automatic: a new address never silently takes over a person.
- Email change itself is out of scope for the beta.

## 8. Data and migration

- New table `identity_link(issuer, subject, person_id, email_at_link, linked_at)`, unique on `(issuer,
  subject)`. Person and reviewer grants move off the legacy `user.id` foreign keys
  (`identity/tables.py:22,49,133`) onto `person.id`.
- Removed after the switch, in the same change: legacy `user` credentials, sessions, verification and reset
  tokens, login throttle buckets that only served passwords.
- **Owner:** signs in once with an email code on staging; `scripts/staging.sh link-owner <email>` links that
  subject to the existing person (profile, jumps, reviewer grant kept). **Test accounts:** recreated by the
  owner signing in with test addresses, or discarded.
- **Erasure ledger:** replay understands `identity_link` and the provider subject (`recovery/ledger.py:56,371`);
  a restore drill (deletion, restore, replay) is part of the switch's checks.
- **Tooling:** `scripts/staging.sh create-account` and `identity/operator.py` (passwords) replaced by
  `link-owner`, `relink` and `grant-reviewer <person>`. `scripts/dev.sh` and `scripts/verify.sh` run a local
  **test identity provider** (section 11) so dev and e2e never touch Neon.

## 9. Gates (must pass on staging before the switch merges)

| Gate | Proves |
|---|---|
| G1 | Email-code sign-in and Google sign-in complete end to end with our own `/sign-in`, in Chromium **and** WebKit (Safari), with the Neon calls server-side; the Neon browser session can be ended. |
| G2 | The encrypted cookie fits (< 4 KB) and key rotation works (two keys accepted during rotation). |
| G3 | Refresh-token rotation and reuse behaviour; two parallel requests near expiry do not end the session. |
| G4 | A fresh re-authentication for sign-out-everywhere and deletion (fresh code; Google with `max_age`/`prompt` given Neon's loop). |
| G5 | Introspection returns `active: false` immediately after sign-out, token revocation, sign-out-everywhere and user deletion. |
| G6 | Webhook signature verification; delivery through Cloudflare Access (path-limited bypass). |
| G7 | Code requests do not reveal account existence. |
| G8 | Neon's limits for code sends/checks and `/oauth2/introspect` (rate, scope); ours sit in front. |
| G9 | Token lifetimes and session caps achievable (7 days absolute, 5 sessions) or a documented deviation approved by the owner. |
| G10 | state/nonce/PKCE enforced; redirect URI exact; replayed callback rejected; wrong issuer/audience/client rejected; JWKS rotation handled. |
| G11 | Password sign-in and sign-up are off at Neon (direct calls to the password endpoints fail). |
| G12 | Whether the first email-code sign-in creates a Neon user, and that identity linking applies the registration switch and ceiling. |
| G13 | Exit export: the `neon_auth` tables read back (users, accounts incl. Google links) with the owner's account present. |

## 10. Exit strategy

All auth data is in our database (`neon_auth`): `user` (id, email, verified), `account` (provider links:
`google`, email), `session`, `verification`. Passwordless means **no password hashes to move**.

1. **Self-hosted Better Auth** against the same tables: change the issuer in configuration; users sign in as
   before.
2. **Any other OIDC provider:** export users and Google links with SQL; import or let users sign in again by
   email code or Google; re-link `identity_link` by verified email (operator-run, logged).
3. **Google** keeps working because the Google OAuth client is the owner's own.
4. Our data never leaves our tables; `identity_link` is the only thing re-pointed.

`docs/product/auth-exit-runbook.md` (written with the switch): export queries, Google client ownership, relink
procedure. G13 proves the export.

## 11. Tests

- **Test identity provider** for dev and e2e: a small local OIDC server (discovery, authorize, token,
  introspect, revoke, JWKS, email-code issuing to the local mail outbox) started by `scripts/dev.sh` and
  `scripts/verify.sh`. It is standards-only, so the app cannot tell it from Neon; Neon-specific behaviour is
  covered by the staging gates.
- Rewritten: auth, account, privacy, boundaries and social suites' sign-in helpers (`web/tests/support/accounts.ts`)
  sign in through the test provider; the privacy and boundary assertions themselves stay unchanged.
- New: callback replay, wrong issuer/audience, expired and revoked tokens rejected at the API, introspection
  outage, read cache ≤ 30 s, mutations always live, encrypted cookie tampering, account existence privacy for
  code requests, throttles, deletion intent retries, restore replay.

## 12. Phases

1. **Gates on staging:** register a confidential client for staging, switch password sign-in off (G11), set
   the webhook and our SMTP for codes, run G1–G13 with a throwaway spike branch of the web app deployed to a
   local tunnel or preview (not merged), record results here. The owner approves the results.
2. **Build the switch** on one git branch: sections 3–8 and 11, old auth removed in the same change, full gate
   green, Codex review.
3. **Switch-over (one deploy):** Access bypass rules set; merge; owner signs in by code and runs `link-owner`;
   restore drill; exit export re-run.
4. **Google:** owner creates the Google OAuth client; configured in Neon; *Continue with Google* enabled.

## 13. Risks

- Neon's OAuth server is labelled **beta** in one Neon FAQ; behaviour can change. Mitigation: standards-only
  code, the test provider, and the exit strategy.
- **Cross-site cookies (G1)** are the most likely blocker: if Neon's sign-in cannot run server-side, the email
  path depends on third-party cookies, which Safari blocks.
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
