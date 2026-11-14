#!/usr/bin/env bash
# Local development stack for the skydiver beta, with data kept between runs.
#
#   scripts/dev.sh start          PostgreSQL + API + web preview; Ctrl-C stops them
#   scripts/dev.sh grant EMAIL    give an account the reviewer role
#   scripts/dev.sh seed EMAIL     load docs/product/inventory/dev-listings.json and the
#                                 dropzones/*.json beside it as EMAIL (DEV_DROPZONES=DIR: another folder)
#   scripts/dev.sh mail           print the newest outgoing email (confirmation links)
#   scripts/dev.sh reset          delete all local dev data
#
# Everything lives in .dev/ (git-ignored): the database cluster, generated secrets,
# the mail outbox and logs. Like verify.sh it never reads the repository .env and
# runs backend commands from an empty directory with a cleared environment.
# ENVIRONMENT=local, so the dev listings loader is allowed here and nowhere else.
# Web: http://127.0.0.1:5180   API: http://127.0.0.1:8150
set -euo pipefail
SWITCHES='export SKYDIVER_REGISTRATION_OPEN=true SKYDIVER_SUBMISSIONS_OPEN=true SKYDIVER_PUBLISHING_OPEN=true SKYDIVER_MAX_ACCOUNTS=20'

ROOT=$(cd "$(dirname "$0")/.." && pwd)
B="$ROOT/backend"
W="$ROOT/web"
DEV="$ROOT/.dev"
PG_BIN_DIR=${PG_BIN:-$(dirname "$(command -v initdb || echo /missing/initdb)")}
PG_PORT=${DEV_PG_PORT:-55433}
API_PORT=${DEV_API_PORT:-8150}
WEB_PORT=${DEV_WEB_PORT:-5180}
WEB_ORIGIN="http://127.0.0.1:$WEB_PORT"

secret() { openssl rand -hex "${1:-32}"; }
log() { printf '\n== %s\n' "$*"; }

setup() {
  [ -x "$PG_BIN_DIR/initdb" ] || { echo "initdb not found (set PG_BIN)" >&2; exit 2; }
  mkdir -p "$DEV/empty" "$DEV/outbox"
  if [ ! -f "$DEV/env.sh" ]; then
    local pg_password
    pg_password=$(secret 16)
    printf '%s\n' "$pg_password" >"$DEV/pgpass"
    "$PG_BIN_DIR/initdb" -D "$DEV/pg" -U dev --pwfile="$DEV/pgpass" \
      --auth=scram-sha-256 -E UTF8 >/dev/null
    rm "$DEV/pgpass"
    cat >"$DEV/env.sh" <<EOF
export ENVIRONMENT=local PROJECT_NAME=dev SECRET_KEY=$(secret 32)
export POSTGRES_SERVER=127.0.0.1 POSTGRES_PORT=$PG_PORT POSTGRES_USER=dev
export POSTGRES_PASSWORD='$pg_password' POSTGRES_DB=dev
export FIRST_SUPERUSER=admin@example.com FIRST_SUPERUSER_PASSWORD=$(secret 16)
export SKYDIVER_WEB_ORIGIN=$WEB_ORIGIN SKYDIVER_WEB_PROXY_KEY=$(secret 24)
export SKYDIVER_MAIL_OUTBOX_DIR='$DEV/outbox'
EOF
    log "created .dev (database cluster and secrets)"
  fi
  if ! "$PG_BIN_DIR/pg_ctl" -D "$DEV/pg" status >/dev/null 2>&1; then
    "$PG_BIN_DIR/pg_ctl" -D "$DEV/pg" -l "$DEV/pg.log" \
      -o "-p $PG_PORT -c listen_addresses=127.0.0.1 -c unix_socket_directories=" start >/dev/null
  fi
  in_backend "uv run --project '$B' python -c \"
import os, psycopg
with psycopg.connect(host='127.0.0.1', port=os.environ['POSTGRES_PORT'], user='dev',
        password=os.environ['POSTGRES_PASSWORD'], dbname='postgres', autocommit=True) as c:
    if not c.execute(\\\"SELECT 1 FROM pg_database WHERE datname = 'dev'\\\").fetchone():
        c.execute('CREATE DATABASE dev')
\""
  sed "s#^script_location = .*#script_location = $B/app/alembic#" "$B/alembic.ini" >"$DEV/alembic.ini"
  in_backend "PYTHONPATH='$B' uv run --project '$B' alembic -c '$DEV/alembic.ini' upgrade head" >/dev/null 2>&1
  in_backend "PYTHONPATH='$B' uv run --project '$B' python -m app.initial_data" >/dev/null 2>&1
}

in_backend() {
  # The switches are set on every run, not stored in env.sh (created once), so a new
  # switch reaches an existing .dev without recreating it.
  (cd "$DEV/empty" && env -i PATH="$PATH" HOME="$HOME" bash -c ". '$DEV/env.sh'; $SWITCHES; $*")
}

start() {
  setup
  local api_pid="" web_pid=""
  trap '[ -n "$api_pid" ] && kill "$api_pid" 2>/dev/null; [ -n "$web_pid" ] && kill "$web_pid" 2>/dev/null; "$PG_BIN_DIR/pg_ctl" -D "$DEV/pg" stop -m fast >/dev/null 2>&1; exit 0' INT TERM
  log "API on 127.0.0.1:$API_PORT (log: .dev/api.log)"
  in_backend "exec uv run --project '$B' uvicorn app.main:app --host 127.0.0.1 --port $API_PORT --app-dir '$B'" \
    >"$DEV/api.log" 2>&1 &
  api_pid=$!
  log "web: build"
  (cd "$W" && npm run -s build >/dev/null)
  local proxy_key
  proxy_key=$(. "$DEV/env.sh" && echo "$SKYDIVER_WEB_PROXY_KEY")
  log "web on $WEB_ORIGIN (log: .dev/web.log). Ctrl-C stops everything."
  (cd "$W" && WRANGLER_SEND_METRICS=false exec npx wrangler dev .svelte-kit/cloudflare/_worker.js \
    --port "$WEB_PORT" --ip 127.0.0.1 --persist-to "$DEV/wrangler" \
    --var "API_ORIGIN:http://127.0.0.1:$API_PORT" --var "APP_ORIGIN:$WEB_ORIGIN" \
    --var SESSION_COOKIE_MODE:localhost-dev --var "API_PROXY_KEY:$proxy_key") >"$DEV/web.log" 2>&1 &
  web_pid=$!
  wait
}

case "${1:-}" in
  start) start ;;
  grant)
    [ -n "${2:-}" ] || { echo "usage: scripts/dev.sh grant EMAIL" >&2; exit 2; }
    setup
    in_backend "PYTHONPATH='$B' uv run --project '$B' python -m app.skydiver.access.grant reviewer '$2'"
    ;;
  seed)
    [ -n "${2:-}" ] || { echo "usage: scripts/dev.sh seed EMAIL" >&2; exit 2; }
    setup
    in_backend "PYTHONPATH='$B' uv run --project '$B' python -m app.skydiver.devdata load \
      '$ROOT/docs/product/inventory/dev-listings.json' --reviewer '$2' \
      ${DEV_DROPZONES:+--dropzones '$DEV_DROPZONES'}"
    ;;
  mail)
    newest=$(ls -t "$DEV/outbox" 2>/dev/null | head -1)
    [ -n "$newest" ] && cat "$DEV/outbox/$newest" || echo "no mail yet"
    ;;
  reset)
    [ -d "$DEV/pg" ] && "$PG_BIN_DIR/pg_ctl" -D "$DEV/pg" stop -m fast >/dev/null 2>&1 || true
    rm -rf "$DEV"
    echo "removed .dev"
    ;;
  *) sed -n '2,14p' "$0"; exit 2 ;;
esac
