#!/usr/bin/env bash
# One-time, read-only copy of the hosted OMI data into a project's database.
#
#   deploy/migrate_from_supabase.sh <project> <workdir>
#
# The source is SOURCE_DATABASE_URL in the environment or, when that is unset,
# SUPABASE_SOURCE_DATABASE_URL from ~/.config/vendocasa/secrets.env. It never
# appears on a command line. The project's db service must be running, on an
# empty volume. <workdir> (mode 0700) keeps the source's schema, counts,
# checksums and data dump, and the reports.
#
# Against the source, everything runs in read-only transactions:
#   1. the definition of schema omi, and the schema that holds PostGIS;
#   2. each table's row count, zones and quotations also by semester;
#   3. each table's checksum: an order-independent sum of per-row md5 values
#      over the source's columns, in the UTC time zone;
#   4. a data-only dump of omi.zones, omi.quotations and omi.transactions, with
#      their sequences.
# On the project's database:
#   5. migrate to 0001, the baseline whose tables match the legacy schema, and
#      stop before loading if the source's columns differ from it;
#   6. load the data in one transaction, then compare counts and checksums
#      with the source's, and stop on any difference;
#   7. migrate to head: migration 0005's backfill validates each semester;
#   8. scripts/validate_semesters.py, read-only, for the report.
set -euo pipefail

here=$(cd "$(dirname "$0")" && pwd)
project=${1:?usage: deploy/migrate_from_supabase.sh <project> <workdir>}
work=${2:?usage: deploy/migrate_from_supabase.sh <project> <workdir>}
# The dump client: postgres:17.4, the image nql8r already uses on this server.
client=postgres@sha256:304ab813518754228f9f792f79d6da36359b82d8ecf418096c636725f8c930ad
tables=(omi.zones omi.quotations omi.transactions)

umask 077
mkdir -p "$work"
chmod 700 "$work"
log() { echo "migrate_from_supabase.sh $(date -u +%FT%TZ): $*"; }

if [ -z "${SOURCE_DATABASE_URL:-}" ]; then
  SOURCE_DATABASE_URL=$(sed -n 's/^SUPABASE_SOURCE_DATABASE_URL=//p' "$HOME/.config/vendocasa/secrets.env" 2>/dev/null || true)
fi
if [ -z "$SOURCE_DATABASE_URL" ]; then
  echo "migrate_from_supabase.sh: no source database URL" >&2
  exit 2
fi
export SOURCE_DATABASE_URL

# psql or pg_dump against the source, from the client image, with the URL
# passed through the environment.
source_run() { docker run --rm -i --network host -e SOURCE_DATABASE_URL "$client" "$@"; }
source_sql() {
  source_run sh -c 'psql "$SOURCE_DATABASE_URL" -X -v ON_ERROR_STOP=1 -At -F " " -q' <<SQL
BEGIN READ ONLY;
SET TIME ZONE 'UTC';
$1
COMMIT;
SQL
}
target_sql() { "$here/compose.sh" "$project" exec -T db psql -U supabase_admin -d postgres -X -v ON_ERROR_STOP=1 -At -F ' ' -q "$@"; }
backend() { "$here/compose.sh" "$project" run --rm --no-deps -T backend "$@"; }

columns_sql() {
  # One line per column of the three tables: table, position, name, type.
  echo "SELECT table_schema || '.' || table_name, ordinal_position, column_name, udt_name FROM information_schema.columns WHERE table_schema = 'omi' AND table_name IN ('zones', 'quotations', 'transactions') ORDER BY 1, 2;"
}

checksum_sql() {
  # $1: table; $2: comma-separated column list.
  echo "SELECT '$1', count(*), coalesce(sum(('x' || substr(md5(t::text), 1, 15))::bit(60)::bigint), 0) FROM (SELECT $2 FROM $1) AS t;"
}

log "source: schema, PostGIS and columns"
source_run sh -c 'pg_dump "$SOURCE_DATABASE_URL" --schema-only --schema=omi --no-owner --no-privileges' > "$work/source-omi-schema.sql"
source_sql "SELECT extname, extnamespace::regnamespace, extversion FROM pg_extension WHERE extname = 'postgis';" > "$work/source-postgis.txt"
source_sql "$(columns_sql)" > "$work/source-columns.txt"
cat "$work/source-postgis.txt"

log "source: counts and checksums"
{
  for table in "${tables[@]}"; do
    cols=$(awk -v t="$table" '$1 == t {print $3}' "$work/source-columns.txt" | paste -sd,)
    checksum_sql "$table" "$cols"
  done
  echo "SELECT 'zones:' || semester, count(*), 0 FROM omi.zones GROUP BY semester ORDER BY semester;"
  echo "SELECT 'quotations:' || semester, count(*), 0 FROM omi.quotations GROUP BY semester ORDER BY semester;"
} > "$work/checksums.sql"
source_sql "$(cat "$work/checksums.sql")" > "$work/source-checksums.txt"
cat "$work/source-checksums.txt"

log "source: data dump"
source_run sh -c 'pg_dump "$SOURCE_DATABASE_URL" --data-only --table=omi.zones --table=omi.quotations --table=omi.transactions --no-owner --no-privileges' > "$work/source-data.sql"
log "dump: $(du -h "$work/source-data.sql" | cut -f1)"

log "target: migrate to the baseline"
existing=$(target_sql -c "SELECT count(*) FROM information_schema.tables WHERE table_schema = 'omi'")
if [ "$existing" != "0" ]; then
  echo "migrate_from_supabase.sh: the target already has omi tables; it must start empty" >&2
  exit 3
fi
backend alembic upgrade 0001
target_sql -c "$(columns_sql)" > "$work/target-columns.txt"
if ! diff -u "$work/source-columns.txt" "$work/target-columns.txt" > "$work/columns.diff"; then
  log "the source's columns differ from the baseline; nothing was loaded"
  cat "$work/columns.diff"
  exit 5
fi

log "target: load in one transaction"
target_sql -1 < "$work/source-data.sql"
# Through standard input: psql -c would print only the last statement's result.
{ echo "SET TIME ZONE 'UTC';"; cat "$work/checksums.sql"; } | target_sql > "$work/target-checksums.txt"
if ! diff -u "$work/source-checksums.txt" "$work/target-checksums.txt"; then
  log "counts or checksums differ from the source's"
  exit 6
fi
log "counts and checksums equal the source's"

log "target: migrate to head (the backfill validates each semester)"
backend alembic upgrade head 2>&1 | tee "$work/backfill.log"
backend python -m scripts.validate_semesters 2>&1 | tee "$work/validation.txt"
log "done"
