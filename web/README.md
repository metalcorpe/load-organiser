# Load Organiser web (SvelteKit)

Mobile-first SvelteKit 3 / Svelte 5 / TypeScript 6 application for the skydiver beta, built with the
official Cloudflare adapter for Workers. Scope and boundaries: [architecture](../docs/product/architecture.md),
[data contracts](../docs/product/data-contracts.md), [handoff](../docs/product/claude-code-handoff.md).

`../frontend/` (React) stays in the repository as the reference/rollback input until a verified cutover.

## Status (#144, #145, #148)

Shell, navigation, route/layout boundaries, the server-only API transport, one real unauthenticated
API flow (`/status`) and accounts: registration with email confirmation, sign-in/out, seven-day
revocable sessions, password reset/change and sign-out everywhere; the dropzone directory and private
provisional places. Opportunity discovery, the logbook/gear records and social features are **not
implemented**; their screens say so explicitly.

## Route inventory

| Route | Access | Behaviour in #144 |
| --- | --- | --- |
| `/` Discover | Public SSR | Explains that no listings are published. No fixture or sample listings |
| `/dz` | Public SSR | Directory search (name/alias/former name, country) over listed and closed venues; keyset “More results”; honest empty state (#148). `?view=map`: the same search on an OpenStreetMap map, loaded only after “Show map” ([map view](../docs/product/dropzone-directory.md#map-view)) |
| `/dz/[id]` | Public SSR | Sourced venue detail; closed label; merged IDs answer `301` to the surviving venue; drafts and unknown IDs `404` |
| `/places` | Private | Owner-only provisional places: add (name + country), edit, link to/unlink from a listed venue, remove |
| `/status` | Public SSR | Live `GET /api/skydiver/v1/health` via the server transport: operational / degraded (DB down) / timeout / unreachable / unexpected response / not configured |
| `/sign-in` | Public SSR, `noindex` | Form action; returns to a safe `returnTo`; a new sign-in revokes the browser's previous session |
| `/register` | Public SSR, `noindex` | Neutral “check your email” answer whether or not the address already has an account |
| `/verify-email?token=` | Public SSR, `noindex` | GET never consumes the token; the visitor confirms with a POST |
| `/forgot-password`, `/reset-password?token=` | Public SSR, `noindex` | Neutral acknowledgement; reset revokes every session |
| `/sign-out` | POST action | Revokes the backend session, clears the cookie, sends `Clear-Site-Data: "cache"` |
| `/profile` | Private | Me overview: account email and confirmation status/resend, sign out, grouped links to records, people and settings; licence and exit weight forms |
| `/profile/account` | Private | Account and security: session end, change password (others signed out), sign out everywhere and delete account (password required) |
| `/activity`, `/jumps/new`, `/records` | Private `(private)` group | Reachable when signed in; still “Not available yet”. Unconfirmed accounts see why private writes will be blocked |
| (any private route, anonymous) | — | `303` → `/sign-in?returnTo=…` (HTML and data requests from `handle`; the layout load forces the server round trip) |
| anything else | — | `404` error page |

React routes **not** ported (excluded from the beta per the handoff, #146): aircraft, instructors,
loads/manifest, operational jumps, weather, analytics, items, admin/user administration. Login,
signup and password recovery are replaced by #145's session design, not ported.

## Boundaries implemented

- **Transport:** `src/lib/server/api/` (server-only). One transport per request, global `fetch` (not
  `event.fetch`, which forwards browser cookies to same-site origins), fixed allowlisted operations,
  `redirect: 'manual'`, 5 s timeout, 64 KiB body cap, runtime shape validation, sanitized failure kinds.
- **Configuration:** `API_ORIGIN` is declared in `src/env.ts` and read from `$app/env/private`. It must be
  an `https` origin (plain `http` only for loopback) without path or credentials. Unset → requests fail closed.
- **Contract types:** `contracts/skydiver-v1.openapi.json` is exported from the backend beta router only
  (`app.skydiver.openapi`); `npm run contracts:generate` writes types-only output to
  `src/lib/contracts/generated`. A backend test fails if the committed document drifts.
- **Sessions (#145):** the API issues an opaque 256-bit secret (stored there only as SHA-256). The web
  server keeps it in `__Host-organiser_session` (Secure, HttpOnly, SameSite=Lax, Path=/, no Domain) and
  sends it to the API as a bearer credential on each request; the viewer is resolved per request and
  only minimal identity reaches page data. `SESSION_COOKIE_MODE=localhost-dev` (loopback `APP_ORIGIN`
  only) is the sole non-Secure option.
- **Origin:** every unsafe method must carry exactly `APP_ORIGIN` (absent, `null` or other origins get
  403), in addition to SvelteKit's own form check. Unset `APP_ORIGIN` refuses all unsafe requests.
- **Headers:** every dynamic response is `Cache-Control: no-store`, with CSP (hashed scripts,
  `frame-ancestors 'none'`; images from 'self', `data:` and `https://tile.openstreetmap.org` for the dropzone map; inline style *attributes* only, because SvelteKit emits them), `nosniff`,
  `Referrer-Policy: same-origin`. Data preloading is disabled.

## Commands

Node `>=22.17` (`.nvmrc` pins 26.13.0, matching the dependency refresh).

```sh
npm ci
npm run check        # wrangler type drift + svelte-check + node-side tsc (clears .svelte-kit/cloudflare)
npm run test:unit    # vitest
npm run build        # Cloudflare Workers output in .svelte-kit/cloudflare
npm run preview      # wrangler dev (local workerd); pass --var API_ORIGIN:… --var APP_ORIGIN:…
E2E_API_ORIGIN=http://127.0.0.1:8144 E2E_MAIL_OUTBOX=<dir> E2E_API_PROXY_KEY=<key> \
  npm run test:e2e   # build + Playwright against three workerd previews (one HTTPS)
```

| Variable (private) | Purpose |
| --- | --- |
| `API_ORIGIN` | Fixed FastAPI origin; unset fails closed |
| `APP_ORIGIN` | Exact public origin required on unsafe requests; unset refuses them |
| `SESSION_COOKIE_MODE` | `secure` (default) or `localhost-dev` for a loopback `APP_ORIGIN` |
| `API_PROXY_KEY` | 32+ chars, equal to the backend's `SKYDIVER_WEB_PROXY_KEY`; lets the API throttle by client address |

`wrangler dev` runs locally and needs no Cloudflare account. `wrangler.jsonc` disables `workers_dev`
and preview URLs; nothing here deploys.

### Isolated backend for the e2e run

Never run the backend from `backend/` for this: `Settings` reads `../.env` relative to the working
directory. Use an empty scratch directory and explicit throwaway values, e.g.:

```sh
cd "$(mktemp -d)" && env -i PATH="$PATH" HOME="$HOME" ENVIRONMENT=local PROJECT_NAME=e2e \
  SECRET_KEY=<random> POSTGRES_SERVER=127.0.0.1 POSTGRES_PORT=<disposable-port> \
  POSTGRES_USER=<user> POSTGRES_PASSWORD=<random> POSTGRES_DB=<disposable-db> \
  FIRST_SUPERUSER=admin@example.com FIRST_SUPERUSER_PASSWORD=<random> \
  uv run --project <repo>/backend uvicorn app.main:app --host 127.0.0.1 --port 8144
```

Add for the account tests: `SKYDIVER_REGISTRATION_OPEN=true SKYDIVER_MAX_ACCOUNTS=1000
SKYDIVER_WEB_ORIGIN=https://127.0.0.1:4175 SKYDIVER_WEB_PROXY_KEY=<key> SKYDIVER_MAIL_OUTBOX_DIR=<dir>`,
run `alembic upgrade head` against the disposable database first, and use a **fresh database per run**:
throttle windows persist (for example, 10 reset requests per hour from 127.0.0.1). The file outbox
is local-only and is not evidence of real mail delivery.
