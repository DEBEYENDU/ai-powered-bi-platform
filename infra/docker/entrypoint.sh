#!/bin/sh
# Entrypoint: wait for DB, run migrations, exec CMD (graceful shutdown via exec).
set -e

if [ -n "$DATABASE_URL" ]; then
  echo "Waiting for database..."
  for i in $(seq 1 30); do
    python -c "
import sys, sqlalchemy
from sqlalchemy import create_engine, text
import os
try:
    eng = create_engine(os.environ['DATABASE_URL'])
    with eng.connect() as c:
        c.execute(text('SELECT 1'))
    sys.exit(0)
except Exception as e:
    print('db not ready:', e)
    sys.exit(1)
" && break
    echo "retry $i/30..."
    sleep 2
  done
fi

if [ "${RUN_MIGRATIONS:-true}" = "true" ]; then
  echo "Running migrations..."
  alembic upgrade head || echo "WARNING: migrations failed, continuing"
fi

exec "$@"
