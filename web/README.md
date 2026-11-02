# Load Organiser web (SvelteKit)

Mobile-first SvelteKit 3 / Svelte 5 / TypeScript 6 application for the skydiver beta, built with the
official Cloudflare adapter for Workers. Scope and boundaries: [architecture](../docs/product/architecture.md),
[data contracts](../docs/product/data-contracts.md), [handoff](../docs/product/claude-code-handoff.md).

`../frontend/` (React) stays in the repository as the reference/rollback input until a verified cutover.

## Status (#144)

This is the foundation only: shell, navigation, route/layout boundaries, the server-only API transport
and one real unauthenticated API flow (`/status`). Discovery, accounts, records and social features
are **not implemented**. Their screens say so explicitly. Sessions/accounts are #145.

## Route inventory

| Route | Access | Behaviour in #144 |
| --- | --- | --- |
| `/` Discover | Public SSR | Explains that no listings are published. No fixture or sample listings |
| `/status` | Public SSR | Live `GET /api/skydiver/v1/health` via the server transport: operational / degraded (DB down) / timeout / unreachable / unexpected response / not configured |
| `/sign-in` | Public SSR, `noindex` | States that accounts are not available yet. Preserves `returnTo` in the URL for #145; renders no form |
| `/activity`, `/jumps/new`, `/records`, `/profile` | Private `(private)` group | Anonymous requests get `303` → `/sign-in?returnTo=…` (HTML from `handle`, data requests from `(private)/+layout.server.ts`). No viewer exists before #145, so these pages are not reachable |
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
- **Headers:** every dynamic response is `Cache-Control: no-store`, with CSP (hashed scripts,
  `frame-ancestors 'none'`; inline style *attributes* only, because SvelteKit emits them), `nosniff`,
  `Referrer-Policy: same-origin`. Data preloading is disabled.

## Commands

Node `>=22.17` (`.nvmrc` pins 26.13.0, matching the dependency refresh).

```sh
npm ci
npm run check        # wrangler type drift + svelte-check + node-side tsc (clears .svelte-kit/cloudflare)
npm run test:unit    # vitest
npm run build        # Cloudflare Workers output in .svelte-kit/cloudflare
npm run preview      # wrangler dev (local workerd); pass --var API_ORIGIN:http://127.0.0.1:8144
E2E_API_ORIGIN=http://127.0.0.1:8144 npm run test:e2e   # build + Playwright against two workerd previews
```

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

The health check only runs `SELECT 1`; it needs no migrations or data.
