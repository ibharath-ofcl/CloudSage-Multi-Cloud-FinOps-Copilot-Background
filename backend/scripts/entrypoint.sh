#!/usr/bin/env bash
# CloudSage Production Backend Entrypoint
# Handles database readiness checks, automated Alembic migrations,
# and hands off execution to the production ASGI application server.

set -eo pipefail

echo "=========================================================="
echo " Starting CloudSage FinOps Backend Container"
echo " Environment: ${ENVIRONMENT:-production}"
echo " Port:        ${PORT:-8000}"
echo "=========================================================="

# 1. Database Connection & Readiness Check
RUN_MIGRATIONS="${RUN_MIGRATIONS:-true}"
SKIP_DB_CHECK="${SKIP_DB_CHECK:-false}"
MAX_RETRIES="${DB_WAIT_MAX_RETRIES:-30}"
RETRY_INTERVAL="${DB_WAIT_RETRY_INTERVAL:-2}"

if [ "$SKIP_DB_CHECK" != "true" ]; then
    echo "[Entrypoint] Waiting for database readiness..."
    python3 - << 'EOF'
import os
import sys
import time
from sqlalchemy import create_engine, text

db_url = os.environ.get("SYNC_DATABASE_URL")
if not db_url:
    user = os.environ.get("POSTGRES_USER", "postgres")
    pwd = os.environ.get("POSTGRES_PASSWORD", "postgres")
    host = os.environ.get("POSTGRES_SERVER", "localhost")
    port = os.environ.get("POSTGRES_PORT", "5432")
    db = os.environ.get("POSTGRES_DB", "cloudsage")
    db_url = f"postgresql://{user}:{pwd}@{host}:{port}/{db}"

# Fallback for SQLite in lightweight/test containers
if "sqlite" in db_url:
    print("[Entrypoint] SQLite database detected, skipping network socket wait.")
    sys.exit(0)

max_retries = int(os.environ.get("DB_WAIT_MAX_RETRIES", "30"))
interval = float(os.environ.get("DB_WAIT_RETRY_INTERVAL", "2"))

for attempt in range(1, max_retries + 1):
    try:
        engine = create_engine(db_url, pool_pre_ping=True, connect_args={"connect_timeout": 3})
        with engine.connect() as conn:
            conn.execute(text("SELECT 1"))
        print(f"[Entrypoint] Database is ready! (Connected on attempt {attempt})")
        sys.exit(0)
    except Exception as exc:
        print(f"[Entrypoint] Database not ready yet (attempt {attempt}/{max_retries}): {exc}")
        time.sleep(interval)

print("[Entrypoint] ERROR: Timed out waiting for database to become ready.", file=sys.stderr)
sys.exit(1)
EOF
    echo "[Entrypoint] Database connectivity verified."
fi

# 2. Automated Schema Migrations
if [ "$RUN_MIGRATIONS" = "true" ]; then
    echo "[Entrypoint] Running database migrations (alembic upgrade head)..."
    if [ -f "backend/alembic.ini" ]; then
        alembic -c backend/alembic.ini upgrade head
    elif [ -f "alembic.ini" ]; then
        alembic upgrade head
    else
        echo "[Entrypoint] WARNING: alembic.ini not found, skipping migrations."
    fi
    echo "[Entrypoint] Database migrations applied successfully."
fi

# 3. Hand-off execution to application server
echo "[Entrypoint] Handing off to application server: $@"
exec "$@"
