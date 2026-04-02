#!/bin/sh
set -eu

ROOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
VENV_DIR="$ROOT_DIR/.venv"

if [ ! -x "$VENV_DIR/bin/python" ]; then
  echo "Virtual environment not found. Run scripts/bootstrap_venv.sh first."
  exit 1
fi

export FLASK_DEBUG=1
export PORT="${PORT:-5000}"

exec "$VENV_DIR/bin/python" "$ROOT_DIR/app.py"
