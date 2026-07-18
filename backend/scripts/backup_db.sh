#!/usr/bin/env bash
# Backup database (PostgreSQL or SQLite)
#
# Usage:
#   ./backend/scripts/backup_db.sh
#   OUTPUT_DIR=/var/backups/pas ./backend/scripts/backup_db.sh
#
# Postgres: set DB_NAME (and DB_USER/DB_PASSWORD/DB_HOST/DB_PORT) in env or backend/.env
# SQLite: leave DB_NAME empty; copies backend/db.sqlite3

set -euo pipefail

SCRIPT_DIR="$(cd "$(dirname "${BASH_SOURCE[0]}")" && pwd)"
BACKEND_ROOT="$(cd "$SCRIPT_DIR/.." && pwd)"
OUTPUT_DIR="${OUTPUT_DIR:-$BACKEND_ROOT/backups}"
mkdir -p "$OUTPUT_DIR"
STAMP="$(date +%Y%m%d_%H%M%S)"
ENV_FILE="$BACKEND_ROOT/.env"

env_val() {
  local key="$1"
  if [[ -n "${!key:-}" ]]; then
    echo "${!key}"
    return
  fi
  if [[ -f "$ENV_FILE" ]]; then
    local line
    line="$(grep -E "^[[:space:]]*${key}[[:space:]]*=" "$ENV_FILE" | head -n1 || true)"
    if [[ -n "$line" ]]; then
      echo "$line" | sed -E "s/^[[:space:]]*${key}[[:space:]]*=[[:space:]]*//" | sed -E "s/^['\"]|['\"]$//g"
    fi
  fi
}

DB_NAME="$(env_val DB_NAME || true)"

if [[ -n "${DB_NAME:-}" ]]; then
  DB_USER="$(env_val DB_USER)"; DB_USER="${DB_USER:-postgres}"
  DB_HOST="$(env_val DB_HOST)"; DB_HOST="${DB_HOST:-localhost}"
  DB_PORT="$(env_val DB_PORT)"; DB_PORT="${DB_PORT:-5432}"
  DB_PASSWORD="$(env_val DB_PASSWORD || true)"
  OUT_FILE="$OUTPUT_DIR/pas_${DB_NAME}_${STAMP}.dump"
  echo "Backing up PostgreSQL database '$DB_NAME' to $OUT_FILE"
  if [[ -n "${DB_PASSWORD:-}" ]]; then
    export PGPASSWORD="$DB_PASSWORD"
  fi
  pg_dump -Fc -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" -f "$OUT_FILE"
else
  SQLITE="$BACKEND_ROOT/db.sqlite3"
  if [[ ! -f "$SQLITE" ]]; then
    echo "No DB_NAME set and $SQLITE not found" >&2
    exit 1
  fi
  OUT_FILE="$OUTPUT_DIR/pas_sqlite_${STAMP}.sqlite3"
  echo "Backing up SQLite to $OUT_FILE (dev only — not for production payroll)"
  cp "$SQLITE" "$OUT_FILE"
fi

SIZE="$(wc -c < "$OUT_FILE" | tr -d ' ')"
if [[ "$SIZE" -le 0 ]]; then
  echo "Backup file is empty: $OUT_FILE" >&2
  exit 1
fi
echo "OK: $OUT_FILE ($SIZE bytes)"
echo "Next: verify restore on staging per docs/BACKUP_AND_RESTORE.md"
