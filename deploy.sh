#!/usr/bin/env bash
#
# deploy.sh — push the working tree to the production server and bring it up.
#
#   ./deploy.sh                      # host taken from .env / DEPLOY_HOST
#   DEPLOY_HOST=1.2.3.4 ./deploy.sh  # or passed in for a one-off
#
# Run from the repo root. Needs SSH access to the server as root.
#
# Two things this exists for:
#
# 1. nginx resolves the `django` hostname once, at startup, and caches the
#    address. `docker compose up --build` gives django a new container with a
#    new address, so nginx keeps proxying to the old one and every /api/ call
#    answers 502 while the SPA's static files still load fine — a shop that
#    looks up but sells nothing. Restarting nginx *after* django is actually
#    serving is the fix, and doing it by hand is how it gets forgotten.
#
# 2. The server's own .env is never shipped (it holds secrets this repo must
#    not carry), so it is the one file that can silently disagree with the box
#    it lives on. The preflight below reads it over ssh and refuses to deploy
#    when PUBLIC_HOST is missing or when WEBAPP_URL still points at a previous
#    server — that combination leaves the «Mahsulotlar» button opening a dead
#    address, which is indistinguishable from the shop being broken.
set -euo pipefail

cd "$(dirname "$0")"

# A local .env is optional here — it only supplies defaults for where to ssh.
if [[ -f .env ]]; then
  set -a; source .env; set +a
fi

HOST="${DEPLOY_HOST:-${PUBLIC_HOST:-}}"
USER="${DEPLOY_USER:-root}"
REMOTE="${DEPLOY_PATH:-/opt/realbeauty}"

info() { printf "\033[1;36m[deploy]\033[0m %s\n" "$*"; }
warn() { printf "\033[1;33m[deploy]\033[0m %s\n" "$*"; }
die()  { printf "\033[1;31m[deploy]\033[0m %s\n" "$*"; exit 1; }

[[ -n "$HOST" ]] || die "Server manzili yo'q. DEPLOY_HOST bering yoki .env ga PUBLIC_HOST yozing:
    DEPLOY_HOST=1.2.3.4 ./deploy.sh"

SSH_OPTS=(-o StrictHostKeyChecking=no -o ServerAliveInterval=15 -o ServerAliveCountMax=8 -o ConnectTimeout=20)
SSH_CMD="ssh ${SSH_OPTS[*]}"

ssh_do() { ssh "${SSH_OPTS[@]}" "${USER}@${HOST}" "$@"; }

# --- 0. preflight: the remote .env has to describe the remote box ------------
info "Checking ${HOST}:${REMOTE}/.env …"
ssh_do "test -f ${REMOTE}/.env" \
  || die "${REMOTE}/.env serverda yo'q. Avval .env.example dan nusxa olib to'ldiring:
    scp .env.example ${USER}@${HOST}:${REMOTE}/.env  &&  ssh ${USER}@${HOST} nano ${REMOTE}/.env"

# Reads one key out of the server's .env. Quote-stripping happens locally so
# the remote command stays a single, quote-free sed.
remote_env() {
  local val
  val="$(ssh_do "sed -n 's/^$1=//p' ${REMOTE}/.env | tail -1" 2>/dev/null || true)"
  val="${val//[$'\r\n\t ']/}"
  val="${val//\"/}"
  val="${val//\'/}"
  printf '%s' "$val"
}

PUBLIC="$(remote_env PUBLIC_HOST)"
WEBAPP="$(remote_env WEBAPP_URL)"

[[ -n "$PUBLIC" ]] || die "Serverdagi .env da PUBLIC_HOST bo'sh.
Domen bo'lmasa sslip.io ishlating — masalan IP 1.2.3.4 uchun:
    PUBLIC_HOST=1-2-3-4.sslip.io"

# WEBAPP_URL is optional: Django derives https://PUBLIC_HOST/webapp/ from
# PUBLIC_HOST when it is empty. It is only ever wrong when it is set *and*
# names a different host — a leftover from the previous server.
if [[ -n "$WEBAPP" && "$WEBAPP" != *"$PUBLIC"* ]]; then
  die "Serverdagi .env da WEBAPP_URL boshqa hostga qarab turibdi:
    WEBAPP_URL=${WEBAPP}
    PUBLIC_HOST=${PUBLIC}
Mini App o'lik manzilni ochadi. WEBAPP_URL ni o'chiring (Django uni
PUBLIC_HOST dan o'zi yasaydi) yoki https://${PUBLIC}/webapp/ ga tuzating."
fi

info "Public host: ${PUBLIC}"

# --- 1. ship the code ---------------------------------------------------------
# Two passes, because the server owns some of what lives in this directory.
#
# The source trees are mirrored with --delete: without it a file deleted here
# lingers there forever, and a stale module that still imports something the
# repo has removed fails the frontend build — which is how this script broke
# the first time a page was deleted. Excluded paths (node_modules, dist,
# __pycache__) are protected from that delete by rsync itself, so the server's
# build artefacts survive.
#
# The root is synced without --delete, since .env, secrets/, media/ and
# backups/ sit alongside the tracked files and belong to the server alone.
SRC_DIRS=(apps bot core tasks tests scripts locale docker frontend)

info "Syncing source trees to ${HOST}:${REMOTE} …"
for dir in "${SRC_DIRS[@]}"; do
  [ -d "$dir" ] || continue
  rsync -az --delete \
    --exclude '__pycache__' --exclude 'node_modules' \
    --exclude 'dist' --exclude '.vite' \
    -e "$SSH_CMD" \
    "./${dir}/" "${USER}@${HOST}:${REMOTE}/${dir}/"
done

info "Syncing root files …"
# -f '- /*/' keeps this pass to the files at the top level; the loop above
# already handled every directory the repo owns.
rsync -az -f '- /*/' \
  --exclude '.env' --exclude '.git' --exclude 'celerybeat-schedule*' \
  -e "$SSH_CMD" \
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
# Every public entry point the customer or the shop actually touches. The Mini
# App is checked too: it is served by nginx from a different volume than the
# API, so it can be the only broken one.
info "Verifying through https://${PUBLIC} …"
sleep 3

check() {  # check <label> <path> <expected>
  local label="$1" path="$2" expect="$3" code
  code=$(curl -sk -o /dev/null -w '%{http_code}' --max-time 20 "https://${PUBLIC}${path}" || echo 000)
  [ "$code" = "$expect" ] || die "${label} (${path}) → ${code}, kutilgani ${expect}. Deploy is NOT healthy."
  info "  ✓ ${label} → ${code}"
}

check "catalog API"  "/api/v1/webapp/catalog/?lang=uz" 200
check "admin panel"  "/login"                          200
check "Mini App"     "/webapp/"                        200

info "✅ Deployed and healthy — API, admin panel and Mini App all answer 200."
info "   Mini App: https://${PUBLIC}/webapp/"
