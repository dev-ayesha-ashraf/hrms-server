#!/bin/sh
# entrypoint.sh — run on every container start
# Waits for PostgreSQL, applies Alembic migrations, seeds initial data,
# then hands off to uvicorn.
set -e

MAX_ATTEMPTS=30
attempt=0

echo "==> Waiting for PostgreSQL..."
until python -c "
import os, sys, psycopg2
try:
    conn = psycopg2.connect(os.environ['DATABASE_URL'])
    conn.close()
except Exception:
    sys.exit(1)
" 2>/dev/null; do
    attempt=$((attempt + 1))
    if [ "$attempt" -ge "$MAX_ATTEMPTS" ]; then
        echo "ERROR: PostgreSQL not reachable after $MAX_ATTEMPTS attempts. Aborting."
        exit 1
    fi
    printf "    not ready yet (attempt %d/%d), retrying in 2s...\n" "$attempt" "$MAX_ATTEMPTS"
    sleep 2
done

echo "==> PostgreSQL is ready."

echo "==> Running Alembic migrations..."
alembic upgrade head

echo "==> Seeding initial data (skips existing rows)..."
python seed.py

echo "==> Starting HRMS API server..."
exec uvicorn main:app --host 0.0.0.0 --port 8000 --workers 1
