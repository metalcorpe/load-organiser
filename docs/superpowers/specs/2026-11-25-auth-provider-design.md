# Delegating authentication to Neon's Managed Better Auth — design (draft for owner approval)

Owner request, 2026-11-25: hand sign-in and sessions to a maintained provider, keeping the web app (FE)
and API (BE) as provider-agnostic as possible. Owner decisions so far: **managed Neon Auth**, the
**latest version Neon offers**. Nothing is built until this note is approved. Facts about Neon and Better
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

## Phases

0. **Spike (no app change):** enable Neon Auth on a **non-staging branch** of the Neon project; read its
   discovery document; confirm introspection, back-channel logout, rate limits, password minimum,
   throttling, session caps, webhook events; send a test email through our SMTP. Write the findings into
   this note; owner decides A or B and the "sign-in help" question.
1. **Adapters, no behaviour change:** API token validation behind an interface with today's sessions as
   the first implementation; `person.sub` column; `AccountAdmin` port. Existing tests unchanged.
2. **Neon Auth behind the interface:** OIDC client in the web server, introspection (or JWT) validator in
   the API, webhook email handler, back-channel logout endpoint; feature-flagged, off on staging.
3. **Switch-over:** owner's account re-created or linked (beta cohort is only the owner); auth e2e suite
   rewritten around the new flow, with the same revocation, enumeration, password-rule and throttling
   assertions; flag on in staging; old session code removed after a week.
4. **Optional later:** Sign in with Google / Apple (configuration in Neon + a button), passkeys when Neon
   offers them.

## Risks

- **Beta features:** Neon's OAuth Provider plugin is labelled beta in one place; behaviour may change.
- **Lock-in where the managed service limits us:** no custom hooks or plugins; anything Neon does not
  expose cannot be added (mitigated by keeping all non-auth data ours and the adapters small).
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
