#!/usr/bin/env bash
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
cd "$ROOT"

PORT="${NEURALPAL_BACKEND_PORT:-8766}"

if lsof -nP -iTCP:"$PORT" -sTCP:LISTEN >/dev/null 2>&1; then
  OLD_PID="$(lsof -nP -iTCP:"$PORT" -sTCP:LISTEN -t 2>/dev/null | head -1)"
  echo "Port $PORT already in use (PID ${OLD_PID:-unknown}). Stopping old backend..."
  if [[ -n "${OLD_PID:-}" ]]; then
    kill "$OLD_PID" 2>/dev/null || true
    sleep 0.5
  fi
fi

if [[ ! -d .venv ]]; then
  python3 -m venv .venv
fi
# shellcheck disable=SC1091
source .venv/bin/activate
pip install -q -r requirements.txt
python -m server.main
