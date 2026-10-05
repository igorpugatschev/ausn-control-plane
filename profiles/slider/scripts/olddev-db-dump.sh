#!/usr/bin/env bash
# Снять копию БД olddev (схема + данные) для локального стенда.
#
#   olddev-db-dump.sh <slider-autotests/.env> <out-dir>
#
# Результат в <out-dir>:
#   olddev-schema.sql        — схема (pg_dump --schema-only, 4 недоступные таблицы исключены)
#   olddev-schema-final.sql  — схема + stub пустой font_families (для FK fonts→font_families)
#   olddev-data.sql.gz       — данные (COPY через psycopg, sequence исключены)
#
# Почему не обычный pg_dump: PG18 pg_dump блокирует ВСЕ таблицы одним LOCK TABLE,
# а QA-пользователь не имеет SELECT на 4 таблицы (category, font_families,
# presentation_image_repair_status, transaction_tokens) и ни на одну sequence.
set -euo pipefail

ENV="${1:?usage: olddev-db-dump.sh <env> <out-dir>}"
OUT="${2:?usage: olddev-db-dump.sh <env> <out-dir>}"
ROOT="$(cd "$(dirname "$0")/../../.." && pwd)"          # ausn-control-plane
PY="$ROOT/.venv/Scripts/python.exe"
mkdir -p "$OUT"

# --- схема ---
PWFILE="$OUT/.pg.env"
PWD_VAL="$(grep -E '^DB_PASSWORD=' "$ENV" | head -1 | cut -d= -f2-)"
umask 077; printf 'PGPASSWORD=%s\n' "$PWD_VAL" > "$PWFILE"; unset PWD_VAL

DENY=(slider_web_test_db.category slider_web_test_db.font_families \
      slider_web_test_db.presentation_image_repair_status slider_web_test_db.transaction_tokens)
ARGS=(); for t in "${DENY[@]}"; do ARGS+=("--exclude-table=$t"); done

DB_HOST="$(grep -E '^DB_HOST=' "$ENV" | cut -d= -f2-)"
DB_PORT="$(grep -E '^DB_PORT=' "$ENV" | cut -d= -f2-)"
DB_USER="$(grep -E '^DB_USER=' "$ENV" | cut -d= -f2-)"
DB_NAME="$(grep -E '^DB_NAME=' "$ENV" | cut -d= -f2-)"

docker run --rm --env-file "$PWFILE" postgres:18 \
  pg_dump -h "$DB_HOST" -p "$DB_PORT" -U "$DB_USER" -d "$DB_NAME" \
    --schema=slider_web_test_db --no-owner --no-privileges --schema-only "${ARGS[@]}" \
  > "$OUT/olddev-schema.sql"
rm -f "$PWFILE"

# --- stub font_families для FK fonts→font_families (таблицу не отдают) ---
"$PY" - "$OUT/olddev-schema.sql" "$OUT/olddev-schema-final.sql" <<'PY'
import sys
src = open(sys.argv[1], encoding="utf-8").read()
stub = """
CREATE TABLE slider_web_test_db.font_families (
    id integer NOT NULL,
    name VARCHAR(150) NOT NULL,
    manufacturer TEXT, designer TEXT, license TEXT, license_url VARCHAR(500),
    copyright TEXT, trademark TEXT, description TEXT,
    created TIMESTAMP WITHOUT TIME ZONE NOT NULL,
    updated TIMESTAMP WITHOUT TIME ZONE NOT NULL,
    PRIMARY KEY (id)
);

"""
anchor = "CREATE SCHEMA slider_web_test_db;\n"
assert anchor in src, "anchor not found in schema dump"
open(sys.argv[2], "w", encoding="utf-8").write(src.replace(anchor, anchor + stub, 1))
print("wrote", sys.argv[2])
PY

# --- данные ---
"$PY" "$(dirname "$0")/olddev-dump-data.py" "$ENV" "$OUT/olddev-data.sql"
gzip -f "$OUT/olddev-data.sql"
echo "done: schema=$OUT/olddev-schema-final.sql  data=$OUT/olddev-data.sql.gz"
