#!/bin/sh
set -eu

python - <<'PY'
from app import init_db

init_db()
print("database initialized for beat")
PY

exec celery -A celery_app.celery beat --loglevel="${CELERY_BEAT_LOG_LEVEL:-info}"
