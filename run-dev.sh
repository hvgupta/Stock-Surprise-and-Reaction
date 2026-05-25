#!/usr/bin/env bash
set -euo pipefail

# run-dev.sh — start backend (uvicorn) and frontend (next) for local development
# Usage: ./run-dev.sh

ROOT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"

cd "$ROOT_DIR"

echo "Starting backend..."
cd backend

if ! command -v uvicorn >/dev/null 2>&1; then
  echo "uvicorn not found. Install it with: pip install 'uvicorn[standard]'"
  exit 1
fi

# start backend in background and capture pid
uvicorn backend.app:app --reload --port 8000 &
BACKEND_PID=$!
echo "Backend started (pid: $BACKEND_PID)"

cd "$ROOT_DIR/frontend"

if ! command -v npm >/dev/null 2>&1; then
  echo "npm not found. Install Node.js/npm first."
  kill $BACKEND_PID || true
  exit 1
fi

echo "Starting frontend..."
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
