#!/usr/bin/env bash
set -euo pipefail

# launch-application-linux.sh — start backend (uvicorn) and frontend (next) for local development
# Usage: ./launch-application-linux.sh

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

cd "$ROOT_DIR"

echo "Starting backend..."
cd backend

# Prefer 'uv' if available (per README). Otherwise create/activate a venv and run uvicorn.
if command -v uv >/dev/null 2>&1; then
  echo "Found 'uv' CLI — using it to run backend"
else
  # create venv if missing
  if [ ! -d ".venv" ]; then
    echo "Creating virtualenv at backend/.venv"
    python3 -m venv .venv
  fi

  # shellcheck disable=SC1091
  source .venv/bin/activate
  pip install uv
fi
uv sync --active
uv run fastapi run app.py &
BACKEND_PID=$!
echo "Backend started via uv (pid: $BACKEND_PID)"

cd "$ROOT_DIR/frontend"

if ! command -v npm >/dev/null 2>&1; then
  echo "npm not found. Install Node.js/npm first."
  kill $BACKEND_PID || true
  exit 1
fi

echo "Starting frontend..."
npm i
npm run dev &
FRONTEND_PID=$!
echo "Frontend started (pid: $FRONTEND_PID)"

echo
echo "Logs are streaming to your terminal. To stop both services, press Ctrl+C."

# Ensure child processes are killed when this script exits
_cleanup() {
  echo "Shutting down..."
  kill "$FRONTEND_PID" 2>/dev/null || true
  kill "$BACKEND_PID" 2>/dev/null || true
  wait "$FRONTEND_PID" 2>/dev/null || true
  wait "$BACKEND_PID" 2>/dev/null || true
}

trap _cleanup INT TERM EXIT

wait "$BACKEND_PID" "$FRONTEND_PID"
