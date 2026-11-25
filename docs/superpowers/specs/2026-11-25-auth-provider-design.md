# Delegating authentication to Neon's Managed Better Auth — design (draft for owner approval)

Owner request, 2026-11-25: hand sign-in and sessions to a maintained provider, keeping the web app (FE)
and API (BE) as provider-agnostic as possible. Owner decisions so far: **managed Neon Auth**, the
**latest version Neon offers**, a **clean break** (no feature flag, no parallel old/new auth, no separate
Neon branch), and an **exit strategy settled before starting** (below). Nothing is built until this note is approved. Facts about Neon and Better
Auth below were checked in their documentation on 2026-11-25 (sources at the end); items marked
**verify** could not be confirmed from the docs and are checked in phase 0 against a real instance.

## Why

- A maintained, widely used auth library instead of our own code for the security-critical parts
  (sign-in, sessions, reset, verification), with features we would otherwise build ourselves: social
  sign-in (Google, Apple, Microsoft, GitHub), magic links / email codes, later passkeys and MFA.
- Provider independence: the app speaks standards (OAuth 2.1 / OpenID Connect), so the provider can be
  replaced by configuration plus one small adapter.

## What Neon provides today (checked 2026-11-25)

| Topic | Neon Managed Better Auth |
|---|---|
| Version | Better Auth **1.7.12**, run by Neon in **the same region as the database**; clients `@neon/auth` 0.8.1+ or any Better Auth 1.7+ client. Upstream Better Auth already has a 1.8 line; Neon chooses when to move. |
| Data | Users, accounts, sessions in our own Neon database, schema `neon_auth` (branches with the database). Counts toward our Neon compute and storage. |
| Price | Included in the Neon plan; Free up to 60,000 monthly active users per project. |
| Sign-in methods | Email + password; social OAuth (Google, GitHub, Vercel, Microsoft, Apple); plugins Email OTP, Magic Link, Phone Number, Admin, JWT, Open API; Organization partial. MFA and Admin customisation on Neon's roadmap. **No custom plugins or custom hooks.** |
| Sessions | Server-side sessions in `neon_auth.session`; revocation per session, others, all; password change can revoke other sessions in the same transaction. Optional signed cookie cache (revocation window = its `maxAge`). |
| JWT | JWT plugin: JWKS at `<auth URL>/.well-known/jwks.json`, EdDSA (Ed25519), 15-minute tokens, no custom claims; not a browser session substitute. |
| OAuth/OIDC provider | OAuth Provider plugin (Neon: available, one FAQ says **beta**): Neon runs discovery, JWKS and token issuance; we host login and consent pages; no `client_credentials`, fixed scopes, ≤100 clients per branch, ≤10 redirect URIs each. Requires naming at least one protected resource. Neon ships `@neon/oauth` for token verification. |
| Introspection / back-channel logout | Upstream Better Auth 1.7+: RFC 7662 `/oauth2/introspect` (client auth, also checks the session behind the token, **default rate limit 100 requests / 60 s**) and OIDC Back-Channel Logout (signed logout token, 120 s, `sid`, one attempt, 5 s timeout, needs the JWT plugin; clients holding only a JWT access token are not notified). **Verify** both are exposed by Neon's managed instance (its discovery document), and whether the rate limit can be changed (likely not: no custom configuration beyond what Neon exposes). |
| Email | Shared sender `auth@mail.myneon.app` is **development only**, rate-limited and **cannot send verification links** (codes only). Production: our own SMTP (Neon's default templates, our From address) or **webhooks** (Neon calls our handler instead of sending, for our own templates). Reset by link arrives as a `send.magic_link` event. |
| Account existence | Better Auth 1.5+: with email verification required (or auto sign-in off), sign-up returns the same 200 for new and existing emails and simulates hashing time. |

## Target architecture

```
Browser ── HttpOnly cookie (opaque) ──► Web server (SvelteKit Worker) = OIDC client (BFF)
                                          │  authorization code + PKCE with Neon Auth
                                          │  keeps the provider tokens server-side
                                          ▼
                                 API (FastAPI) = resource server
                                   validates the access token on each call (below)
                                   owns all skydiver data, keyed by the provider's stable `sub`
                                          │
                                          ▼  standards only (discovery, JWKS, introspection)
                                 Neon Managed Better Auth (issuer)
                                   accounts, credentials, sessions, revocation, auth emails
```

- **FE stays agnostic:** it talks only to our web server and API, as today. Sign-in pages become an OIDC
  redirect (or our own pages calling the provider's client API, decided in phase 1); the browser never
  holds a token it can read.
- **BE stays agnostic:** the API accepts "a valid token from the configured issuer for our audience".
  Provider-specific code lives in one adapter (`AccountAdmin`: delete a user and their sessions, list
  sessions), used by account deletion and erasure.
- **Our data** (jumps, gear, profile, follows, listings) stays in our tables; `person` gains the
  provider's `sub` as the link. Swapping providers later = configuration + a new `AccountAdmin` adapter +
  re-linking `sub`.

### Token validation (the revocation guarantee)

- **Preferred — A. Introspection (RFC 7662)** with a 30-second cache per token (as the current session
  reuse): revocation (sign-out everywhere, password reset, deletion) takes effect within 30 s, the
  guarantee the current auth tests check. One call to Neon per uncached request; Neon runs in the
  database's region.
  - Rate limit: Better Auth's default is **100 introspections per 60 s** per instance. At beta scale
    (one owner, a few testers) with a 30 s cache per token, use is a few per minute. It becomes a limit
    around 50+ concurrently active users; the fallback below then applies. **Verify** the limit Neon
    applies and whether it can be raised.
- **Fallback — B. Short JWT access tokens (RFC 9068)** verified locally against the issuer's JWKS, no
  call per request; revocation waits for expiry (Neon: 15 min), refresh tokens revoked at the provider.
  Used if Neon does not expose introspection, or if A hits the rate limit.
- **Plus back-channel logout** (if Neon exposes it): the web server drops a session as soon as the
  provider ends it. A bonus, not the guarantee (one attempt, not sent for JWT-only clients). Staging
  sits behind Cloudflare Access, so the logout endpoint needs an Access bypass rule for the provider's
  requests (path-limited, signed logout tokens verified against JWKS).

## Emails (which ones, and who sends them)

Today the API sends three, through our SMTP mailer (`backend/app/skydiver/identity/service.py`):

| Today | After |
|---|---|
| **Confirm your email address** (sign-up, resend) | Neon Auth, as a verification **link** → needs our SMTP or a webhook (the shared sender cannot send links). |
| **Reset your password** (link, 30 min, single use) | Neon Auth (`send.magic_link` event for a reset link), same requirement. |
| **"Sign-in help"** to an existing account when someone signs up with its address (keeps account existence private) | Better Auth returns the same response (enumeration-safe), but sending this hint needs its `onExistingUserSignUp` hook, which Neon's managed service does not allow. **Decision for the owner:** drop the hint email (privacy unchanged; the existing owner just gets no notice), or send it from a Neon webhook if one covers this event (**verify**). |

Recommendation: **webhooks**, so the texts stay ours (plain, the current wording) and are sent by the
same SMTP account we already have; no new paid service. Webhook handler on the API, signature-verified,
behind the same Access bypass consideration as back-channel logout.

## Constraints carried over (must hold after the move)

- Do not expose account existence (sign-up, reset, sign-in responses identical).
- Do not weaken password rules: today **15–128 characters**, no composition rules, never trimmed.
  **Verify** Neon lets us set the minimum to 15 (Better Auth's default is 8).
- Throttling at least as strict as today (login 10 per 15 min per pair / 50 per IP; reset 3 per hour
  per address / 10 per IP; registration 3 per hour per address / 10 per IP). **Verify** what Neon applies
  and whether it is configurable; otherwise keep our own limits in front (the web server already sees
  every sign-in request).
- Sessions: HttpOnly, Secure, SameSite=Lax cookie; no raw tokens in HTML, page data or logs; revocation
  within 30 s; at most a fixed number of active sessions per account (today 5, **verify**).
- Account deletion and erasure reach `neon_auth` (via `AccountAdmin`) and keep the erasure ledger.
- No paid services, no new infrastructure beyond Neon Auth itself (owner: free stack).
- Social sign-in apps (Google, Apple) are registered under the owner's own developer accounts.

## Phase 0 findings (2026-11-25, read-only via the Neon CLI; nothing changed in Neon)

Owner decisions recorded: **our own sign-in pages**; **Google** as the first social sign-in.

- Project `rough-paper-15304455`, region **aws-eu-central-1** (Frankfurt). Neon Auth runs in the same
  region (`base_url` `https://ep-winter-math-b9muy5c8.neonauth.c-7.eu-central-1.aws.neon.tech/neondb/auth`).
  Side finding: the API runs in **us-east-1**, so every API database query crosses the Atlantic (the
  ~180–210 ms per call measured earlier).
- JWKS published at `<base_url>/.well-known/jwks.json`, one EdDSA/Ed25519 key.
- **No OIDC discovery, no introspection, no back-channel logout yet:** `/.well-known/openid-configuration`
  and `/.well-known/oauth-authorization-server` return 404. They belong to the OAuth-server plugin
  (`oauth_provider`), which is disabled; enabling it needs a login page URL, a consent page URL and at
  least one protected resource (`neon neon-auth config oauth-server update`). Whether it then offers
  RFC 7662 introspection and back-channel logout is still to be checked after enabling.
- Email and password: enabled; verification **required**, by **code** (`otp`), auto sign-in after
  verification; **sessions revoked on password reset**. **No password-length setting** in Neon's
  configuration: Better Auth's default minimum applies (8), below today's 15.
- Email sender: Neon's **shared** sender (development only). Webhooks off; available events
  `user.before_create`, `user.created`, `send.otp`, `send.magic_link` — **no event for a sign-up with an
  existing address**, so the "sign-in help" email cannot be kept.
- Google sign-in already enabled with Neon's **shared** credentials; must be replaced by the owner's own
  Google OAuth client (exit strategy) before anyone uses it.
- Not visible in the configuration: rate limits and the active-session cap.
- Exit export: not run yet (no users in `neon_auth`); run after the owner's account exists.

### Decisions these findings raise

1. **Password minimum 15 vs Neon's 8.** Our own pages can refuse under 15, but Neon's sign-up endpoint is
   public, so someone calling it directly could still create an account with 8–14 characters
   (`user.before_create` does not receive the password). Options: accept Neon's minimum; or keep the
   15-character rule only in our pages (best effort); or self-host Better Auth (full control, loses
   "managed").
2. **How the API validates sessions without introspection:**
   - (i) enable Neon's OAuth server (beta) for standard OIDC + introspection, with our own login page; or
   - (ii) no OAuth server: our pages call Neon Auth's API; the web server checks the session with Better
     Auth's session endpoint (30-second cache, immediate revocation within 30 s) and passes the API a
     15-minute EdDSA JWT verified against JWKS. Provider-specific code stays inside the web server's auth
     adapter.



Neon keeps all auth data in **our own database** (schema `neon_auth`), so leaving is an export, not a
negotiation.

| Table (Better Auth standard) | Contents | On exit |
|---|---|---|
| `user` | id, email, name, `emailVerified`, timestamps | Exported: every account with its verified status |
| `account` | one row per sign-in method: `providerId` (`credential`, `google`, `apple`…), provider account id; for `credential` the **password hash** | Exported: passwords and social links can move |
| `session` | active sessions | Not moved: everyone signs in once more |
| `verification` | pending verification/reset tokens | Not moved: they expire within minutes |

Ways out, in order of preference:

1. **Self-hosted Better Auth** (same version line): same tables and hash format; point it at the
   `neon_auth` tables (or a copy), change the issuer URL in configuration. Users keep their passwords; the
   app is unchanged because it speaks only OIDC/OAuth to the issuer.
2. **Another provider:** plain SQL export of `user` and `account`. If it imports Better Auth's hash format
   (scrypt by default, **verify** Neon's parameters), passwords move as they are; otherwise a **lazy
   migration** (on first sign-in, check against the old hash, then store in the new system) and a reset
   link for anyone who never returns.
3. **Social sign-in** keeps working only if the new system uses the **same** Google/Apple developer apps:
   Google's user id is stable per account, Apple's is tied to the developer team. So these apps are
   registered under the owner's own accounts from the start, never Neon's shared credentials.
4. **Our data** (jumps, gear, profile, follows, listings) never leaves our tables. `person` keeps the auth
   user id (`sub`); on exit a one-off mapping (old id → new id) relinks everyone.

Kept true while on Neon:

- Nothing the app needs is stored only in Neon's settings or custom fields; app data stays in our tables.
- The export works: phase 0 runs the export queries on staging (read-only) and records the hash format.
- `docs/product/auth-exit-runbook.md`: the export queries, the hash format, the social app ownership and
  the relink step, kept next to the deploy runbook.

## Phases

Clean break: no feature flag, no old and new auth side by side, no separate Neon branch. Code work on a
git feature branch as always.

0. **Verify on staging (no app change):** the owner enables Neon Auth on the **staging project** (this
   creates the `neon_auth` schema in the staging database: a write to the hosted database, so the owner
   does it or explicitly asks for it). Then read the instance's discovery document; confirm introspection,
   back-channel logout, rate limits, password minimum, throttling, session caps, webhook events; send a
   test email through our SMTP; run the exit export queries read-only and record the hash format. Write
   the findings into this note; the owner decides A or B and the "sign-in help" question.
1. **Build the switch on one branch:** OIDC client in the web server, introspection (or JWT) validator in
   the API, `person.sub`, `AccountAdmin` adapter (deletion and erasure), webhook email handler,
   back-channel logout endpoint, the exit runbook; the old session code and its tables removed in the same
   change. The auth e2e suite rewritten around the new flow with the same revocation, enumeration,
   password-rule and throttling assertions; full gate green.
2. **Switch-over (one deploy):** merge; the owner's account is re-created in Neon Auth and relinked to
   their existing person (the beta cohort is only the owner); Cloudflare Access bypass rules for the two
   provider-facing endpoints set before the merge.
3. **Optional later:** Sign in with Google / Apple (developer apps under the owner's accounts, then
   configuration in Neon + a button), passkeys when Neon offers them.

## Risks

- **Beta features:** Neon's OAuth Provider plugin is labelled beta in one place; behaviour may change.
- **Lock-in where the managed service limits us:** no custom hooks or plugins; anything Neon does not
  expose cannot be added (mitigated by keeping all non-auth data ours and the adapters small).
- **Clean break:** no fallback to the old auth after the switch; a problem found after merging is fixed
  forward (or the merge reverted as a whole). The full gate and the rewritten auth suite are the safety net.
- **A new trust path:** a bug in token validation is a bug in authorisation; covered by the existing
  boundary and privacy suites, run unchanged against the new flow.
- **Cloudflare Access:** two public endpoints (back-channel logout, email webhook) need bypass rules on
  staging.
- **Neon compute:** auth queries run on our database, so they count toward the 100 CU-hours; small at
  beta scale.

## Open questions for the owner

1. "Sign-in help" email: drop it, or keep it via webhook if possible (after phase 0)?
2. Our own sign-in pages (calling Neon's client API, same look) or Neon's hosted pages (simpler, less
   control over wording and design)?
3. Which social providers first, if any (Google, Apple)?

## Sources (checked 2026-11-25)

- Neon: [Managed Better Auth overview](https://neon.com/docs/auth/overview), [About](https://neon.com/docs/auth/about),
  [Plugins](https://neon.com/docs/auth/guides/plugins), [OAuth Provider](https://neon.com/docs/auth/guides/plugins/oauth-provider),
  [JWT](https://neon.com/docs/auth/guides/plugins/jwt), [Customize emails](https://neon.com/docs/auth/guides/customize-emails),
  [Email verification](https://neon.com/docs/auth/guides/email-verification), [Webhooks](https://neon.com/docs/auth/guides/webhooks),
  [Production checklist](https://neon.com/docs/auth/production-checklist), [Roadmap](https://neon.com/docs/auth/roadmap),
  [Managed vs self-hosted](https://neon.com/faqs/managed-better-auth-vs-self-hosting-better-auth),
  [Free up to 60,000 MAU](https://neon.com/faqs/free-auth-service-60000-monthly-active-users),
  [OAuth provider blog](https://neon.com/blog/managed-better-auth-oauth-provider-mcp)
- Better Auth: [OAuth 2.1 Provider](https://better-auth.com/docs/plugins/oauth-provider),
  [OpenID Connect and logout](https://better-auth.com/docs/plugins/oauth-provider/openid-connect),
  [Provider reference](https://better-auth.com/docs/plugins/oauth-provider/reference),
  [Session management](https://better-auth.com/docs/concepts/session-management),
  [Email & password](https://better-auth.com/docs/authentication/email-password),
  [1.7 release](https://better-auth.com/blog/1-7)
