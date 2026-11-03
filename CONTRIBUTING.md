# Contributing

## Workflow

- Work on a feature branch; never commit to `main` directly. Open a pull request that references
  its issue (`Refs #N`) and record the evidence (commands run, results, what stayed untested).
- New issues use the **Task** or **Bug** template. Labels follow `type:*`, `scope:*`, `phase:*`
  and `area:*`.
- Project board: add issues and pull requests manually. The inherited "Add to Project" workflow
  targeted the upstream FastAPI organisation and was removed; no project token is configured.
- Report security problems privately via
  [GitHub vulnerability reporting](https://github.com/metalcorpe/load-organiser/security/advisories/new).

## Prerequisites

Python 3.15 with [uv](https://docs.astral.sh/uv/) 0.13.6, Node `>=22.17` (`web/.nvmrc` pins 26.13.0),
PostgreSQL 17+ (`initdb` on `PATH`, or `PG_BIN=/path/to/bin`), `openssl` and `curl`. For e2e, a
Playwright Chromium: `cd web && npx playwright install chromium`.

## Verification

```sh
scripts/verify.sh                 # all stages
scripts/verify.sh backend web     # any subset of: backend web e2e
```

| Stage | Runs |
| --- | --- |
| `backend` | Alembic migrations on a fresh `verify_backend` database, all backend tests, ruff and mypy on the beta modules |
| `web` | `npm run check` (types), unit tests, Cloudflare Workers build |
| `e2e` | Fresh `verify_e2e` database, isolated API, Playwright against three local workerd previews (one HTTPS); fails on any API 5xx |

Isolation rules the script enforces:

- **The repository `.env` is never read.** Backend settings load `../.env` relative to the working
  directory, so backend commands run from an empty temporary directory with a cleared environment
  and generated throwaway secrets. Do not run backend tests from `backend/`.
- **Disposable data only.** Without configuration the script creates a throwaway PostgreSQL cluster
  and deletes it afterwards. To use an existing server, set `VERIFY_PG_HOST`, `VERIFY_PG_PORT`,
  `VERIFY_PG_USER`, `VERIFY_PG_PASSWORD` and `VERIFY_PG_DISPOSABLE=yes`; only the databases
  `verify_backend` and `verify_e2e` are dropped and recreated. The legacy test fixtures delete all
  users, so never point verification at a database you care about.
- E2E uses a fresh database each run because throttle windows persist. Mail goes to a local file
  outbox, which is not evidence of real delivery.

Lint and type gates cover the beta modules only. The legacy prototype has known lint/type debt
(ruff and mypy report existing errors) and is not mounted in the beta (#146).

## Generated code

- Web API types: `cd backend && uv run python -m app.skydiver.openapi > ../web/contracts/skydiver-v1.openapi.json`,
  then `cd web && npm run contracts:generate`. A backend test fails when the committed contract drifts.
- `scripts/generate-client.sh` regenerates the legacy React client only.

## Continuous integration

`.github/workflows/ci.yml` runs the same three stages on GitHub-hosted runners with a PostgreSQL
service container and no secrets. **GitHub Actions is disabled for this repository**, so the
workflow does not run until the owner enables Actions; it has not been executed on GitHub.
Enabling Actions is an owner decision, not part of a code change. Dependabot updates are
configured for `web/`, `backend/` and the workflows.

The template's deployment, release-notes, coverage-upload, labeler, issue-manager and
client-autocommit workflows were removed: they targeted the upstream repository, needed secrets
this repository does not have, or deployed the legacy stack. Hosting is evaluated in #161.
