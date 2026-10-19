FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

# ffmpeg earns its ~70MB twice over: it lifts a poster frame out of every
# lesson video so the course is a wall of pictures rather than a list of
# identical play icons, and it reads the dimensions Telegram needs to show a
# video at its real aspect ratio instead of a guess.
RUN apt-get update \
    && apt-get install -y --no-install-recommends build-essential libpq-dev ffmpeg \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
# The VPS this is built on drops long downloads: pip's two default
# retries are not enough to get through a 300 MB install, and a build
# that dies two thirds of the way through costs the whole layer.
RUN pip install --no-cache-dir --retries 10 --timeout 60 -r requirements.txt

COPY . .

# .mo files are derived, not committed; skipping this leaves the admin on
# Django's half-finished uz catalogue — half the panel turns English.
RUN python scripts/compile_messages.py

# collectstatic needs no DB and no real secret — run at build time on the
# dedicated build settings so the image is complete. (The old `|| true`
# variant silently shipped images with no static files when this failed.)
RUN DJANGO_SETTINGS_MODULE=core.settings.build python manage.py collectstatic --noinput

EXPOSE 8000
