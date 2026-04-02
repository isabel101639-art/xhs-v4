#!/bin/sh
set -eu

python - <<'PY'
from app import init_db

init_db()
print("database initialized for worker")
PY

exec celery -A celery_app.celery worker --loglevel="${CELERY_LOG_LEVEL:-info}"
