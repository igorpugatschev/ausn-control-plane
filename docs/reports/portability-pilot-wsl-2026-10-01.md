# Clean-clone pilot (изолированная WSL Ubuntu) — 2026-10-01

Цель: проверить, что репозиторий готов к переносу — свежий клон в отдельной среде (без наших `.local`,
`.venv`, `node_modules`, сгенерированных конфигов и коллекций SocratiCode) проходит инструкции и гейты.
Формат — по Фазе 8 `OPENCODE_PORTABILITY_OPTIMIZATION_PROMPT.md`. Верификация read-only; действия уровня
окружения (клоны/`npm ci`/`docker compose`) в этой среде не выполнялись как целевые.

## Среда

- WSL2 Ubuntu (kernel 5.15), пользователь `unix`, `/mnt/c` виден, свободно ~949 ГБ.
- Node: **Linux `node` отсутствует**; `npm` в PATH — Windows-интерполяция (`/mnt/c/Program Files/nodejs/npm`).
- Python 3.12.3; Docker CLI в Ubuntu **отсутствует** (интеграция Docker Desktop не включена).
- Сеть из WSL: `gitlab.com` → 301; corporate MCP `192.168.100.108:3002` → 406 (доступен);
  Qdrant `127.0.0.1:17333` → 200 (Docker Desktop порт виден); **Ollama `127.0.0.1:11434` → нет соединения**.

## Метод

Свежий клон control plane в Linux-ФС (`git clone /mnt/c/... /home/unix/ausn-pilot/ausn-control-plane`,
HEAD `a752a78`, dirty=0). Клон из локального пути, а не по HTTPS-remote: приватный репозиторий требует
токена, передавать секрет в WSL/логи нельзя → **независимая проверка авторизации remote не выполнялась**
(typed gap, см. ниже).

## Результаты

| Шаг | Результат |
|---|---|
| 1. Свежий клон без наших артефактов | ✓ HEAD `a752a78`, dirty=0 |
| 2. `requirements.txt` (README шаг 3) | ✗ **файла нет** — инструкция сломана |
| 3. `.venv` + `pip install pytest` | ✓ Python 3.12.3, pytest 9.1.1 (PyPI доступен) |
| 4. `tools/checks/validate_manifests.py` | ✓ `OK workspace`, `OK env`, `OK mcp` (stdlib) |
| 5. `pytest tools/checks/tests/test_validate_manifests.py` | ✓ 11 passed |
| 6. `npm ci --prefix tools/mcp-runtime` | ⚠ формально ok (через Windows-node интероп), `node_modules` создан |
| 7. `node scripts/bootstrap.mjs --check` | ✗ `node: команда не найдена` |
| 8. `codemap --docs --all --check` | ✗ control plane «УСТАРЕЛО — битые ссылки: 10»; qa-project «lock отсутствует» |
| 9. Соседние репозитории `../ausn` | ✗ отсутствуют (workspace не развёрнут) |

## Дефекты и пробелы (typed gaps)

| # | Что | Класс | Действие |
|---|---|---|---|
| D1 | README шаг 3 ссылается на отсутствующий `requirements.txt` | **дефект репозитория** | исправлено в этом же коммите: добавлен `requirements.txt` (pytest для тестов инструментов) |
| D2 | Linux `node` в WSL нет (только Windows-интероп `npm`) → `bootstrap` и Node-тесты не запускаются | среда целевой машины | prerequisite Node.js 22+ в инструкции; `bootstrap` даёт typed gap |
| D3 | Docker CLI в Ubuntu нет (интеграция Docker Desktop выключена) → `docker compose up` невозможен | среда | включить интеграцию или запускать compose на хосте |
| D4 | Ollama из WSL по `127.0.0.1:11434` недоступна (нативный Windows-сервис) | среда | адрес хоста/зеркальная сеть; иначе эмбеддинги недоступны |
| D5 | В свежем клоне **без соседнего `ausn-qa-project`** документный граф даёт **10 битых ссылок** (пример: `.agents/skills/ausn-api-contract-testing/SKILL.md:28 → tests/conftest.py`) | **дефект репозитория** (подтверждает п.13 плана) | инкремент 2: генератор должен различать отсутствующий внешний репозиторий (typed gap) и не писать заведомо неполную карту / не считать это ошибкой |
| D6 | `../ausn` не развёрнут | ожидаемо | выполняется `bootstrap --apply` на целевой машине |
| D7 | Клон по HTTPS-remote не проверялся (нет токена в среде) | внешний доступ | `BLOCKED_EXTERNAL_ACCESS` для авторизованного клона |

## Вердикт

**PARTIAL.** Репозиторный слой переносим: свежий клон в чистой Linux-среде разворачивает Python-окружение,
stdlib-валидатор и pytest-наборы инструментов проходят (11 passed). Полный путь
`clone → deps → MCP → index → first task` в этой среде **не пройден** из-за среды (Node/Docker/Ollama) и
двух дефектов репозитория (D1 исправлен, D5 — в инкремент 2). Основной вывод: остаточные пробелы —
инфраструктурные prerequisites целевой машины и корректная обработка отсутствующих внешних репозиториев.

## Следующие шаги

1. Инкремент 2: `bootstrap --apply`, рендер клиентских конфигов, runbook пилота, ревизия полноты
   (включая D5 — типизовать отсутствующий внешний репозиторий в документном графе).
2. На целевой машине: установить Node.js 22+, включить Docker/WSL-интеграцию или поднять compose на хосте,
   обеспечить доступ к Ollama; затем прогнать `bootstrap --check/--apply` и получить terminal PASS.
