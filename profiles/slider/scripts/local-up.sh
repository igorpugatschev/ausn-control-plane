#!/usr/bin/env bash
# local-up.sh — воспроизводимый подъём локального стенда Slider (canonical PG18 + QA-оверлей).
#
# Цель: локально в Docker поднимается решение как на olddev:
#   infra (postgres/redis/mongo) → данные olddev-копии → статика (static + slider-static + fonts)
#   → flask (mountable src) + web-auth + dashboard + landing + pptx + nginx + dozzle.
#
# Идемпотентен: повторный запуск ничего не ломает; недостающее доустанавливает.
# Самолечение: uwsgi-flask импортирует приложение при старте воркера и при неготовом
# postgres навсегда падает ("no python application found", 500) — скрипт проверяет
# health flask и перезапускает контейнер до успеха.
#
# Использование:
#   local-up.sh                 # подъём; БД восстанавливается только если пуста
#   local-up.sh --with-db       # принудительно пересоздать БД из дампа olddev
#   local-up.sh --skip-db       # не трогать БД вообще
#   local-up.sh --no-smoke      # без HTTP/БД проверок
#
# Переменные:
#   DUMP_DIR — каталог дампа olddev (olddev-schema-final.sql + olddev-data.sql.gz),
#              по умолчанию <control-plane>/tmp
#
# ВАЖНО (Windows): постгрес на этой машине работает на bind-маунте compose/data/postgres.
# Канонический `make up` на Git Bash автодетектит named-тома (compose/data/postgres будет
# проигнорирован -> ПУСТАЯ БД). Этот скрипт вызывает compose напрямую, без dbvolumes-оверрайда.
set -uo pipefail

ROOT="/c/rocketscience/slider-web/compose-28128"
CP="/c/rocketscience/ausn-control-plane"
ENV_FILE="$ROOT/compose/.env"
DUMP_DIR="${DUMP_DIR:-$CP/tmp}"
CONTAINER="slider-postgres"; DB="slider_web"; DBUSER="slider_user"; SCHEMA="slider_web_test_db"

WITH_DB=0; SKIP_DB=0; SMOKE=1
for a in "$@"; do
  case "$a" in
    --with-db) WITH_DB=1 ;;
    --skip-db) SKIP_DB=1 ;;
    --no-smoke) SMOKE=0 ;;
    *) echo "unknown arg: $a"; exit 2 ;;
  esac
done

say() { printf '%s\n' "== $*"; }
die() { printf 'ERROR: %s\n' "$*" >&2; exit 1; }

COMPOSE() {
  docker compose \
    -f "$ROOT/compose/docker-compose.yml" \
    -f "$ROOT/compose/docker-compose.local-dev.yml" \
    -f "$ROOT/compose/docker-compose.observability.yml" \
    --env-file "$ENV_FILE" "$@"
}

env_val() { grep -E "^$1=" "$ENV_FILE" | head -1 | cut -d= -f2-; }

# --- 0. Preflight -------------------------------------------------------------
docker ps >/dev/null 2>&1 || die "docker недоступен"
[[ -f "$ENV_FILE" ]] || die "нет $ENV_FILE (сначала make init-env / скопируйте настроенный .env)"
FLASK_SRC=$(env_val FLASK_SRC_HOST_PATH)
[[ -n "$FLASK_SRC" && -d "$FLASK_SRC" ]] || die "FLASK_SRC_HOST_PATH не задан или каталога нет: '$FLASK_SRC'"
DATA_STATIC="$ROOT/compose/$(env_val DATA_STATIC)"
DATA_SLIDER="$ROOT/compose/$(env_val DATA_SLIDER_STATIC)"
say "стек: $ROOT"
say "flask src: $FLASK_SRC"

# --- 1. Каталоги данных (аналог make data-dirs) --------------------------------
while IFS= read -r p; do
  [[ -n "$p" ]] && mkdir -p "$ROOT/compose/$p"
done < <(grep -E '^DATA_[A-Z_]+=' "$ENV_FILE" | cut -d= -f2-)
chmod 0777 "$ROOT/compose/$(env_val DATA_FLASK_LOGS)" 2>/dev/null || true

# --- 2. Статика (идемпотентно) --------------------------------------------------
if [[ -d "$DATA_STATIC/cloud" ]]; then
  say "static: уже распакован ($DATA_STATIC/cloud)"
else
  say "static: распаковка static.tar.gz (~2.5 ГБ, долго)"
  tar -xzf "$ROOT/compose/init/static.tar.gz" -C "$DATA_STATIC" --strip-components=1
fi

if [[ -d "$DATA_SLIDER" && -n "$(ls -A "$DATA_SLIDER" 2>/dev/null)" ]]; then
  say "slider-static: уже распакован ($DATA_SLIDER)"
else
  say "slider-static: распаковка slider-static.tar.gz"
  mkdir -p "$DATA_SLIDER"
  tar -xzf "$ROOT/compose/init/slider-static.tar.gz" -C "$DATA_SLIDER" --strip-components=1
fi

if [[ -d "$DATA_STATIC/cloud/fonts" ]]; then
  say "fonts: уже распакованы ($DATA_STATIC/cloud/fonts)"
else
  say "fonts: распаковка fonts.tar.gz -> cloud/fonts"
  tar -xzf "$ROOT/compose/init/fonts.tar.gz" -C "$DATA_STATIC/cloud"
fi

# --- 3. Infra ------------------------------------------------------------------
say "infra: postgres/redis/mongo up"
COMPOSE --profile infra up -d slider-postgres slider-redis slider-mongo || die "infra up"
# Ждём ПОЛНОЙ готовности: pg_isready может пройти раньше конца recovery.
db_ok=0
for i in $(seq 1 90); do
  if docker exec "$CONTAINER" psql -U "$DBUSER" -d "$DB" -t -A -c "SELECT 1;" 2>/dev/null | grep -q 1; then
    db_ok=1; say "postgres: ready (select 1 ok, итерация $i)"; break
  fi
  sleep 2
done
[[ "$db_ok" == "1" ]] || die "postgres не готов за 180 c"

# --- 4. БД ---------------------------------------------------------------------
tables=$(docker exec "$CONTAINER" psql -U "$DBUSER" -d "$DB" -t -A -c \
  "SELECT count(*) FROM information_schema.tables WHERE table_schema='$SCHEMA';" 2>/dev/null || echo 0)
if [[ "$WITH_DB" == "1" ]]; then
  say "db: принудительное восстановление из $DUMP_DIR"
  bash "$CP/profiles/slider/scripts/olddev-db-restore.sh" "$DUMP_DIR" "$CONTAINER" "$DB" "$DBUSER" "$SCHEMA"
elif [[ "$SKIP_DB" == "1" ]]; then
  say "db: пропущено (--skip-db); таблиц в $SCHEMA: $tables"
elif [[ "${tables:-0}" -lt 70 ]]; then
  say "db: схема $SCHEMA пуста/неполна ($tables таблиц) — восстановление из $DUMP_DIR"
  bash "$CP/profiles/slider/scripts/olddev-db-restore.sh" "$DUMP_DIR" "$CONTAINER" "$DB" "$DBUSER" "$SCHEMA"
else
  say "db: схема $SCHEMA на месте ($tables таблиц) — пропускаю"
fi

# --- 5. Полный стек -------------------------------------------------------------
say "стек: up -d (все сервисы, профиль infra)"
COMPOSE --profile infra up -d || die "stack up"
docker restart slider-nginx >/dev/null 2>&1 || true

# --- 6. Health-gate flask (самолечение uwsgi "no app loaded") --------------------
# Один 200 не гарантирует здоровье: uwsgi держит пул воркеров, и если часть воркеров
# не смогла импортировать приложение (гонка create_all / неготовый postgres на старте),
# запросы падают на них intermittently (round-robin). Поэтому 5 проб подряд.
flask_healthy=0
for attempt in 1 2 3; do
  ok=1
  for probe in 1 2 3 4 5; do
    sleep 2
    code=$(curl -s -o /dev/null -w '%{http_code}' "http://localhost:8080/dashboard/edit_pres?presentation_id=1" 2>/dev/null || echo 000)
    if [[ "$code" != "200" ]]; then ok=0; say "flask: проба $probe -> $code (попытка $attempt) — рестарт контейнера"; docker restart slider-flask >/dev/null 2>&1 || true; break; fi
  done
  if [[ "$ok" == "1" ]]; then flask_healthy=1; say "flask: healthy (5/5 проб, попытка $attempt)"; break; fi
done
[[ "$flask_healthy" == "1" ]] || die "flask не поднялся за 3 попытки по 5 проб (см. docker logs slider-flask)"

# --- 7. Проверки -----------------------------------------------------------------
fail=0
check_http() { # url expect
  code=$(curl -s -o /dev/null -w '%{http_code}' "$1" 2>/dev/null || echo 000)
  if [[ "$code" == "$2" ]]; then say "  OK  $code $1"; else say "  FAIL $code (ожидался $2) $1"; fail=1; fi
}
tables=$(docker exec "$CONTAINER" psql -U "$DBUSER" -d "$DB" -t -A -c \
  "SELECT count(*) FROM information_schema.tables WHERE table_schema='$SCHEMA';" 2>/dev/null || echo 0)
users=$(docker exec "$CONTAINER" psql -U "$DBUSER" -d "$DB" -t -A -c \
  "SELECT count(*) FROM \"$SCHEMA\".users;" 2>/dev/null || echo 0)
giga=$(grep -c -F "GigaChat-2" "$FLASK_SRC/frontend/editor-static/assets/index.js" 2>/dev/null || echo 0)

if [[ "$SMOKE" == "1" ]]; then
  say "smoke:"
  check_http "http://localhost:8080/" 200
  check_http "http://localhost:8080/auth/login" 200
  check_http "http://localhost:8080/dashboard/edit_pres?presentation_id=1" 200
  check_http "http://localhost:8080/frontend/editor-static/assets/index.js" 200
  [[ -d "$DATA_STATIC/cloud/fonts/1" ]] && say "  OK  fonts: cloud/fonts на месте" || { say "  WARN fonts: cloud/fonts нет"; }
  [[ -n "$(ls -A "$DATA_SLIDER" 2>/dev/null)" ]] && say "  OK  slider-static: на месте" || { say "  WARN slider-static пуст"; }
  [[ "${tables:-0}" -ge 70 ]] && say "  OK  db: $tables таблиц в $SCHEMA, users=$users" || { say "  FAIL db: $tables таблиц, users=$users"; fail=1; }
  [[ "${giga:-0}" -gt 0 ]] && say "  OK  editor: GigaChat-2 в бандле (строк: $giga)" || { say "  FAIL editor: GigaChat-2 не найден в бандле"; fail=1; }
fi

if [[ "$fail" == "0" ]]; then
  say "стенд готов: http://localhost:8080"
  say "тесты: bash $CP/tmp/run_28836.sh local"
else
  die "есть неудачные проверки (см. FAIL выше)"
fi
