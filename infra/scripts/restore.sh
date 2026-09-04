#!/bin/sh
# Disaster recovery: restore a pg_dump custom-format backup into a database.
# Usage: ./restore.sh <backup_file> [target_db]
# DANGER: overwrites the target database. Requires typed confirmation.
set -eu

FILE="${1:?usage: restore.sh <backup_file> [target_db]}"
TARGET_DB="${2:-bi_platform_restore}"
HOST="${POSTGRES_HOST:-localhost}"
USER="${POSTGRES_USER:-bi}"

echo "This will restore $FILE into database '$TARGET_DB' on $HOST."
printf "Type the target db name to confirm: "
read -r CONFIRM
[ "$CONFIRM" = "$TARGET_DB" ] || { echo "Aborted."; exit 1; }

echo "Verifying backup..."
pg_restore --list "$FILE" > /dev/null || { echo "Invalid backup file"; exit 1; }

psql -h "$HOST" -U "$USER" -d postgres -c "DROP DATABASE IF EXISTS \"$TARGET_DB\";"
psql -h "$HOST" -U "$USER" -d postgres -c "CREATE DATABASE \"$TARGET_DB\";"
pg_restore -h "$HOST" -U "$USER" -d "$TARGET_DB" --no-owner "$FILE"
echo "Restore complete: $TARGET_DB"
echo "Next: run 'alembic upgrade head' against the restored DB, then smoke tests."
