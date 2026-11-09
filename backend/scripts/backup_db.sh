#!/usr/bin/env bash
# ==============================================================================
# CloudSage Database Backup & Disaster Recovery Script
# Creates a compressed, timestamped, checksummed backup of PostgreSQL database.
# ==============================================================================

set -eo pipefail

BACKUP_DIR="${BACKUP_DIR:-/backups}"
TIMESTAMP=$(date -u +"%Y%m%d_%H%M%S")
RETENTION_DAYS="${BACKUP_RETENTION_DAYS:-30}"

PG_USER="${POSTGRES_USER:-postgres}"
PG_HOST="${POSTGRES_SERVER:-localhost}"
PG_PORT="${POSTGRES_PORT:-5432}"
PG_DB="${POSTGRES_DB:-cloudsage}"

mkdir -p "$BACKUP_DIR"

BACKUP_FILE="${BACKUP_DIR}/cloudsage_backup_${TIMESTAMP}.sql.gz"
CHECKSUM_FILE="${BACKUP_FILE}.sha256"

echo "=========================================================="
echo " CloudSage Database Backup Utility"
echo " Timestamp:   $TIMESTAMP"
echo " Target DB:   $PG_DB on $PG_HOST:$PG_PORT"
echo " Destination: $BACKUP_FILE"
echo "=========================================================="

START_TIME=$(date +%s)

# Perform backup using pg_dump if available, or simulate if in test/mock mode
if command -v pg_dump >/dev/null 2>&1; then
    echo "[Backup] Executing pg_dump with gzip compression..."
    export PGPASSWORD="${POSTGRES_PASSWORD:-postgres}"
    pg_dump -h "$PG_HOST" -p "$PG_PORT" -U "$PG_USER" -d "$PG_DB" \
        --no-owner --no-acl --clean --if-exists | gzip -c > "$BACKUP_FILE"
else
    echo "[Backup] pg_dump utility not found in PATH."
    if [ "${TEST_MOCK_BACKUP:-false}" = "true" ] || [ -n "$MOCK_BACKUP_CONTENT" ]; then
        echo "[Backup] Creating test mock archive for test harness..."
        echo "${MOCK_BACKUP_CONTENT:-MOCK_DATABASE_DUMP_SQL_CONTENT}" | gzip -c > "$BACKUP_FILE"
    else
        echo "[Backup] ERROR: pg_dump utility is required to create a production database backup." >&2
        exit 1
    fi
fi

# Verify backup was created and has non-zero size
if [ ! -s "$BACKUP_FILE" ]; then
    echo "[Backup] ERROR: Backup file was created but is empty." >&2
    rm -f "$BACKUP_FILE"
    exit 1
fi

FILE_SIZE=$(ls -lh "$BACKUP_FILE" | awk '{print $5}')
echo "[Backup] Archive size: $FILE_SIZE"

# Generate SHA256 Checksum
echo "[Backup] Calculating cryptographic SHA256 checksum..."
if command -v sha256sum >/dev/null 2>&1; then
    sha256sum "$BACKUP_FILE" > "$CHECKSUM_FILE"
elif command -v shasum >/dev/null 2>&1; then
    shasum -a 256 "$BACKUP_FILE" > "$CHECKSUM_FILE"
else
    # Python fallback for checksum calculation
    python3 -c "import hashlib, sys; f=sys.argv[1]; print(hashlib.sha256(open(f, 'rb').read()).hexdigest() + '  ' + f)" "$BACKUP_FILE" > "$CHECKSUM_FILE"
fi

CHECKSUM=$(awk '{print $1}' "$CHECKSUM_FILE")
echo "[Backup] SHA256: $CHECKSUM"

# Backup retention pruning
if [ "$RETENTION_DAYS" -gt 0 ]; then
    echo "[Backup] Enforcing retention policy ($RETENTION_DAYS days)..."
    find "$BACKUP_DIR" -type f -name "cloudsage_backup_*.sql.gz*" -mtime +"$RETENTION_DAYS" -exec rm -f {} + 2>/dev/null || true
fi

END_TIME=$(date +%s)
DURATION=$((END_TIME - START_TIME))

echo "=========================================================="
echo " Backup Completed Successfully in ${DURATION}s"
echo " Archive:  $BACKUP_FILE"
echo " Checksum: $CHECKSUM"
echo "=========================================================="
exit 0
