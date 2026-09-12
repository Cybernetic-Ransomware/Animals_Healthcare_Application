#!/bin/sh -eu
# Proves a pg_dump archive restores, using a disposable postgres:18-alpine -- never point this at production.

dump_file="${1:?usage: restore-check.sh <path-to-pg_dump-archive>}"
[ -f "$dump_file" ] || { echo "No such file: $dump_file" >&2; exit 1; }

container="ahc-restore-check-$$"
check_db="restore_check"
check_user="restore_check"
check_password="restore-check-scratch-password"

cleanup() {
  docker rm -f "$container" >/dev/null 2>&1 || true
}
trap cleanup EXIT

echo "==> Starting disposable postgres:18-alpine ($container)"
docker run -d --name "$container" \
  -e POSTGRES_DB="$check_db" -e POSTGRES_USER="$check_user" -e POSTGRES_PASSWORD="$check_password" \
  postgres:18-alpine >/dev/null

echo "==> Waiting for it to accept connections"
i=0
until docker exec "$container" pg_isready -U "$check_user" >/dev/null 2>&1; do
  i=$((i + 1))
  if [ "$i" -ge 30 ]; then
    echo "Scratch postgres never became ready" >&2
    exit 1
  fi
  sleep 1
done

echo "==> Restoring $dump_file into the scratch database"
docker exec -i "$container" pg_restore -U "$check_user" -d "$check_db" --no-owner --no-privileges < "$dump_file"

echo "==> Checking Django's migration table landed with rows"
row_count=$(docker exec "$container" psql -U "$check_user" -d "$check_db" -tAc \
  "SELECT count(*) FROM django_migrations;")

if [ "${row_count:-0}" -gt 0 ]; then
  echo "OK: restored successfully, django_migrations has $row_count rows"
else
  echo "FAIL: django_migrations exists but is empty -- restore is suspect" >&2
  exit 1
fi
