#!/usr/bin/env bash
#
# run_local.sh — boot the whole Real Beauty stack locally with one command.
#
#   ./run_local.sh
#
# Brings up Postgres + Redis (Docker if running, otherwise Homebrew services),
# installs deps, migrates, creates an admin user, then launches Django + the
# aiogram bot + Celery worker/beat. Ctrl-C stops everything.
#
set -euo pipefail

cd "$(dirname "$0")"

# --- Config (override via environment) ---------------------------------------
export DJANGO_SETTINGS_MODULE="${DJANGO_SETTINGS_MODULE:-core.settings.dev}"
export DJANGO_SECRET_KEY="${DJANGO_SECRET_KEY:-dev-insecure-secret}"
DJANGO_PORT="${DJANGO_PORT:-8000}"
DJANGO_SUPERUSER_USERNAME="${DJANGO_SUPERUSER_USERNAME:-admin}"
DJANGO_SUPERUSER_EMAIL="${DJANGO_SUPERUSER_EMAIL:-admin@example.com}"
DJANGO_SUPERUSER_PASSWORD="${DJANGO_SUPERUSER_PASSWORD:-admin}"
export DJANGO_SUPERUSER_USERNAME DJANGO_SUPERUSER_EMAIL DJANGO_SUPERUSER_PASSWORD

PY="./.venv/bin/python"
PIP="./.venv/bin/pip"

info() { printf "\033[1;36m[run]\033[0m %s\n" "$*"; }
warn() { printf "\033[1;33m[warn]\033[0m %s\n" "$*"; }
die()  { printf "\033[1;31m[error]\033[0m %s\n" "$*"; exit 1; }

# Homebrew Postgres client on PATH (Apple Silicon default keg).
export PATH="/opt/homebrew/opt/postgresql@14/bin:/opt/homebrew/bin:$PATH"

# --- 1. .env -----------------------------------------------------------------
if [[ ! -f .env ]]; then
  info "No .env — copying from .env.example. Edit BOT_TOKEN before real use."
  cp .env.example .env
fi
set -a; source .env; set +a
# .env carries docker-oriented values (prod settings, db/redis hostnames) for
# the container stack. For a LOCAL run, force dev settings + localhost so
# DEBUG=True (static finders serve unfold assets) and app procs reach services.
export DJANGO_SETTINGS_MODULE=core.settings.dev
export POSTGRES_HOST=localhost
export POSTGRES_PORT="${POSTGRES_PORT:-5432}"
export REDIS_URL="redis://localhost:6379/0"
PG_DB="${POSTGRES_DB:-realbeauty}"
PG_USER="${POSTGRES_USER:-realbeauty}"
PG_PASS="${POSTGRES_PASSWORD:-strongpassword}"

# --- 2. venv + deps ----------------------------------------------------------
if [[ ! -d .venv ]]; then
  info "Creating virtualenv (.venv)…"
  python3 -m venv .venv
fi
info "Installing requirements…"
$PIP install -q --upgrade pip
$PIP install -q -r requirements.txt

# --- 3. Postgres + Redis -----------------------------------------------------
USE_DOCKER=0
if command -v docker >/dev/null 2>&1 && docker info >/dev/null 2>&1; then
  USE_DOCKER=1
fi

if [[ "$USE_DOCKER" == "1" ]]; then
  info "Starting Postgres + Redis via Docker…"
  docker compose up -d db redis
elif command -v brew >/dev/null 2>&1; then
  info "Docker not available — using Homebrew services (postgresql@14 + redis)…"
  command -v redis-server >/dev/null 2>&1 || brew install redis
  brew services start postgresql@14 >/dev/null 2>&1 || true
  brew services start redis >/dev/null 2>&1 || true
else
  warn "No Docker and no Homebrew. Provide your own Postgres:5432 and Redis:6379."
fi

# --- wait for Postgres (hard fail if never comes up) -------------------------
info "Waiting for Postgres on localhost:${POSTGRES_PORT}…"
pg_up=0
for _ in $(seq 1 30); do
  if $PY - <<'PYEOF' 2>/dev/null
import os, socket, sys
s = socket.socket(); s.settimeout(1)
try: s.connect(("localhost", int(os.environ["POSTGRES_PORT"])))
except OSError: sys.exit(1)
PYEOF
  then pg_up=1; break; fi
  sleep 1
done
[[ "$pg_up" == "1" ]] || die "Postgres not reachable on localhost:${POSTGRES_PORT}. Start it and retry."

# --- provision role + database (native/brew path) ----------------------------
if [[ "$USE_DOCKER" != "1" ]] && command -v psql >/dev/null 2>&1; then
  info "Ensuring role '${PG_USER}' and database '${PG_DB}' exist…"
  psql -d postgres -tAc "SELECT 1 FROM pg_roles WHERE rolname='${PG_USER}'" | grep -q 1 \
    || psql -d postgres -c "CREATE ROLE ${PG_USER} LOGIN PASSWORD '${PG_PASS}';"
  psql -d postgres -tAc "SELECT 1 FROM pg_database WHERE datname='${PG_DB}'" | grep -q 1 \
    || createdb -O "${PG_USER}" "${PG_DB}"
  psql -d postgres -c "GRANT ALL PRIVILEGES ON DATABASE ${PG_DB} TO ${PG_USER};" >/dev/null
fi

# --- 4. migrate + superuser --------------------------------------------------
# A bot instance left over from a previous run holds Telegram's getUpdates
# lock — the new bot then gets TelegramConflictError and every button looks
# dead. Clear them before starting.
# Case-insensitive: macOS runs the venv python as ".../MacOS/Python" (capital
# P), which a lowercase pattern silently misses — leaving a zombie poller that
# gives every new bot TelegramConflictError.
if pgrep -if "python.*-m bot.main" >/dev/null 2>&1; then
  warn "Eski bot nusxalari topildi — o'chirilmoqda…"
  pkill -if "python.*-m bot.main" || true
  sleep 1
fi

info "Compiling admin translations…"
$PY scripts/compile_messages.py

info "Applying migrations…"
$PY manage.py migrate --noinput

info "Ensuring superuser '${DJANGO_SUPERUSER_USERNAME}' exists…"
$PY manage.py shell <<'PYEOF'
import os
from django.contrib.auth import get_user_model
User = get_user_model()
u = os.environ["DJANGO_SUPERUSER_USERNAME"]
if not User.objects.filter(username=u).exists():
    User.objects.create_superuser(
        u, os.environ["DJANGO_SUPERUSER_EMAIL"], os.environ["DJANGO_SUPERUSER_PASSWORD"]
    )
    print(f"created superuser {u}")
else:
    print(f"superuser {u} already exists")
PYEOF

# Optional demo data: SEED=1 ./run_local.sh
if [[ "${SEED:-0}" == "1" ]]; then
  info "Seeding demo data…"
  $PY manage.py seed_demo
fi

# --- 5. launch processes -----------------------------------------------------
PIDS=()
cleanup() {
  info "Shutting down app processes…"
  for pid in "${PIDS[@]}"; do kill "$pid" 2>/dev/null || true; done
  wait 2>/dev/null || true
  if [[ "$USE_DOCKER" == "1" ]]; then docker compose stop db redis >/dev/null 2>&1 || true; fi
  info "Done. (Homebrew Postgres/Redis left running — 'brew services stop postgresql@14 redis' to stop.)"
}
trap cleanup INT TERM EXIT

info "Starting Django on http://localhost:${DJANGO_PORT}/admin/ …"
$PY manage.py runserver "0.0.0.0:${DJANGO_PORT}" &
PIDS+=("$!")

info "Starting Celery worker + beat…"
./.venv/bin/celery -A tasks.celery worker -B -l info &
PIDS+=("$!")

if [[ -n "${BOT_TOKEN:-}" && "${BOT_TOKEN}" != "123456:ABC-your-token-here" ]]; then
  info "Starting Telegram bot…"
  $PY -m bot.main &
  PIDS+=("$!")
else
  warn "BOT_TOKEN is the placeholder — skipping bot. Set it in .env to enable."
fi

info "Stack up. Admin: http://localhost:${DJANGO_PORT}/admin/  (login: ${DJANGO_SUPERUSER_USERNAME}/${DJANGO_SUPERUSER_PASSWORD})"
info "Press Ctrl-C to stop."
wait
