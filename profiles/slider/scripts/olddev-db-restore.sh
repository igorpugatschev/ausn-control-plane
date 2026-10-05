#!/usr/bin/env bash
# Восстановить копию БД olddev в локальный canonical-стенд (PG18).
#
#   olddev-db-restore.sh <dump-dir> [container] [db] [dbuser] [schema]
#   по умолчанию: slider-postgres slider_web slider_user slider_web_test_db
#
# Шаги: DROP схем → схема (+ stub font_families) → данные (FK отключены в файле)
#       → setval sequence → search_path роли (web_auth не читает DB_SCHEMA).
set -euo pipefail

DUMP="${1:?usage: olddev-db-restore.sh <dump-dir> [container] [db] [user] [schema]}"
C="${2:-slider-postgres}"; DB="${3:-slider_web}"; U="${4:-slider_user}"; SCH="${5:-slider_web_test_db}"

echo "==> drop schemas"
docker exec -i "$C" psql -U "$U" -d "$DB" -v ON_ERROR_STOP=1 <<SQL
DROP SCHEMA IF EXISTS public CASCADE;
DROP SCHEMA IF EXISTS "$SCH" CASCADE;
SQL

echo "==> restore schema"
docker exec -i "$C" psql -U "$U" -d "$DB" -v ON_ERROR_STOP=1 < "$DUMP/olddev-schema-final.sql" >/dev/null

echo "==> restore data"
gunzip -c "$DUMP/olddev-data.sql.gz" | docker exec -i "$C" psql -U "$U" -d "$DB" -v ON_ERROR_STOP=1 >/dev/null

echo "==> setval sequences"
docker exec -i "$C" psql -U "$U" -d "$DB" -v ON_ERROR_STOP=1 <<SQL
DO \$\$
DECLARE r record; mx bigint;
BEGIN
  FOR r IN
    SELECT n.nspname AS sch, c.relname AS seq, t.relname AS tbl, a.attname AS col
    FROM pg_class c
    JOIN pg_namespace n ON n.oid=c.relnamespace
    JOIN pg_depend d ON d.objid=c.oid AND d.deptype='a'
    JOIN pg_class t ON t.oid=d.refobjid
    JOIN pg_attribute a ON a.attrelid=t.oid AND a.attnum=d.refobjsubid
    WHERE c.relkind='S' AND n.nspname='$SCH'
  LOOP
    EXECUTE format('SELECT max(%I) FROM %I.%I', r.col, r.sch, r.tbl) INTO mx;
    IF mx IS NOT NULL THEN
      EXECUTE format('SELECT setval(%L, %s, true)', r.sch||'.'||r.seq, mx);
    END IF;
  END LOOP;
END \$\$;
SQL

echo "==> role search_path (web_auth игнорирует DB_SCHEMA)"
docker exec -i "$C" psql -U "$U" -d "$DB" -v ON_ERROR_STOP=1 \
  -c "ALTER ROLE $U SET search_path TO $SCH, public;"

echo "==> verify"
docker exec "$C" psql -U "$U" -d "$DB" -t -A -c \
  "SELECT count(*) FROM information_schema.tables WHERE table_schema='$SCH';"
docker exec "$C" psql -U "$U" -d "$DB" -t -A -c \
  "SELECT count(*) FROM \"$SCH\".users;"
echo "restored."
