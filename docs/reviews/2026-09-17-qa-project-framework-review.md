# Ревизия каркаса ausn-qa-project

Дата: 2026-09-17. Ревизия performed на коммите `69022bd` (`main`, синхронизирован с origin).
Проверки выполнялись локально в `.venv` проекта (ruff 0.16.6, mypy, pytest); статус CI —
через GitLab API. Это срез состояния, а не приговор фреймворку.

## Общая оценка

Каркас зрелый и рабочий: слои `unit`/`static` (274 теста) зелёные за ~7 с, mypy чист
(223 файла), `--strict-markers`, развитая конфигурация ruff с per-file ignores, env_discovery
для `.env`, защита от секретов в Postman-окружениях (static-тест), Windows-safe логирование.

## Блокер: quality gate (CI)

Последний pipeline на `main` (2828639662) — failed. Локальный прогон
`scripts/tools/audit_gate.py --full`: **6/11, упали 5 проверок**.

| # | Проверка | Факт | Комментарий |
|---|---|---|---|
| 1 | `ruff format --check` | **153 файла** требуют переформатирования | Массовое; вероятная причина — дрейф версии ruff |
| 2 | `ruff check` | 22 ошибки: 14× PLR0917, 5× S106, 2× RUF036, 1× I001 | PLR0917 — «preview»-правило новых ruff; было 34 на снимке 2026-09-08 |
| 3 | audit: text encoding | падает | детали собрать при фиксе |
| 4 | audit: module docstrings | падает | где именно — собрать при фиксе |
| 5 | audit: mixed HTTP statuses | падает | риск «перmissive-проверок», нужно ревью правил |

OK: mypy, pytest collect-only, pytest unit/static, no mojibake, no legacy Postman,
no permissive 500, no secrets в Postman-окружениях.

## Корневые причины и риски

1. **Неп pinned инструменты.** `requirements.txt` полностью плавающий (`ruff>=0.1.9` и т.д.),
   lock-файла нет. CI ставит свежие версии → правила/формат меняются под ногами → gate
   ломается без изменений кода. PLR0917 в новых ruff — наглядный пример.
2. **Мёртвые зависимости.** `fastapi`+`uvicorn` в requirements, но `web_ui/` удалён в v2.2.0.
   Плюс двойной HTTP-стек (`requests` + `httpx`) — проверить фактическое использование.
3. **Док-дрейф.** README v2.3.0 описывает другой `.gitlab-ci.yml` и структуру `tests/`
   (без `unit/`/`static/`). `AGENTS.md` репозитория указывает на устаревший
   `C:\Users\igorp\CodexCLI` вместо `ausn-control-plane`.
4. **Легаси-дефолты.** `.env.example` ссылается на прежний контур `192.168.20.18`
   (известное ограничение из docs/ausn-context/test-automation-assets.md).
5. S106 (hardcoded-password-func-arg) в тестах — при фиксе проследить, чтобы реальные
   токены не попали в коммит; использовать синтетические значения.

## Рекомендованный порядок работ

- **P1. Восстановить quality gate** — ✅ выполнено 2026-09-17, коммиты `b396313`…`12145da`, pipeline 2856901564 success.
- **P2. Контекст-дрейф** — ✅ выполнено 2026-09-17, коммит `a4fbd55`.
- **P3. Гигиена зависимостей** — не начато: убрать/обосновать fastapi+uvicorn, свести HTTP-стек к httpx.
