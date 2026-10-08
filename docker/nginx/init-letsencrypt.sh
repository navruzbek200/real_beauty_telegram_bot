#!/bin/sh
# One-time Let's Encrypt bootstrap for the Real Beauty CRM.
#
# Reads the hostname from .env (PUBLIC_HOST) so this script never has to be
# edited when the stack moves to a new server. If the server has no domain
# yet, use the sslip.io name that resolves straight to its IP — for 1.2.3.4
# that is 1-2-3-4.sslip.io, a real publicly-valid name Let's Encrypt issues for.
#
# Run once from the compose directory (/opt/realbeauty):
#
#   sh docker/nginx/init-letsencrypt.sh
#
# Idempotent enough to re-run: it clears the old material and reissues.
set -e

cd "$(dirname "$0")/../.."

[ -f .env ] || { echo "❌ .env topilmadi — avval .env.example dan nusxa oling."; exit 1; }
# shellcheck disable=SC1091
. ./.env

DOMAIN="${PUBLIC_HOST:-}"
EMAIL="${LETSENCRYPT_EMAIL:-}"

[ -n "$DOMAIN" ] || { echo "❌ .env da PUBLIC_HOST bo'sh. Masalan: PUBLIC_HOST=1-2-3-4.sslip.io"; exit 1; }
[ -n "$EMAIL" ]  || { echo "❌ .env da LETSENCRYPT_EMAIL bo'sh — sertifikat muddati haqida ogohlantirish shu manzilga keladi."; exit 1; }

LIVE="/etc/letsencrypt/live/$DOMAIN"
echo "→ domen: $DOMAIN   email: $EMAIL"

echo "→ 1/4 dummy cert so nginx can boot with the :443 block"
docker compose run --rm --entrypoint "/bin/sh -c \"\
  mkdir -p '$LIVE' && \
  openssl req -x509 -nodes -newkey rsa:2048 -days 1 \
    -keyout '$LIVE/privkey.pem' -out '$LIVE/fullchain.pem' \
    -subj '/CN=$DOMAIN'\"" certbot

echo "→ 2/4 (re)start nginx with the TLS config"
docker compose up -d nginx

echo "→ 3/4 clear the dummy and request the real certificate"
docker compose run --rm --entrypoint "/bin/sh -c \"\
  rm -rf /etc/letsencrypt/live/$DOMAIN \
         /etc/letsencrypt/archive/$DOMAIN \
         /etc/letsencrypt/renewal/$DOMAIN.conf\"" certbot
docker compose run --rm --entrypoint "certbot certonly --webroot \
  -w /var/www/certbot -d $DOMAIN \
  --email $EMAIL --agree-tos --no-eff-email --non-interactive" certbot

echo "→ 4/4 reload nginx with the real certificate"
docker compose exec nginx nginx -s reload

echo "✅ HTTPS ready:  https://$DOMAIN"
echo "   Mini App:     https://$DOMAIN/webapp/"
