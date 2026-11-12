# Staging deployment runbook (#161)

Status 2026-11-12: written before the first deploy. Nothing here has run against the
hosted services yet; each step says what to check. Owner decisions the same day:
staging, owner only; the free `*.workers.dev` address; no mail sender yet.

```
browser ──https──> Cloudflare Worker (web/, SvelteKit)
                     │ server-only fetch, API_PROXY_KEY
                     ▼
                   FastAPI Cloud (backend/)  ──>  Neon PostgreSQL
```

The browser never talks to the API directly. Real listings and real records wait for
the backup and restore drill below (release gate in the issue).

## Secrets

Generate each secret on your own machine, for example `openssl rand -base64 48`, and
paste it only into the service's own dashboard or CLI. Never into chat, the repository
or an issue.

| Secret | Where |
| --- | --- |
| `SECRET_KEY` | FastAPI Cloud (secret) |
| Proxy key (one value, 32+ characters) | FastAPI Cloud `SKYDIVER_WEB_PROXY_KEY` and Cloudflare `API_PROXY_KEY`, both secret |
| Neon connection strings | Injected by the FastAPI Cloud Neon integration (`DATABASE_URL`); the direct one is used only in your terminal for `scripts/staging.sh` |

## 1. Neon

- One project for staging. Note the region you chose (data location).
- Two connection strings: the pooled one (host contains `-pooler`) and the direct one.
  Operator commands use the direct one; `scripts/staging.sh` refuses the pooled one.

## 2. FastAPI Cloud (API)

- Application directory: `backend`. The app is found at `app/main.py` (`app`).
- Python: the project requires 3.15 (`backend/pyproject.toml`, `backend/.python-version`).
  **Untested whether FastAPI Cloud offers 3.15**; if the build fails on the version,
  that is the first finding to record here.
- Neon integration: link the staging database; it sets `DATABASE_URL`. Whether it
  injects the pooled or direct string is untested; the backend accepts either.
- Environment variables:

| Name | Value |
| --- | --- |
| `ENVIRONMENT` | `staging` |
| `PROJECT_NAME` | `Load Organiser` |
| `SECRET_KEY` | secret (see above) |
| `SKYDIVER_WEB_ORIGIN` | the Worker's https address, e.g. `https://load-organiser-web.<your-subdomain>.workers.dev` |
| `SKYDIVER_WEB_PROXY_KEY` | secret, the shared proxy key |
| `SKYDIVER_REGISTRATION_OPEN` | `false` (no mail sender: registration cannot confirm addresses) |
| `SKYDIVER_SUBMISSIONS_OPEN` | `false` until the review routine is in use |
| `SKYDIVER_PUBLISHING_OPEN` | `false` until there is someone to share with |
| `SKYDIVER_MAX_ACCOUNTS` | `5` |

Leave unset: `LEGACY_API_ENABLED`, `SKYDIVER_MAIL_OUTBOX_DIR` (both refused outside
local), `FIRST_SUPERUSER*` (not used by the beta), `EMAILS_FROM_NAME` (falls back to
`PROJECT_NAME`).

Mail through Resend (optional; owner chose Resend on 2026-11-12). Without these the API
runs with no mail: registration and password reset are unavailable and your account
comes from `scripts/staging.sh create-account`.

| Name | Value |
| --- | --- |
| `SMTP_HOST` | `smtp.resend.com` |
| `SMTP_PORT` | `587` |
| `SMTP_TLS` | `true` (STARTTLS) |
| `SMTP_USER` | `resend` |
| `SMTP_PASSWORD` | secret: a Resend API key with sending access only |
| `EMAILS_FROM_EMAIL` | `onboarding@resend.dev` until a domain is verified in Resend |

With the `resend.dev` sender, Resend delivers only to the address of the Resend account
itself, which fits an owner-only staging; other people need a verified domain. Untested
against Resend until the first deploy: send yourself a password reset to check.

- Check: `https://<api-address>/api/skydiver/v1/health` answers `{"status":"ok","database":"ok",...}`.

## 3. Cloudflare Workers Builds (web)

- Root directory: `web`. Build command: `npm ci && npm run build`. Deploy command:
  `npx wrangler deploy`. Production branch: `main`. Builds for other branches: off.
- `web/wrangler.jsonc` turns on the `*.workers.dev` address, keeps pull-request preview
  URLs off and keeps dashboard variables across deploys (`keep_vars`).
- Variables (Settings → Variables and secrets):

| Name | Value |
| --- | --- |
| `API_ORIGIN` | `https://<api-address>` (https only; see `web/src/env.ts`) |
| `APP_ORIGIN` | the Worker's own https address, exactly as the browser shows it |
| `API_PROXY_KEY` | secret, the shared proxy key |

`SESSION_COOKIE_MODE` stays unset (`secure`: `__Host-` cookie).

## 4. Order of a deploy

1. Migrations first, from your terminal: `export DATABASE_URL='<direct string>'`, then
   `scripts/staging.sh status` and `scripts/staging.sh migrate`. A migration must work
   with the code that is still running (FastAPI Cloud replaces instances gradually):
   add before using; stop using before removing.
2. Merge to `main`: FastAPI Cloud and Cloudflare each build and deploy from it.
3. Check the API health address, then the web address.

First time only, after step 3:
- `scripts/staging.sh create-account you@example.com` (asks for the password twice),
- `scripts/staging.sh grant-reviewer you@example.com`.

## 5. Smoke check (record results in this file)

- [ ] `/` loads over https; `/status` shows the API reachable.
- [ ] Sign in; the cookie is `__Host-organiser_session`, Secure, HttpOnly.
- [ ] Log a jump, open it, edit it; Logbook and History show it.
- [ ] Export your data; "Check file" on the export answers that it holds 1 jump.
- [ ] Sign out; Back does not show the logbook.
- [ ] A cross-site POST is refused: `curl -i -X POST -H 'Origin: https://evil.example' https://<web-address>/sign-in` answers 403.
- [ ] The API refuses a request without a session: `curl -i https://<api-address>/api/skydiver/v1/jumps` answers 401.
- [ ] Cold start: first request after idle, note the time.

## Not done yet (gates before real data or other people)

- **Backups and a restore drill on the hosted database** (#161): destination, schedule,
  key custody, and a restore with erasure replay (`recovery-runbook.md`). Until then,
  staging holds test data only.
- **Mail to other people**: Resend's test sender reaches only your own address; anyone
  else needs a verified domain in Resend.
- **Custom domain**: sessions are per address, so moving from `workers.dev` signs
  everyone out once.
- **Free-tier limits and failure behaviour**: record the actual limits of each account
  here; no paid upgrade without an owner decision.
- **Vercel**: the repository is also connected to Vercel, which builds every branch
  behind Vercel's login. It is not part of this setup; disconnect it to avoid two web
  hosts.
