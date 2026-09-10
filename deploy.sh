#!/usr/bin/env bash
#
# deploy.sh — push the working tree to the production server and bring it up.
#
#   ./deploy.sh
#
# Run from the repo root. Needs SSH access to the server as root.
#
# The one thing this exists for: nginx resolves the `django` hostname once, at
# startup, and caches the address. `docker compose up --build` gives django a
# new container with a new address, so nginx keeps proxying to the old one and
# every /api/ call answers 502 while the SPA's static files still load fine —
# a shop that looks up but sells nothing. Restarting nginx *after* django is
# actually serving is the fix, and doing it by hand is how it gets forgotten.
set -euo pipefail

HOST="${DEPLOY_HOST:-169.58.58.145}"
USER="${DEPLOY_USER:-root}"
REMOTE="${DEPLOY_PATH:-/opt/realbeauty}"

cd "$(dirname "$0")"

info() { printf "\033[1;36m[deploy]\033[0m %s\n" "$*"; }
die()  { printf "\033[1;31m[deploy]\033[0m %s\n" "$*"; exit 1; }

ssh_do() { ssh -o StrictHostKeyChecking=no "${USER}@${HOST}" "$@"; }

# --- 1. ship the code ---------------------------------------------------------
# No --delete: the server holds things the repo does not (.env, secrets, media).
info "Syncing working tree to ${HOST}:${REMOTE} …"
rsync -az \
  --exclude '.git' --exclude '.venv' --exclude 'node_modules' \
  --exclude 'frontend/dist' --exclude 'media' --exclude 'staticfiles' \
  --exclude '.env' --exclude 'secrets' --exclude 'celerybeat-schedule' \
  --exclude '__pycache__' \
  -e "ssh -o StrictHostKeyChecking=no" \
  ./ "${USER}@${HOST}:${REMOTE}/"

# --- 2. rebuild ---------------------------------------------------------------
# `migrate` runs as its own service and must exit 0 before anything serves.
info "Building and starting containers (this takes a few minutes) …"
ssh_do "cd ${REMOTE} && docker compose up -d --build"

# --- 3. wait for django to actually answer ------------------------------------
# Polled from inside the network, so this is django itself and not nginx's
# cached view of it.
info "Waiting for django to serve …"
for attempt in $(seq 1 30); do
  if ssh_do "cd ${REMOTE} && docker compose exec -T django python -c \
      'import urllib.request; urllib.request.urlopen(\"http://127.0.0.1:8000/api/v1/schema/\", timeout=3)'" \
      >/dev/null 2>&1; then
    info "django is up (after ${attempt} attempt(s))."
    break
  fi
  [ "$attempt" -eq 30 ] && die "django never came up — check 'docker compose logs django'."
  sleep 2
done

# --- 4. only now re-point nginx ----------------------------------------------
info "Restarting nginx so it re-resolves django …"
ssh_do "cd ${REMOTE} && docker compose restart nginx"

# --- 5. prove it from outside -------------------------------------------------
info "Verifying through the public URL …"
sleep 3
code=$(curl -sk -o /dev/null -w '%{http_code}' \
  "https://169-58-58-145.sslip.io/api/v1/webapp/catalog/?lang=uz" || echo 000)
[ "$code" = "200" ] || die "catalog API returned ${code}, not 200. Deploy is NOT healthy."

login=$(curl -sk -o /dev/null -w '%{http_code}' "https://169-58-58-145.sslip.io/login" || echo 000)
[ "$login" = "200" ] || die "admin panel returned ${login}, not 200."

info "✅ Deployed and healthy — catalog API and admin panel both answer 200."
