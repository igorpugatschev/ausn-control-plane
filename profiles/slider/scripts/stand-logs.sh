#!/usr/bin/env bash
# Просмотр логов контейнеров локального canonical-стенда Slider.
#
#   stand-logs.sh list                 — сервисы и их статус
#   stand-logs.sh tail [svc...]        — последние строки (по умолчанию все app-сервисы)
#   stand-logs.sh follow [svc...]      — поток в реальном времени (Ctrl+C)
#   stand-logs.sh errors [svc...]      — только ошибки/трейсбеки/5xx (последние N)
#   stand-logs.sh requests [svc]       — только строки HTTP-запросов (с кодом)
#
# Опции:
#   -n N            сколько строк (tail: 120, errors: 400)
#   --since DUR     окно (например 30s, 10m, 1h)
#
# Сервисы: slider-flask, slider-web-auth, slider-dashboard, slider-landing,
#          slider-nginx, slider-pptx, slider-pptx-lb, slider-postgres,
#          slider-redis, slider-mongo  (по умолчанию — приложения без инфры).
set -uo pipefail

COMPOSE="/c/rocketscience/slider-web/compose-28128"
APP_SERVICES=(slider-flask slider-web-auth slider-dashboard slider-landing slider-nginx slider-pptx slider-pptx-lb)

compose() { ( cd "$COMPOSE" && docker compose -f compose/docker-compose.yml --env-file compose/.env "$@" ); }

ERR_RE='error|traceback|exception|critical|failed|fatal| 500 | 502 | 503 | 504 |unhandled|panic'
REQ_RE='"(GET|POST|PUT|PATCH|DELETE) |HTTP/1\.[01]" [0-9]{3}|"[A-Z]+ /[^ ]*" [0-9]{3}'

cmd="${1:-tail}"; shift || true
n=120; since=""
args=()
while [[ $# -gt 0 ]]; do
  case "$1" in
    -n) n="$2"; shift 2;;
    --since) since="$2"; shift 2;;
    *) args+=("$1"); shift;;
  esac
done
services=("${args[@]:-}"); [[ ${#services[@]} -eq 0 ]] && services=("${APP_SERVICES[@]}")

since_opt=(); [[ -n "$since" ]] && since_opt=(--since "$since")

case "$cmd" in
  list|ls)
    compose ps --format 'table {{.Service}}\t{{.Status}}\t{{.Ports}}'
    ;;
  follow|f|-f)
    echo ">>> follow: ${services[*]}  (Ctrl+C — выход)"
    compose logs -f --tail "$n" "${since_opt[@]}" "${services[@]}" 2>&1
    ;;
  errors|e)
    [[ "$n" == "120" ]] && n=400
    echo ">>> ошибки (${services[*]}), последние $n строк на сервис"
    compose logs --tail "$n" "${since_opt[@]}" "${services[@]}" 2>&1 | grep -iE "$ERR_RE" || echo "  (ошибок не найдено)"
    ;;
  requests|req)
    echo ">>> HTTP-запросы (${services[*]}), последние $n строк"
    compose logs --tail "$n" "${since_opt[@]}" "${services[@]}" 2>&1 | grep -E "$REQ_RE" || echo "  (запросов не найдено)"
    ;;
  tail|t|"")
    echo ">>> tail ${n} (${services[*]})"
    compose logs --tail "$n" "${since_opt[@]}" "${services[@]}" 2>&1
    ;;
  *)
    sed -n '2,20p' "$0"; exit 1
    ;;
esac
