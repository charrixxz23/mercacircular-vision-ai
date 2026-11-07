#!/usr/bin/env bash
# Instalación en Linux, macOS o WSL. Equivale a scripts/setup.ps1.
set -euo pipefail
ROOT="$(cd "$(dirname "$0")/.." && pwd)"
PY="${PYTHON:-python3}"
"$PY" -c 'import sys; assert sys.version_info >= (3, 11), "Se necesita Python 3.11+"'
[ -x "$ROOT/backend/.venv/bin/python" ] || "$PY" -m venv "$ROOT/backend/.venv"
"$ROOT/backend/.venv/bin/pip" install -q --upgrade pip
"$ROOT/backend/.venv/bin/pip" install -r "$ROOT/requirements-dev.txt"
(cd "$ROOT/frontend" && npm ci --no-audit --no-fund)
[ -f "$ROOT/.env" ] || cp "$ROOT/.env.example" "$ROOT/.env"
echo "Listo. Inicie con: scripts/start.sh"
