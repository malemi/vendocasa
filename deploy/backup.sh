#!/usr/bin/env bash
# Dumps of a VendoCasa project's database, and their restore test.
#
#   deploy/backup.sh <project> daily        schemas app, auth and omi, without the
#                                           data of omi.zones, omi.quotations and
#                                           omi.semester_import; kept 14 days
#   deploy/backup.sh <project> on-change    the data of omi.zones, omi.quotations
#                                           and omi.semester_import, after the first
#                                           restore and after each import; the
#                                           previous ones go once this one succeeds
#   deploy/backup.sh <project> restore-test rebuild a scratch database from the
#                                           latest of each, and compare every
#                                           table's row count in app, auth and omi
#
# pg_dump runs inside the db container as the database's superuser, and the
# dump reaches the host through standard output. Dumps go to
# BACKUP_DIR/<project> (~/backups/vendocasa by default), mode 0600. A dump
# refuses to start below BACKUP_FLOOR_GB (3) of free disk, and exits with 4.
set -euo pipefail

here=$(cd "$(dirname "$0")" && pwd)
project=${1:?usage: deploy/backup.sh <project> daily|on-change|restore-test}
mode=${2:?usage: deploy/backup.sh <project> daily|on-change|restore-test}
dir="${BACKUP_DIR:-$HOME/backups/vendocasa}/$project"
floor_gb=${BACKUP_FLOOR_GB:-3}
umask 077
mkdir -p "$dir"

compose() { "$here/compose.sh" "$project" "$@"; }
# In bytes: `df -BG` rounds up, and would pass the floor with up to 1 GiB less.
free_bytes() { df -B1 --output=avail "$dir" | tail -1 | tr -dc '0-9'; }
gib() { awk -v b="$1" 'BEGIN { printf "%.2f GiB", b / 1073741824 }'; }
log() { echo "backup.sh $(date -u +%FT%TZ) $project $mode: $*" >&2; }

count_sql="SELECT table_schema || '.' || table_name, (xpath('/row/c/text()', query_to_xml(format('SELECT count(*) AS c FROM %I.%I', table_schema, table_name), false, true, '')))[1]::text FROM information_schema.tables WHERE table_schema IN ('app', 'auth', 'omi') AND table_type = 'BASE TABLE' ORDER BY 1"

dump() {
  local kind=$1
  shift
  local free
  free=$(free_bytes)
  if [ "$free" -lt $((floor_gb * 1073741824)) ]; then
    log "refusing: $(gib "$free") free, below the ${floor_gb} GiB floor"
    exit 4
  fi
  local stamp target partial
  stamp=$(date -u +%Y%m%dT%H%M%SZ)
  target="$dir/$kind-$stamp.dump"
  partial="$dir/.$kind-$stamp.partial"
  compose exec -T db pg_dump -U supabase_admin -d postgres -Fc "$@" > "$partial"
  mv "$partial" "$target"
  log "wrote $(basename "$target"), $(du -h "$target" | cut -f1); free disk $(gib "$free") before"
  echo "$target"
}

case "$mode" in
  daily)
    dump daily --schema=app --schema=auth --schema=omi \
      --exclude-table-data=omi.zones --exclude-table-data=omi.quotations \
      --exclude-table-data=omi.semester_import > /dev/null
    find "$dir" -maxdepth 1 -name 'daily-*.dump' -mtime +14 -print -delete | sed 's/^/removed /'
    ;;
  on-change)
    newest=$(dump on-change --data-only --table=omi.zones --table=omi.quotations --table=omi.semester_import | tail -1)
    find "$dir" -maxdepth 1 -name 'on-change-*.dump' ! -path "$newest" -print -delete | sed 's/^/removed /'
    ;;
  restore-test)
    daily=$(ls -1 "$dir"/daily-*.dump 2>/dev/null | tail -1)
    change=$(ls -1 "$dir"/on-change-*.dump 2>/dev/null | tail -1)
    if [ -z "$daily" ] || [ -z "$change" ]; then
      log "needs one daily and one on-change dump in $dir"
      exit 2
    fi
    image=$(compose images -q db | head -1)
    postgis_schema=$(compose exec -T db psql -U supabase_admin -d postgres -AtX -c "SELECT extnamespace::regnamespace FROM pg_extension WHERE extname = 'postgis'")
    scratch="vendocasa-restore-test-$$"
    log "restoring $(basename "$daily") and $(basename "$change") into $scratch"
    docker run -d --rm --name "$scratch" --network none -e POSTGRES_PASSWORD=restore-test "$image" > /dev/null
    trap 'docker stop "$scratch" > /dev/null 2>&1 || true' EXIT
    for _ in $(seq 1 60); do
      if docker exec "$scratch" pg_isready -U postgres -h localhost > /dev/null 2>&1; then break; fi
      sleep 2
    done
    # The restore database starts from template0: the image's own init fills
    # `postgres` with an Auth skeleton that the dump's auth schema would hit.
    docker exec -i "$scratch" psql -U supabase_admin -d postgres -v ON_ERROR_STOP=1 -qX <<SQL
CREATE DATABASE restore_test TEMPLATE template0;
\c restore_test
CREATE SCHEMA IF NOT EXISTS extensions;
CREATE EXTENSION IF NOT EXISTS "uuid-ossp" SCHEMA extensions;
CREATE EXTENSION IF NOT EXISTS pgcrypto SCHEMA extensions;
CREATE SCHEMA IF NOT EXISTS ${postgis_schema};
CREATE EXTENSION IF NOT EXISTS postgis SCHEMA ${postgis_schema};
SQL
    docker exec -i "$scratch" pg_restore -U supabase_admin -d restore_test --exit-on-error < "$daily"
    docker exec -i "$scratch" pg_restore -U supabase_admin -d restore_test --data-only --exit-on-error < "$change"
    compose exec -T db psql -U supabase_admin -d postgres -AtX -F ' ' -c "$count_sql" > "$dir/.counts-production"
    docker exec "$scratch" psql -U supabase_admin -d restore_test -AtX -F ' ' -c "$count_sql" > "$dir/.counts-restored"
    if diff -u "$dir/.counts-production" "$dir/.counts-restored"; then
      log "row counts equal in $(wc -l < "$dir/.counts-restored") tables"
      sed 's/^/  /' "$dir/.counts-restored"
      rm -f "$dir/.counts-production" "$dir/.counts-restored"
    else
      log "row counts differ"
      exit 1
    fi
    ;;
  *)
    echo "backup.sh: unknown mode $mode" >&2
    exit 2
    ;;
esac
