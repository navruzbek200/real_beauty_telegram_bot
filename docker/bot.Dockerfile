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
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

CMD ["python", "-m", "bot.main"]
