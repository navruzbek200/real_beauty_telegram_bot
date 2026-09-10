#!/bin/sh
# One-time Let's Encrypt bootstrap for the Real Beauty CRM.
#
# The IP has no domain, so we use the sslip.io hostname that resolves straight
# to it — a real, publicly-valid name Let's Encrypt will issue for. Run once
# from the compose directory (/opt/realbeauty):
#
#   sh docker/nginx/init-letsencrypt.sh
#
# Idempotent enough to re-run: it force-renews and reloads.
set -e

DOMAIN=169-58-58-145.sslip.io
EMAIL=tmbekzod05@gmail.com
LIVE="/etc/letsencrypt/live/$DOMAIN"

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
