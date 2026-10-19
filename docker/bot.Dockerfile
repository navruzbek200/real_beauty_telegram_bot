FROM python:3.12-slim

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1

WORKDIR /app

# ffprobe is what lets the bot send a video at its real aspect ratio; without
# it Telegram guesses, and a 9:16 lesson arrives letterboxed into a square.
RUN apt-get update \
    && apt-get install -y --no-install-recommends libpq-dev ffmpeg \
    && rm -rf /var/lib/apt/lists/*

COPY requirements.txt .
# The VPS this is built on drops long downloads: pip's two default
# retries are not enough to get through a 300 MB install, and a build
# that dies two thirds of the way through costs the whole layer.
RUN pip install --no-cache-dir --retries 10 --timeout 60 -r requirements.txt

COPY . .

CMD ["python", "-m", "bot.main"]
