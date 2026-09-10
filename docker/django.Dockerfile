FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

RUN apt-get update \
    && apt-get install -y --no-install-recommends build-essential libpq-dev \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# .mo files are derived, not committed; skipping this leaves the admin on
# Django's half-finished uz catalogue — half the panel turns English.
RUN python scripts/compile_messages.py

# collectstatic needs no DB and no real secret — run at build time on the
# dedicated build settings so the image is complete. (The old `|| true`
# variant silently shipped images with no static files when this failed.)
RUN DJANGO_SETTINGS_MODULE=core.settings.build python manage.py collectstatic --noinput

EXPOSE 8000
