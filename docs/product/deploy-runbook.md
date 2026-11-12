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
- Python: 3.14 (`backend/.python-version`, `requires-python = ">=3.14"`). Finding
  2026-11-12: FastAPI Cloud's build has no Python 3.15 ("No interpreter found for
  Python 3.15+gil in managed installations"; its uv predates 3.15), so the backend
  moved to 3.14, the minimum the code needs (`uuid.uuid7`). Do not pin a patch
  release: the host offers whichever 3.14.x its uv knows.
- Neon integration: link the staging database; it sets `DATABASE_URL`. Whether it
  injects the pooled or direct string is untested; the backend accepts either.
- Environment variables:

| Name | Value |
| --- | --- |
| `ENVIRONMENT` | `staging` |
| `PROJECT_NAME` | `Load Organiser` |
| `SECRET_KEY` | secret (see above) |
| `SKYDIVER_WEB_ORIGIN` | the Worker's https address, `https://load-organiser.metalcorpe.workers.dev` |
| `SKYDIVER_WEB_PROXY_KEY` | secret, the shared proxy key |
| `SKYDIVER_REQUIRE_PROXY_KEY` | `true`: closed beta, the API answers only the web server (others get 404; health stays open) |
| `SKYDIVER_MIGRATE_ON_START` | `true`: migrations run when the app starts (see "Order of a deploy") |
| `SKYDIVER_BOOTSTRAP_REVIEWER` | your email: the reviewer role is granted at start-up once that account exists |
| `SKYDIVER_REGISTRATION_OPEN` | `true` with `SKYDIVER_MAX_ACCOUNTS=1`: you register on the site, nobody else can (needs mail) |
| `SKYDIVER_SUBMISSIONS_OPEN` | `false` until the review routine is in use |
| `SKYDIVER_PUBLISHING_OPEN` | `false` until there is someone to share with |
| `SKYDIVER_MAX_ACCOUNTS` | `1` while staging is owner-only |

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

- The Worker is named `load-organiser` (as in the dashboard; `web/wrangler.jsonc` must
  use the same name). Finding 2026-11-12: with the root directory unset, Workers Builds
  built the old template frontend (`frontend/`, "Full Stack FastAPI Project"); the root
  directory must be `web`.
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

1. Migrations run when the app starts (`SKYDIVER_MIGRATE_ON_START=true`,
   `backend/app/skydiver/migrate.py`): over Neon's direct host (the `-pooler` part is
   dropped from the injected `DATABASE_URL`), in one transaction, without locks. When
   several instances start at once, one applies them and the others roll back and go
   on. A failed migration stops the new instances; the running ones keep serving. A
   migration must work with the code that is still running (FastAPI Cloud replaces
   instances gradually): add before using; stop using before removing.
   Export files are checked strictly (`backend/app/skydiver/records/format.py`: unknown
   keys are refused). A file exported by new code with a new optional key (e.g.
   `jumps[].aircraft`, `components[].jump_limit`) is refused by an instance still on the
   old code, with nothing written. So restore is not safe in the middle of a rollover:
   wait until every instance runs the new code before restoring a new file. Older files
   restore on new code.
   `scripts/staging.sh` stays available for status checks and manual runs.
2. Merge to `main`: FastAPI Cloud and Cloudflare each build and deploy from it.
3. Check the API health address, then the web address.

First time only, after step 3: register on the web address with the email in
`SKYDIVER_BOOTSTRAP_REVIEWER`, confirm it from the Resend mail, then redeploy (or wait
for the next deploy) so the reviewer role is granted. Without mail, use
`scripts/staging.sh create-account` and `grant-reviewer` instead.

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

## Closed beta (owner decision 2026-11-12)

- **Web:** Cloudflare Access on the Worker (Workers & Pages → `load-organiser` →
  Access → Protect this Worker behind Access → All traffic → allowed emails). Visitors
  prove an allowed email with a one-time code before the app runs.
- **API:** `SKYDIVER_REQUIRE_PROXY_KEY=true`. Every call from the web server carries
  `SKYDIVER_WEB_PROXY_KEY` (`x-organiser-proxy-key`); anything else gets a plain 404,
  except `/api/skydiver/v1/health`. The key must be identical on both sides (Cloudflare
  secret `API_PROXY_KEY`), or every page reports the service as unavailable.
