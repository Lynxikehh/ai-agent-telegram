FROM python:3.12-slim

# Node.js 20 + Claude Code CLI (dibutuhkan oleh claude-agent-sdk),
# plus tzdata untuk zona waktu pengingat.
RUN apt-get update \
    && apt-get install -y --no-install-recommends curl ca-certificates gnupg tzdata \
    && curl -fsSL https://deb.nodesource.com/setup_20.x | bash - \
    && apt-get install -y --no-install-recommends nodejs \
    && npm install -g @anthropic-ai/claude-code \
    && apt-get purge -y gnupg \
    && apt-get autoremove -y \
    && rm -rf /var/lib/apt/lists/*

WORKDIR /app

COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY bot ./bot

# Folder data (database SQLite + sesi) — dipetakan ke volume lewat compose
RUN mkdir -p /data
ENV DB_PATH=/data/bot.db

CMD ["python", "-m", "bot.main"]
