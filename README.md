# Load Organiser

A skydiver-first beta: public discovery of dropzones and dated opportunities, private personal
records (jumps, gear, history) and selected sharing. Scope, decisions and status live in the
[product documentation](docs/product/README.md); the beta boundaries are in
[architecture](docs/product/architecture.md), [data contracts](docs/product/data-contracts.md)
and the [API boundary](docs/product/api-boundary.md).

Nothing is deployed. Work proceeds issue by issue under the
[roadmap epic #134](https://github.com/metalcorpe/load-organiser/issues/134).

## Repository layout

| Path | What it is |
| --- | --- |
| `web/` | SvelteKit 3 / Svelte 5 beta app for Cloudflare Workers ([web/README.md](web/README.md)) |
| `backend/` | FastAPI + SQLModel + PostgreSQL. Beta code in `backend/app/skydiver/`, served under `/api/skydiver/v1` |
| `backend/app/api/`, `frontend/` | Legacy prototype (operations API, React client). Reference/rollback only; not mounted by default (#146) |
| `docs/product/` | Product, architecture and contract documents |
| `scripts/verify.sh` | Isolated verification used locally and by CI |
| `scripts/dev.sh` | Local development stack with data kept between runs (`.dev/`, git-ignored) |

## Verify a change

```sh
scripts/verify.sh            # backend, web and e2e against a throwaway PostgreSQL
scripts/verify.sh backend    # or: web, e2e
```

See [CONTRIBUTING.md](CONTRIBUTING.md) for prerequisites, the disposable-database rules and why
the repository `.env` is never read by tests.

## Run it locally

```sh
scripts/dev.sh start              # PostgreSQL, API and web on http://127.0.0.1:5180; Ctrl-C stops
scripts/dev.sh mail               # newest outgoing email (sign-up confirmation link)
scripts/dev.sh grant EMAIL        # reviewer role for your local account
scripts/dev.sh seed EMAIL         # load the dev listings as that reviewer
scripts/dev.sh reset              # delete all local data
```

Register at `/register`, confirm with the link from `scripts/dev.sh mail`, then `grant` and
`seed` (with `start` running in another terminal, or on their own). Needs PostgreSQL 17+
(`initdb` on PATH, or `PG_BIN`), `uv` and the web dependencies (`npm install` in `web/`).
The dev listings are researched candidate records for local testing only; they are never
loaded into production (`docs/product/inventory/README.md`).

## Origin and license

Started from the [Full Stack FastAPI Template](https://github.com/fastapi/full-stack-fastapi-template);
the legacy Docker Compose and template notes remain in [development.md](development.md) and
[deployment.md](deployment.md) for the reference stack. Licensed under the terms in [LICENSE](LICENSE).
