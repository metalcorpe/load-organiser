# Dependency refresh

Registry and upstream release checks: 2026-11-02. This is an upgrade of the existing React/FastAPI prototype, separate from the planned SvelteKit product. The product owner explicitly authorized dependency implementation after the planning-only instruction. It does not implement the product roadmap or deploy a service.

## Selected versions and compatibility work

- Node container/runtime target: 26.13.0. Python: 3.15.2. Local tooling should use `frontend/.nvmrc` and `backend/.python-version`.
- Frontend: latest stable direct packages reported by npm, including React 19.3.1, Vite 8.3.5, Chakra 3.37.0, Zod 4.6.7, Playwright 1.64.1, Biome 2.6.4, and OpenAPI generator 0.99.0. TanStack plugin/devtools use their replacement package names.
- TypeScript exception: 6.0.3 is the newest compatible compiler-API release tested here. TypeScript 7.0.2 caused OpenAPI generation to fail when accessing `SyntaxKind.AnyKeyword`; do not update to 7 until the generator supports its API. No prerelease is selected to work around this.
- Python direct requirements and the uv lockfile are refreshed from PyPI. Development requirements use dependency groups. uv 0.13.6 is consistent across CI and the backend container.
- Passlib is replaced with pwdlib, using Argon2id for new hashes and bcrypt verification for existing hashes. Existing bcrypt verification preserves Passlib's 72-byte truncation behavior, including multibyte passwords. New Argon2id hashes do not truncate passwords at that boundary.
- SQLModel's new default timezone-aware column behavior is explicitly overridden for existing naive timestamp columns. This refresh does not reinterpret historical time zones or migrate timestamp data.
- The current generator emits an Axios client with structured body/path/query options. Call sites, bearer authentication, error handling, and test helpers use that API. Generated files are regenerated from the updated backend OpenAPI schema.
- TypeScript now includes `.tsx` files in checking. Router search types, an invalid relative settings link, and unused React imports are corrected. The empty analytics route remains an explicit unavailable placeholder.
- YAML transitive overrides select patched versions within the existing major lines (`js-yaml` 4.3.2 and `yaml` 1.10.3). Reassess these when upstream parsers update their dependency constraints.
- GitHub Actions and pre-commit hooks use checked upstream release tags. The previously disabled upstream project workflow is still disabled; changing its action version does not authorize enabling it.

## PostgreSQL 18 rollout boundary

Compose now selects PostgreSQL 18.6 and a **separate `app-db-data-pg18` volume**, mounted at `/var/lib/postgresql` with `PGDATA=/var/lib/postgresql/18/docker`. Existing PostgreSQL 17 storage is not reused or deleted. Existing deployments need an explicit migration; starting the new service alone does not transfer their data.

The `db` service also mounts the old `app-db-data` volume read-only at `/legacy-pg17`. If that volume holds a cluster (`PG_VERSION` exists) and the PostgreSQL 18 data directory is still empty, the container exits with a message instead of initialising an empty database. The healthcheck never passes, so `prestart` and `backend` do not start. Set `ALLOW_EMPTY_PG18=true` only to deliberately start empty, for example to restore a dump into the new volume. Once the PostgreSQL 18 cluster exists, the guard no longer applies. On fresh installs Compose creates `app-db-data` empty and the guard passes.

Before changing an existing deployment:

1. Identify the actual PostgreSQL 17 volume, databases, roles, extensions, encoding/collation, and application version. Preserve the old configuration and volume.
2. Rehearse a logical dump/restore into a separate PostgreSQL 18 instance. Capture database content and required roles/grants using the appropriate `pg_dump`/`pg_dumpall` tooling; keep backups outside ephemeral containers and verify that restoration succeeds. Do not treat a filesystem copy as a cross-major upgrade.
3. Check schema/Alembic state, row counts, ownership, extensions, login, account recovery, CRUD, timestamps, and application behavior against restored data. Local fresh-database tests do not validate a production migration.
4. For cutover, stop writes, take the final backup, restore it into the new volume, validate, and then switch application traffic. Keep the old volume and backups until the migration has been accepted.
5. If validation fails before accepting new writes, restore the old application/configuration and reconnect to the untouched PostgreSQL 17 instance. Once the new instance accepts writes, reverting to the old volume would lose those writes; plan reconciliation or restore from the authoritative new backup before rollback.

No production migration, existing-volume manipulation, public deployment, or CI secret changes are performed by this refresh.

## Verification and limitations

Validation completed locally:

- 59 backend tests passed on Python 3.15.2 and a disposable PostgreSQL 18.6 database.
- 41 configured Chromium browser tests passed, including login/logout, signup, password recovery/change, settings, and color-mode persistence.
- Frontend production build and TypeScript checking (including test helpers) passed.
- Frontend and backend container builds passed.
- Generated client reproduced without differences after regeneration and formatting; `uv lock --check` and whitespace checks passed.

The upgrade PR records these results and limitations. npm audit and pip-audit of the resolved lockfile packages reported no known vulnerabilities. Workflow syntax passed actionlint with the repository's existing self-hosted `production`/`staging` labels declared for the check. GitHub Actions is disabled at repository level; this refresh does not enable it, so no Actions execution is claimed. Tests use a disposable PostgreSQL 18 instance and explicit test settings; the user's local `.env` and existing databases are not used. Fresh-database Alembic migrations pass. Authentication/hash and datetime compatibility checks supplement the existing backend tests.

Full backend static analysis remains incomplete: the updated source has existing missing CRUD functions, endpoint/CRUD argument mismatches, and other prototype typing defects. Comparing original and updated source under the same upgraded mypy/dependency environment found no new diagnostic categories; that is not proof of full behavioral equivalence. These operational defects must still be resolved or isolated before release, as tracked in #146 and #166.

React emits a development warning about client-rendered script tags; color-mode switching and persistence are included in the browser checks. The production bundle also retains a large-chunk warning.

Browser checks cover only configured Chromium journeys. Container builds and a fresh database do not establish production readiness, cross-browser compatibility, or a validated PostgreSQL 17-to-18 data migration. Provider free-tier or production hosting behavior is not tested here.

## Sources

- [npm registry](https://registry.npmjs.org/) and [PyPI JSON API](https://docs.pypi.org/api/json/) for package versions.
- [Node release index](https://nodejs.org/dist/index.json) and official Docker image tags for runtime versions.
- [SQLModel release notes](https://sqlmodel.tiangolo.com/release-notes/) for datetime compatibility changes.
- [FastAPI password hashing guidance](https://fastapi.tiangolo.com/tutorial/security/oauth2-jwt/) for pwdlib and legacy hash support.
- [Vite migration guidance](https://vite.dev/guide/migration) and upstream GitHub release APIs for tool/action versions.
