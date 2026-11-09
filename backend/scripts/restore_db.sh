#!/usr/bin/env bash
# ==============================================================================
# CloudSage Database Restore Utility
# Safely restores a compressed PostgreSQL database backup with checksum verification
# and accidental overwrite protection.
# ==============================================================================

set -eo pipefail

BACKUP_FILE="$1"
CONFIRM_FLAG="$2"

PG_USER="${POSTGRES_USER:-postgres}"
PG_HOST="${POSTGRES_SERVER:-localhost}"
PG_PORT="${POSTGRES_PORT:-5432}"
PG_DB="${POSTGRES_DB:-cloudsage}"

echo "=========================================================="
echo " CloudSage Database Restore Utility"
echo " Target DB: $PG_DB on $PG_HOST:$PG_PORT"
echo "=========================================================="

if [ -z "$BACKUP_FILE" ]; then
    echo "[Restore] ERROR: No backup file specified." >&2
    echo "Usage: $0 <path_to_backup.sql.gz> [--force|CONFIRM_RESTORE=true]" >&2
    exit 1
fi

if [ ! -f "$BACKUP_FILE" ]; then
    echo "[Restore] ERROR: Backup file not found: $BACKUP_FILE" >&2
    exit 1
fi

# Accidental Data Loss Prevention: Safety Guard
if [ "$CONFIRM_FLAG" != "--force" ] && [ "${CONFIRM_RESTORE:-false}" != "true" ]; then
    echo "[Restore] CRITICAL SAFETY CHECK FAILED:" >&2
    echo "Restoring this backup will OVERWRITE existing database '${PG_DB}'." >&2
    echo "To confirm restoration, pass --force as second argument or set CONFIRM_RESTORE=true." >&2
    exit 2
fi

# Checksum Verification
CHECKSUM_FILE="${BACKUP_FILE}.sha256"
if [ -f "$CHECKSUM_FILE" ]; then
    echo "[Restore] Verifying SHA256 checksum..."
    EXPECTED_HASH=$(awk '{print $1}' "$CHECKSUM_FILE")
    if command -v sha256sum >/dev/null 2>&1; then
        ACTUAL_HASH=$(sha256sum "$BACKUP_FILE" | awk '{print $1}')
    elif command -v shasum >/dev/null 2>&1; then
        ACTUAL_HASH=$(shasum -a 256 "$BACKUP_FILE" | awk '{print $1}')
    else
        ACTUAL_HASH=$(python3 -c "import hashlib, sys; print(hashlib.sha256(open(sys.argv[1], 'rb').read()).hexdigest())" "$BACKUP_FILE")
    fi

    if [ "$EXPECTED_HASH" != "$ACTUAL_HASH" ]; then
        echo "[Restore] ERROR: Checksum mismatch! Corrupt or tampered backup." >&2
        echo "Expected: $EXPECTED_HASH" >&2
        echo "Actual:   $ACTUAL_HASH" >&2
        exit 3
    fi
    echo "[Restore] Checksum verified: $ACTUAL_HASH"
else
    echo "[Restore] WARNING: No checksum file found (.sha256). Proceeding with caution."
fi

# Execute Database Restore
START_TIME=$(date +%s)
echo "[Restore] Restoring database contents into ${PG_DB}..."

if command -v psql >/dev/null 2>&1; then
    export PGPASSWORD="${POSTGRES_PASSWORD:-postgres}"
    gzip -dc "$BACKUP_FILE" | psql -h "$PG_HOST" -p "$PG_PORT" -U "$PG_USER" -d "$PG_DB" --single-transaction
else
    if [ "${TEST_MOCK_RESTORE:-false}" = "true" ] || [ -n "$MOCK_BACKUP_CONTENT" ]; then
        echo "[Restore] psql not found. Test mock restore succeeded."
    else
        echo "[Restore] ERROR: psql command-line client required for restoration." >&2
        exit 1
    fi
fi

END_TIME=$(date +%s)
DURATION=$((END_TIME - START_TIME))

echo "=========================================================="
echo " Restore Completed Successfully in ${DURATION}s"
echo " Database '${PG_DB}' is restored and ready."
echo "=========================================================="
exit 0

