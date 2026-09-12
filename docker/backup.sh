#!/bin/sh -eu
# Minimal Compose backup (pg_dump + CouchDB export + tar); see kubernetes/README.md "Backups (Compose)".

POSTGRES_CONTAINER="${POSTGRES_CONTAINER:-ahc-postgres}"
COUCHDB_CONTAINER="${COUCHDB_CONTAINER:-ahc-couchdb}"
COUCHDB_PORT="${COUCHDB_PORT:-5982}"
MEDIA_DIR="${MEDIA_DIR:-./static/media}"
PRIVATE_STORAGE_DIR="${VOLUMEN_PRIVATE_STORAGE:-}"
BACKUP_DIR="${BACKUP_DIR:-./backups}"

: "${POSTGRES_USER:?POSTGRES_USER must be set (source .env first)}"
: "${POSTGRES_DB:?POSTGRES_DB must be set (source .env first)}"
: "${COUCHDB_USER:?COUCHDB_USER must be set (source .env first)}"
: "${COUCHDB_PASSWORD:?COUCHDB_PASSWORD must be set (source .env first)}"

stamp="$(date -u +%Y%m%dT%H%M%SZ)"
mkdir -p "$BACKUP_DIR"

echo "==> Postgres: pg_dump -Fc from $POSTGRES_CONTAINER"
docker exec "$POSTGRES_CONTAINER" pg_dump -Fc -U "$POSTGRES_USER" "$POSTGRES_DB" \
  > "$BACKUP_DIR/pg-$stamp.dump"

echo "==> CouchDB: _all_docs diagnostic export from $COUCHDB_CONTAINER (not attachment-complete)"
docker exec "$COUCHDB_CONTAINER" curl -fsS --user "$COUCHDB_USER:$COUCHDB_PASSWORD" \
  "http://localhost:$COUCHDB_PORT/appendixes/_all_docs?include_docs=true" \
  > "$BACKUP_DIR/couchdb-appendixes-$stamp.json"

if [ -d "$MEDIA_DIR" ]; then
  echo "==> Media: tar of $MEDIA_DIR"
  tar -czf "$BACKUP_DIR/media-$stamp.tar.gz" -C "$(dirname "$MEDIA_DIR")" "$(basename "$MEDIA_DIR")"
else
  echo "==> Media: skipped, $MEDIA_DIR not found"
fi

if [ -n "$PRIVATE_STORAGE_DIR" ] && [ -d "$PRIVATE_STORAGE_DIR" ]; then
  echo "==> Private storage: tar of $PRIVATE_STORAGE_DIR"
  tar -czf "$BACKUP_DIR/private-storage-$stamp.tar.gz" -C "$(dirname "$PRIVATE_STORAGE_DIR")" "$(basename "$PRIVATE_STORAGE_DIR")"
else
  echo "==> Private storage: skipped, VOLUMEN_PRIVATE_STORAGE not set or not found"
fi

echo "==> Done: $BACKUP_DIR/*-$stamp.*"
echo "==> Verify the Postgres dump before trusting it: ./docker/restore-check.sh $BACKUP_DIR/pg-$stamp.dump"
