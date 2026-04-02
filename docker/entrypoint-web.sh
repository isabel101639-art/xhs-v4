#!/bin/sh
set -eu

python - <<'PY'
from app import init_db

init_db()
print("database initialized")
PY

exec gunicorn --config docker/gunicorn.conf.py wsgi:app
