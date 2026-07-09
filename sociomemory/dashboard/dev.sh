#!/usr/bin/env bash
# Build the dashboard frontend and serve it (UI + /api) from the Python server.
# Single process on :8765 — no Vite dev server. Ctrl+C stops it.
set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"   # .../sociomemory/dashboard
REPO_ROOT="$(cd "$SCRIPT_DIR/../.." && pwd)"
WEB_DIR="$SCRIPT_DIR/web"
# Prefer an explicit $PYTHON, else an active venv, else python3, else python.
PYTHON="${PYTHON:-${VIRTUAL_ENV:+$VIRTUAL_ENV/bin/python}}"
PYTHON="${PYTHON:-$(command -v python3 || command -v python)}"
API_PORT="${SOCIOMEMORY_DASHBOARD_PORT:-8765}"

# Load local env (Neo4j creds, LLM keys) for the backend.
ENV_FILE="$REPO_ROOT/.env.local"
if [ -f "$ENV_FILE" ]; then
  set -a; . "$ENV_FILE"; set +a
  echo "→ loaded $ENV_FILE"
else
  echo "⚠  $ENV_FILE not found — backend may lack Neo4j/LLM config"
fi

# Free the port if a stale server is holding it.
if command -v lsof >/dev/null 2>&1 && lsof -ti "tcp:$API_PORT" >/dev/null 2>&1; then
  echo "→ port $API_PORT busy; stopping existing listener"
  lsof -ti "tcp:$API_PORT" | xargs kill 2>/dev/null || true
  sleep 1
fi

# Build the production bundle into web/dist (the server serves it directly).
if [ ! -d "$WEB_DIR/node_modules" ]; then
  echo "→ installing web deps (first run)..."
  ( cd "$WEB_DIR" && npm install )
fi
echo "→ building frontend (dist)..."
( cd "$WEB_DIR" && npm run build )

echo "→ serving UI + API: http://127.0.0.1:$API_PORT   ·   Ctrl+C to stop"
cd "$REPO_ROOT"
exec "$PYTHON" -m sociomemory.dashboard.server --port "$API_PORT"
