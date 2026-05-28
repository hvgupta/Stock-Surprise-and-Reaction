FROM python:3.11-slim-bookworm

ENV PYTHONDONTWRITEBYTECODE=1 \
    PYTHONUNBUFFERED=1 \
    PIP_NO_CACHE_DIR=1 \
    NEXT_TELEMETRY_DISABLED=1 \
    PATH="/root/.local/bin:${PATH}"

WORKDIR /app

RUN apt-get update \
    && apt-get install -y --no-install-recommends ca-certificates curl gnupg \
    && curl -fsSL https://deb.nodesource.com/setup_20.x | bash - \
    && apt-get install -y --no-install-recommends nodejs \
    && rm -rf /var/lib/apt/lists/*

RUN pip install --no-cache-dir uv

COPY pyproject.toml uv.lock ./
RUN uv sync --frozen --no-install-project

COPY frontend/package*.json ./frontend/
WORKDIR /app/frontend
RUN npm ci

COPY frontend/ ./
RUN npm run build

WORKDIR /app
COPY backend/ ./backend/

EXPOSE 8000 3000

CMD ["bash", "-lc", "set -euo pipefail; uv run uvicorn backend.app:app --host 0.0.0.0 --port 8000 & backend_pid=$!; cd /app/frontend && npm run start -- --hostname 0.0.0.0 --port 3000 & frontend_pid=$!; trap 'kill ${backend_pid} ${frontend_pid} 2>/dev/null || true' INT TERM EXIT; wait -n ${backend_pid} ${frontend_pid}"]