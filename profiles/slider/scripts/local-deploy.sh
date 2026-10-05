#!/usr/bin/env bash
# Локальный деплой ветки/коммита задачи на canonical PG18-стенд
# (аналог editor-build-webhook.sh на olddev, но целиком локально).
#
# Использование:
#   local-deploy.sh <component> <ref> [--task <id>]
#   local-deploy.sh restore [<component>...]
#   local-deploy.sh status
#
# component: flask | landing | dashboard | pptx | pptx-nginx | nginx
# ref:       branch или полный/короткий SHA
#
# Механика:
#   - flask       — mountable: worktree + FLASK_SRC_HOST_PATH + restart (без пересборки)
#   - остальные   — worktree + re-point junction compose/src/<repo> + build.sh + recreate
#
# Ветки разработчиков не изменяются: всё в отдельных git worktree под .worktrees/.
set -uo pipefail

ROOT="/c/rocketscience/slider-web"
COMPOSE="$ROOT/compose-28128"
COMPOSE_DIR="$COMPOSE/compose"
SRC="$COMPOSE_DIR/src"
WORKTREES="$ROOT/.worktrees"
COMPOSE_ENV="$COMPOSE_DIR/.env"
declare -A REPO=(
  [flask]="flask-slider-webeditor"
  [landing]="slider-ai-frontend-landing"
  [dashboard]="slider-ai-dashboard-frontend"
  [pptx]="pptx-converter-service"
)
declare -A SERVICE=(
  [flask]="slider-flask"
  [landing]="slider-landing"
  [dashboard]="slider-dashboard"
  [pptx]="slider-pptx"
  [pptx-nginx]="slider-pptx-lb"
  [nginx]="slider-nginx"
)

log() { printf '%s\n' "$*"; }
die() { printf 'ERROR: %s\n' "$*" >&2; exit 1; }

win()  { cygpath -w "$1"; }   # backslashes — для cmd mklink
winf() { cygpath -m "$1"; }   # forward slashes — для .env / compose bind source

del_link() { # безопасно снять junction/symlink (не трогая target)
  [[ -e "$1" ]] || return 0
  cmd //c rmdir "$(win "$1")" >/dev/null 2>&1 || rm -rf "$1"
}

set_env_var() { # key value
  python - "$COMPOSE_ENV" "$1" "$2" <<'PY'
import sys, re
p, k, v = sys.argv[1], sys.argv[2], sys.argv[3]
t = open(p, encoding="utf-8").read()
pat = rf'(?m)^{re.escape(k)}=.*$'
if re.search(pat, t):
    t = re.sub(pat, f"{k}={v}", t)
else:
    t = t.rstrip("\n") + f"\n{k}={v}\n"
open(p, "w", encoding="utf-8", newline="\n").write(t)
PY
}

compose_recreate() { # service
  ( cd "$COMPOSE" && docker compose \
      -f compose/docker-compose.yml -f compose/docker-compose.local-dev.yml \
      --env-file compose/.env up -d --force-recreate "$1" ) >/dev/null 2>&1
  docker restart slider-nginx >/dev/null 2>&1 || true
}

ensure_worktree() { # repo ref path
  local repo="$1" ref="$2" path="$3"
  local main="$SRC/$repo"
  [[ -d "$main/.git" || -f "$main/.git" ]] || die "нет репозитория: $main"
  git -C "$main" fetch --quiet origin || true
  if [[ -e "$path" ]]; then
    git -C "$main" worktree remove --force "$path" >/dev/null 2>&1 || rm -rf "$path"
  fi
  mkdir -p "$(dirname "$path")"
  if [[ "$ref" =~ ^[0-9a-fA-F]{7,40}$ ]]; then
    git -C "$main" worktree add --quiet --detach "$path" "$ref" || die "worktree add $ref"
  else
    git -C "$main" worktree add --quiet --detach "$path" "origin/$ref" || die "worktree add origin/$ref"
  fi
}

flask_extras() { # path
  local p="$1"
  cat > "$p/project_setting.py" <<'EOF'
import os


class Settings_app():
    def __init__(self):
        self.mode_app = os.environ.get('CONFIG_MODE_APP', 'work_app')
        self.app_secret_key = os.environ.get(
            'SECRET_KEY', 'changeme_secret_key_min32chars__').encode()
        self.SLIDER_AI_SECRET_TOKEN = os.environ.get('SECRET_KEY_API', '')
        self.abs_folder_project = ''
        self.TerminalKey = ''
        self.password_Terminal = ''
        self.os_server = 'linux'


ACCESS_ADMIN_UPLOAD = []
EXCEPT_EMAIL_CORP = []
EOF
  for pair in editor-template editor-static; do
    local j="$p/templates/$pair" t="$p/frontend/$pair"
    [[ -e "$j" ]] && rm -rf "$j"
    cmd //c mklink //J "$(win "$j")" "$(win "$t")" >/dev/null 2>&1 || true
  done
}

receipt() { # component ref sha service
  local f="$ROOT/.worktrees/deploy-receipts.log"
  mkdir -p "$(dirname "$f")"
  printf '%s component=%s ref=%s sha=%s service=%s\n' \
    "$(date -u +%Y-%m-%dT%H:%M:%SZ)" "$1" "$2" "$3" "$4" | tee -a "$f"
}

cmd_deploy() { # component ref task
  local comp="$1" ref="$2" task="${3:-}"
  [[ -n "${SERVICE[$comp]:-}" ]] || die "unknown component: $comp"
  local slug="${task:-$(printf '%s' "$ref" | tr '/' '_')}"

  if [[ "$comp" == "nginx" || "$comp" == "pptx-nginx" ]]; then
    ( cd "$COMPOSE" && RUNTIME=docker bash compose/scripts/build.sh "$comp" ) || die "build $comp"
    compose_recreate "${SERVICE[$comp]}"
    receipt "$comp" "$ref" "$(git -C "$COMPOSE" rev-parse --short HEAD)" "${SERVICE[$comp]}"
    return 0
  fi

  local repo="${REPO[$comp]}"
  local wt="$WORKTREES/$slug/$repo"
  ensure_worktree "$repo" "$ref" "$wt"
  local sha; sha=$(git -C "$wt" rev-parse HEAD)

  if [[ "$comp" == "flask" ]]; then
    flask_extras "$wt"
    set_env_var FLASK_SRC_HOST_PATH "$(winf "$wt")"
    compose_recreate slider-flask
  else
    # re-point junction compose/src/<repo> -> worktree, then build image
    del_link "$SRC/$repo"
    cmd //c mklink //J "$(win "$SRC/$repo")" "$(win "$wt")" >/dev/null 2>&1 || die "junction $repo"
    ( cd "$COMPOSE" && RUNTIME=docker bash compose/scripts/build.sh "$comp" ) || die "build $comp"
    compose_recreate "${SERVICE[$comp]}"
  fi
  receipt "$comp" "$ref" "$sha" "${SERVICE[$comp]}"
}

cmd_restore() { # component...
  local comps=("$@")
  [[ ${#comps[@]} -eq 0 ]] && comps=(flask landing dashboard pptx)
  for comp in "${comps[@]}"; do
    local repo="${REPO[$comp]:-}"
    [[ -n "$repo" ]] || continue
    local main="$ROOT/$repo"
    if [[ "$comp" == "flask" ]]; then
      set_env_var FLASK_SRC_HOST_PATH "$(winf "$main")"
      compose_recreate slider-flask
    else
      del_link "$SRC/$repo"
      cmd //c mklink //J "$(win "$SRC/$repo")" "$(win "$main")" >/dev/null 2>&1 || true
      ( cd "$COMPOSE" && RUNTIME=docker bash compose/scripts/build.sh "$comp" ) >/dev/null 2>&1 || true
      compose_recreate "${SERVICE[$comp]}"
    fi
    log "restored $comp -> stage clone ($main)"
  done
}

cmd_status() {
  log "FLASK_SRC_HOST_PATH=$(grep -E '^FLASK_SRC_HOST_PATH=' "$COMPOSE_ENV" | cut -d= -f2-)"
  for c in flask landing dashboard pptx pptx-nginx nginx; do
    local n; n=$( cd "$COMPOSE" && docker compose -f compose/docker-compose.yml \
      --env-file compose/.env ps --status running -q "${SERVICE[$c]}" 2>/dev/null | grep -c . )
    printf '  %-12s -> running instances: %s\n' "$c" "${n:-0}"
  done
  log "worktrees:"; ls -1 "$WORKTREES" 2>/dev/null | sed 's/^/  /' || true
}

case "${1:-}" in
  restore) shift; cmd_restore "$@" ;;
  status)  cmd_status ;;
  ""|-h|--help) sed -n '2,20p' "$0"; exit 0 ;;
  *)       cmd_deploy "$1" "${2:-}" "$( [[ "${3:-}" == "--task" ]] && echo "${4:-}" )" ;;
esac
