#!/bin/sh
set -eu

ROOT_DIR="$(cd "$(dirname "$0")/.." && pwd)"
CRAWLER_DIR="$ROOT_DIR/crawler_service"
VENV_DIR="$CRAWLER_DIR/.venv"

if [ ! -x "$VENV_DIR/bin/python" ]; then
  echo "Crawler virtual environment not found. Run crawler_service/scripts/bootstrap_venv.sh first."
  exit 1
fi

export CRAWLER_PROVIDER="${CRAWLER_PROVIDER:-mock}"
export CRAWLER_PORT="${CRAWLER_PORT:-8081}"
export CRAWLER_RELOAD="${CRAWLER_RELOAD:-false}"
export CRAWLER_HOST="${CRAWLER_HOST:-127.0.0.1}"

if [ "$CRAWLER_RELOAD" = "true" ]; then
  exec "$VENV_DIR/bin/python" -m uvicorn crawler_service.main:app --host "$CRAWLER_HOST" --port "$CRAWLER_PORT" --reload --reload-dir "$CRAWLER_DIR" --app-dir "$ROOT_DIR"
fi

exec "$VENV_DIR/bin/python" -m uvicorn crawler_service.main:app --host "$CRAWLER_HOST" --port "$CRAWLER_PORT" --app-dir "$ROOT_DIR"
