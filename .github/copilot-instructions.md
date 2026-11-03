# Instructions for AI coding assistants

The authoritative scope is the skydiver-first beta described in `docs/product/`: start with
`docs/product/README.md`, `architecture.md`, `data-contracts.md`, `api-boundary.md` and
`claude-code-handoff.md`. Earlier operations-first notes (loads, aircraft, instructors, admin
roles) describe the legacy prototype, which is reference-only and not mounted in the beta.

- Beta backend code lives in `backend/app/skydiver/` under `/api/skydiver/v1`; follow the access
  conventions in `backend/app/skydiver/access/` (owner from the session, owner predicate in SQL,
  404 for foreign records, server-granted roles only).
- The web app is `web/` (SvelteKit 3, server-only API transport). The browser never calls the API
  directly and never receives credentials.
- Never read or modify the repository `.env`. Verify with `scripts/verify.sh` (see
  `CONTRIBUTING.md`); do not run backend tests from `backend/`.
- Work on feature branches and report evidence; say "untested" when something was not run.
