#!/bin/sh
# Database backup: pg_dump custom format + retention + verification.
# Usage: POSTGRES_HOST=... POSTGRES_USER=... POSTGRES_DB=... ./backup.sh [backup_dir]
# Required env: PGPASSWORD (never pass on the command line).
set -eu

BACKUP_DIR="${1:-/backups}"
RETENTION_DAYS="${RETENTION_DAYS:-14}"
HOST="${POSTGRES_HOST:-localhost}"
USER="${POSTGRES_USER:-bi}"
DB="${POSTGRES_DB:-bi_platform}"

mkdir -p "$BACKUP_DIR"
STAMP="$(date +%Y%m%d-%H%M%S)"
FILE="$BACKUP_DIR/bi-$STAMP.dump"

echo "Backing up $DB@$HOST -> $FILE"
pg_dump -h "$HOST" -U "$USER" -Fc "$DB" > "$FILE"

echo "Verifying backup..."
pg_restore --list "$FILE" > /dev/null && echo "backup OK: $FILE" || {
  echo "backup verification FAILED"; rm -f "$FILE"; exit 1
}

echo "Applying retention (${RETENTION_DAYS}d)..."
find "$BACKUP_DIR" -name 'bi-*.dump' -mtime +"$RETENTION_DAYS" -delete

echo "Recording metric timestamp..."
date +%s > "$BACKUP_DIR/.last_backup_timestamp"
