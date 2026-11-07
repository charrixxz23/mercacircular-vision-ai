#!/usr/bin/env bash
# Inicia backend (8000) y frontend (3000) en la misma terminal. Ctrl+C detiene ambos.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
trap 'kill 0' EXIT
(cd "$ROOT/backend" && .venv/bin/python -m uvicorn app.main:app --host 127.0.0.1 --port 8000) &
(cd "$ROOT/frontend" && npx next dev -p 3000) &
echo "Abra http://localhost:3000"
wait
