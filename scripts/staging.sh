#!/usr/bin/env bash
# Operator commands against the hosted staging database (#161). Run from your own
# terminal; nothing here runs in CI or on the hosts.
#
#   export DATABASE_URL='postgresql://...'   # Neon, the DIRECT (not -pooler) string
#   scripts/staging.sh status                # current and latest migration
#   scripts/staging.sh migrate               # apply migrations (before deploying code that needs them)
#   scripts/staging.sh create-account EMAIL  # your confirmed account; asks for the password
#   scripts/staging.sh grant-reviewer EMAIL  # the maintainer role
#   scripts/staging.sh load-dropzones EMAIL [STATUSES]
#                                            # the researched dropzones as drafts; with
#                                            # STATUSES (e.g. active,seasonal) those go public
#
# The connection string is read from this shell only and never written anywhere.
# Commands run from an empty temporary directory with a cleared environment, so the
# backend settings never pick up a local .env. See docs/product/deploy-runbook.md.
set -euo pipefail

: "${DATABASE_URL:?export DATABASE_URL (the Neon direct connection string) in this shell first}"
case "$DATABASE_URL" in
  *-pooler.*) echo "Use Neon's direct connection string (without -pooler) for operator commands." >&2; exit 2 ;;
esac

B=$(cd "$(dirname "$0")/../backend" && pwd)
EMPTY=$(mktemp -d)
trap 'rm -rf "$EMPTY"' EXIT

run() {
  # Operator commands never serve requests, so the proxy key only satisfies the
  # settings check outside local; it is not the deployed secret.
  (cd "$EMPTY" && env -i PATH="$PATH" HOME="$HOME" ${TERM:+TERM="$TERM"} \
    DATABASE_URL="$DATABASE_URL" ENVIRONMENT=staging PROJECT_NAME=load-organiser \
    SKYDIVER_WEB_PROXY_KEY=operator-commands-only-not-the-deployed-key \
    PYTHONPATH="$B" uv run --quiet --project "$B" "$@")
}

alembic() {
  sed "s#^script_location = .*#script_location = $B/app/alembic#" "$B/alembic.ini" >"$EMPTY/alembic.ini"
  run alembic -c "$EMPTY/alembic.ini" "$@"
}

case "${1:-}" in
  status)
    echo "current:"; alembic current
    echo "latest:"; alembic heads
    ;;
  migrate) alembic upgrade head ;;
  create-account)
    [ -n "${2:-}" ] || { echo "usage: $0 create-account EMAIL" >&2; exit 2; }
    run python -m app.skydiver.identity.operator create-confirmed "$2"
    ;;
  grant-reviewer)
    [ -n "${2:-}" ] || { echo "usage: $0 grant-reviewer EMAIL" >&2; exit 2; }
    run python -m app.skydiver.access.grant reviewer "$2"
    ;;
  load-dropzones)
    [ -n "${2:-}" ] || { echo "usage: $0 load-dropzones EMAIL [STATUSES]" >&2; exit 2; }
    run python -m app.skydiver.devdata dropzones \
      "$(cd "$B/.." && pwd)/docs/product/inventory/dropzones" --reviewer "$2" \
      ${3:+--publish "$3"}
    ;;
  *)
    sed -n '2,13p' "$0" >&2
    exit 2
    ;;
esac
