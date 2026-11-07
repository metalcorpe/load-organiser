#!/usr/bin/env bash
# Isolated verification for the skydiver beta (#147): backend, web, e2e.
#
#   scripts/verify.sh [backend] [web] [e2e] [recovery]   (default: all four)
#
# Never reads the repository .env: backend commands run from an empty temporary
# directory with a cleared environment and generated throwaway secrets.
#
# PostgreSQL (17+), one of:
#   - nothing set: a throwaway cluster is created with `initdb` (on PATH, or PG_BIN)
#     and removed afterwards;
#   - VERIFY_PG_HOST/PORT/USER/PASSWORD for an existing *disposable* server, plus
#     VERIFY_PG_DISPOSABLE=yes. The databases verify_backend, verify_e2e,
#     verify_recovery, verify_restored and verify_fresh on it are dropped and
#     recreated; no other database is touched.
#
# CI=true runs `npm ci` before the web stages. Playwright browsers must be installed
# (`npx playwright install chromium webkit`). Nothing here deploys or contacts paid services.
set -euo pipefail

ROOT=$(cd "$(dirname "$0")/.." && pwd)
B="$ROOT/backend"
W="$ROOT/web"
STAGES="${*:-backend web e2e recovery}"
for stage in $STAGES; do
  case "$stage" in backend | web | e2e | recovery) ;; *) echo "unknown stage: $stage" >&2; exit 2 ;; esac
done

SCRATCH=$(mktemp -d "${TMPDIR:-/tmp}/organiser-verify.XXXXXX")
API_PID=""
PG_CLUSTER=""
cleanup() {
  [ -n "$API_PID" ] && kill "$API_PID" 2>/dev/null || true
  [ -n "$PG_CLUSTER" ] && "$PG_BIN_DIR/pg_ctl" -D "$PG_CLUSTER" stop -m fast >/dev/null 2>&1 || true
  rm -rf "$SCRATCH"
}
trap cleanup EXIT
mkdir -p "$SCRATCH/empty"
secret() { openssl rand -hex "${1:-32}"; }
log() { printf '\n== %s\n' "$*"; }

needs_db=no
case " $STAGES " in *" backend "* | *" e2e "* | *" recovery "*) needs_db=yes ;; esac

# ---------------------------------------------------------------- PostgreSQL
if [ "$needs_db" = yes ]; then
  if [ -n "${VERIFY_PG_HOST:-}" ]; then
    if [ "${VERIFY_PG_DISPOSABLE:-}" != yes ]; then
      echo "Set VERIFY_PG_DISPOSABLE=yes to confirm $VERIFY_PG_HOST is disposable." >&2
      exit 2
    fi
    PG_HOST=$VERIFY_PG_HOST PG_PORT=${VERIFY_PG_PORT:-5432}
    PG_USER=${VERIFY_PG_USER:-postgres} PG_PASSWORD=${VERIFY_PG_PASSWORD:-}
  else
    PG_BIN_DIR=${PG_BIN:-$(dirname "$(command -v initdb || echo /missing/initdb)")}
    if [ ! -x "$PG_BIN_DIR/initdb" ]; then
      echo "No VERIFY_PG_HOST and no initdb found (set PG_BIN)." >&2
      exit 2
    fi
    PG_CLUSTER="$SCRATCH/pg"
    PG_HOST=127.0.0.1 PG_PORT=${VERIFY_PG_PORT:-55432} PG_USER=verify
    PG_PASSWORD=$(secret 16)
    printf '%s\n' "$PG_PASSWORD" >"$SCRATCH/pgpass"
    "$PG_BIN_DIR/initdb" -D "$PG_CLUSTER" -U "$PG_USER" --pwfile="$SCRATCH/pgpass" \
      --auth=scram-sha-256 -E UTF8 >/dev/null
    "$PG_BIN_DIR/pg_ctl" -D "$PG_CLUSTER" -l "$SCRATCH/pg.log" \
      -o "-p $PG_PORT -c listen_addresses=127.0.0.1 -c unix_socket_directories=" start >/dev/null
  fi
fi

# Environment file for one database; secrets are generated per run.
backend_env() {
  local db=$1 file="$SCRATCH/env-$1.sh"
  {
    echo "export ENVIRONMENT=local PROJECT_NAME=verify"
    echo "export SECRET_KEY=$(secret 32)"
    echo "export POSTGRES_SERVER=$PG_HOST POSTGRES_PORT=$PG_PORT POSTGRES_USER=$PG_USER"
    echo "export POSTGRES_PASSWORD='$PG_PASSWORD' POSTGRES_DB=$db"
    echo "export FIRST_SUPERUSER=admin@example.com FIRST_SUPERUSER_PASSWORD=$(secret 16)"
  } >"$file"
  echo "$file"
}

# Run a backend command from the empty directory with only the given env file.
in_backend() {
  local env_file=$1
  shift
  (cd "$SCRATCH/empty" && env -i PATH="$PATH" HOME="$HOME" ${CI:+CI=$CI} \
    bash -c ". '$env_file'; $*")
}

# An empty database (no schema), dropped first if it exists.
empty_db() {
  local env_file=$1 db=$2
  in_backend "$env_file" "uv run --project '$B' python -c \"
import os, psycopg
with psycopg.connect(host=os.environ['POSTGRES_SERVER'], port=os.environ['POSTGRES_PORT'],
        user=os.environ['POSTGRES_USER'], password=os.environ['POSTGRES_PASSWORD'],
        dbname='postgres', autocommit=True) as c:
    c.execute('DROP DATABASE IF EXISTS $db WITH (FORCE)')
    c.execute('CREATE DATABASE $db')
\""
}

alembic_cmd() {
  local env_file=$1
  shift
  sed "s#^script_location = .*#script_location = $B/app/alembic#" "$B/alembic.ini" >"$SCRATCH/alembic.ini"
  in_backend "$env_file" "PYTHONPATH='$B' uv run --project '$B' alembic -c '$SCRATCH/alembic.ini' $*"
}

recreate_db() {
  local env_file=$1 db=$2
  empty_db "$env_file" "$db"
  alembic_cmd "$env_file" upgrade head
  in_backend "$env_file" "PYTHONPATH='$B' uv run --project '$B' python -m app.initial_data"
}

# Lint/type gates cover the beta modules plus the legacy modules the beta imports
# (app/models.py for User; app/core for settings and the engine). The rest of the
# legacy backend is unmounted in the beta and not gated (decision 2026-11-03;
# fixing it belongs to #166).
BETA_PY="app/skydiver app/tests/skydiver tests/test_skydiver_health.py tests/test_skydiver_directory_policy.py \
tests/test_skydiver_identity_policy.py tests/test_skydiver_access_policy.py tests/test_skydiver_opportunity_policy.py \
tests/test_skydiver_gear_policy.py tests/test_skydiver_logbook_policy.py tests/test_skydiver_history_policy.py tests/test_skydiver_records_policy.py tests/test_skydiver_social_policy.py tests/test_skydiver_posts_policy.py \
app/main.py \
app/models.py app/core"

# --------------------------------------------------------------------- stages
stage_backend() {
  log "backend: migrate disposable database verify_backend"
  local env_file
  env_file=$(backend_env verify_backend)
  recreate_db "$env_file" verify_backend
  log "backend: tests"
  in_backend "$env_file" "uv run --project '$B' pytest '$B/tests' '$B/app/tests' -q -p no:cacheprovider --rootdir '$B'"
  log "backend: lint and types (beta modules)"
  (cd "$B" && env -i PATH="$PATH" HOME="$HOME" bash -c \
    "uv run ruff check $BETA_PY && uv run ruff format --check $BETA_PY && uv run mypy $BETA_PY")
}

stage_web() {
  log "web: install, check, unit tests, build"
  (cd "$W" && { [ -z "${CI:-}" ] || npm ci; } && npm run check && npm run test:unit && npm run build)
}

stage_e2e() {
  log "e2e: fresh database verify_e2e and isolated API"
  local env_file outbox proxy_key api_port=${VERIFY_API_PORT:-8144}
  env_file=$(backend_env verify_e2e)
  outbox="$SCRATCH/outbox"
  proxy_key=$(secret 24)
  mkdir -p "$outbox"
  cat >>"$env_file" <<EOF
export SKYDIVER_REGISTRATION_OPEN=true SKYDIVER_SUBMISSIONS_OPEN=true SKYDIVER_MAX_ACCOUNTS=1000
export SKYDIVER_WEB_ORIGIN=https://127.0.0.1:4175 SKYDIVER_WEB_PROXY_KEY=$proxy_key
export SKYDIVER_MAIL_OUTBOX_DIR=$outbox
EOF
  recreate_db "$env_file" verify_e2e
  (cd "$SCRATCH/empty" && exec env -i PATH="$PATH" HOME="$HOME" bash -c \
    ". '$env_file'; exec uv run --project '$B' uvicorn app.main:app --host 127.0.0.1 --port $api_port --app-dir '$B'") \
    >"$SCRATCH/api.log" 2>&1 &
  API_PID=$!
  for _ in $(seq 1 60); do
    curl -sf "http://127.0.0.1:$api_port/api/skydiver/v1/health" >/dev/null && break
    sleep 0.5
  done
  curl -sf "http://127.0.0.1:$api_port/api/skydiver/v1/health" >/dev/null || {
    tail -20 "$SCRATCH/api.log" >&2
    exit 1
  }
  log "e2e: reviewer account (registered through the API, role granted by the operator command)"
  local reviewer_email reviewer_password
  reviewer_email="reviewer-$(secret 6)@example.com"
  reviewer_password=$(secret 16)
  curl -sf -o /dev/null -X POST "http://127.0.0.1:$api_port/api/skydiver/v1/auth/registrations" \
    -H 'content-type: application/json' -H "x-organiser-proxy-key: $proxy_key" \
    -H 'x-organiser-client-ip: 10.99.0.1' \
    -d "{\"email\":\"$reviewer_email\",\"password\":\"$reviewer_password\"}"
  in_backend "$env_file" "PYTHONPATH='$B' uv run --project '$B' python -m app.skydiver.access.grant reviewer '$reviewer_email'"

  log "e2e: Playwright against workerd previews"
  (cd "$W" && { [ -z "${CI:-}" ] || [ -d node_modules ] || npm ci; } &&
    E2E_API_ORIGIN="http://127.0.0.1:$api_port" E2E_MAIL_OUTBOX="$outbox" \
      E2E_API_PROXY_KEY="$proxy_key" E2E_REVIEWER_EMAIL="$reviewer_email" \
      E2E_REVIEWER_PASSWORD="$reviewer_password" npm run test:e2e)
  if grep -q 'HTTP/1.1" 5' "$SCRATCH/api.log"; then
    echo "API answered 5xx during e2e:" >&2
    grep 'HTTP/1.1" 5' "$SCRATCH/api.log" >&2
    exit 1
  fi
}

# Local recovery drill (#161): backup/restore with pg_dump/pg_restore and a full
# migration round trip, on disposable databases. Production backup destination,
# schedule, encryption and key custody are not exercised here.
stage_recovery() {
  local src dst fresh tools pg manifest
  tools=${PG_BIN_DIR:-$(dirname "$(command -v pg_dump || echo /missing/pg_dump)")}
  [ -x "$tools/pg_dump" ] || { echo "pg_dump not found (set PG_BIN)" >&2; exit 2; }
  pg="-h $PG_HOST -p $PG_PORT -U $PG_USER"
  src=$(backend_env verify_recovery)
  # One configuration for every database of the drill, as a real restore would use.
  dst="$SCRATCH/env-verify_restored.sh" fresh="$SCRATCH/env-verify_fresh.sh"
  sed 's/POSTGRES_DB=verify_recovery/POSTGRES_DB=verify_restored/' "$src" >"$dst"
  sed 's/POSTGRES_DB=verify_recovery/POSTGRES_DB=verify_fresh/' "$src" >"$fresh"
  manifest="$SCRATCH/recovery.json"
  local drill="PYTHONPATH='$B' uv run --project '$B' python -m app.tests.skydiver.recovery"

  log "recovery: seed verify_recovery through the API"
  recreate_db "$src" verify_recovery
  in_backend "$src" "$drill seed '$manifest'"
  in_backend "$src" "$drill snapshot" >"$SCRATCH/before.json"

  log "recovery: pg_dump (custom format), restore into an empty database"
  PGPASSWORD=$PG_PASSWORD "$tools/pg_dump" $pg -Fc -f "$SCRATCH/backup.dump" verify_recovery
  empty_db "$dst" verify_restored
  PGPASSWORD=$PG_PASSWORD "$tools/pg_restore" $pg --exit-on-error --no-owner \
    -d verify_restored "$SCRATCH/backup.dump"
  in_backend "$dst" "$drill snapshot" >"$SCRATCH/after.json"
  diff -u "$SCRATCH/before.json" "$SCRATCH/after.json" || {
    echo "restored data differs from the backup source" >&2
    exit 1
  }
  in_backend "$dst" "$drill seeded '$SCRATCH/after.json'"
  # The restored schema itself equals the source schema (before any round trip).
  # Restore re-parses CHECK constraints and PostgreSQL deparses varchar IN-lists with
  # an equivalent but differently cast ARRAY; on CHECK lines only, casts and
  # parentheses are dropped before comparing. Every other line must match exactly.
  local db
  for db in verify_recovery verify_restored; do
    PGPASSWORD=$PG_PASSWORD "$tools/pg_dump" $pg --schema-only --no-owner --no-privileges "$db" |
      grep -v '^\\\(un\)\?restrict ' |
      sed -e '/ CHECK /s/::character varying//g' -e '/ CHECK /s/::text\[\]//g' \
        -e '/ CHECK /s/::text//g' -e '/ CHECK /s/[()]//g' >"$SCRATCH/restored-$db.sql"
  done
  diff -u "$SCRATCH/restored-verify_recovery.sql" "$SCRATCH/restored-verify_restored.sql" || {
    echo "restored schema differs from the backup source" >&2
    exit 1
  }
  log "recovery: the restored database behaves like the source at backup time"
  in_backend "$dst" "$drill check '$manifest'"

  # c6459ca8ce2a is the last legacy migration; every beta migration after it is
  # downgraded here with the restored data present. Legacy downgrades below it are
  # not supported (the template's unnamed foreign keys; legacy is #166).
  log "recovery: downgrade every beta migration of the restored database, upgrade, compare schema"
  alembic_cmd "$dst" downgrade c6459ca8ce2a
  alembic_cmd "$dst" upgrade head
  recreate_db "$fresh" verify_fresh
  for db in verify_restored verify_fresh; do
    # \restrict lines carry a random key per dump; everything else must match.
    PGPASSWORD=$PG_PASSWORD "$tools/pg_dump" $pg --schema-only --no-owner --no-privileges "$db" |
      grep -v '^\\\(un\)\?restrict ' >"$SCRATCH/schema-$db.sql"
  done
  diff -u "$SCRATCH/schema-verify_fresh.sql" "$SCRATCH/schema-verify_restored.sql" || {
    echo "schema after downgrade/upgrade differs from a fresh migration" >&2
    exit 1
  }
}

for stage in $STAGES; do "stage_$stage"; done
log "verify: passed ($STAGES)"
