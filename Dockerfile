FROM python:3.13-slim-bookworm

RUN apt-get update \
    && apt-get install -y --no-install-recommends \
       ffmpeg \
       curl \
       ca-certificates \
       unzip \
    && rm -rf /var/lib/apt/lists/*

# Node.js 24 is required by yt-dlp's current YouTube EJS challenge solver.
RUN curl -fsSL https://deb.nodesource.com/setup_24.x | bash - \
    && apt-get update \
    && apt-get install -y --no-install-recommends nodejs \
    && node --version \
    && npm --version \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .

RUN pip install --no-cache-dir -r requirements.txt

COPY . .

CMD ["python", "bot.py"]
