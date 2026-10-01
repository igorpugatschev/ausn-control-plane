# Slider: разбор управляющей модели и план работы (второй писатель)

Источник: чтение `slider-web-control-plane` (15a55fb), `slider-qa-docs` (ddf0b4c),
`slider-autotests` (fdfe495) — клоны в `tmp/slider-read/` (read-only).

## Как управляются автотесты и документация

**slider-web-control-plane** — управляющий; клиент — Codex (межмодельное делегирование выключено).
- Agent layer `agents/slider-ai-qa/` (skills `slider-qa-loop`, `slider-test-design`); отдельный nested-контракт SliderDiagram.
- **Три отдельно запускаемых этапа**: `context-review` → `testing` → `stage-regression`; approvals не переносятся, сборка olddev и merge в stage — только по отдельной команде пользователя; статусы Bitrix агент не меняет.
- **Продуктовые ветки Редактора не создаются**; task-ветки/worktree — только в `slider-autotests`.
- **Жизненный цикл артефактов**: control plane не архив; временные отчёты — в ignored `.reports/`; gate очистки — docs/codexcli-artifact-lifecycle-policy.md; `finalize-control-plane-change.mjs` + серия `check-*` (agent-execution-policy, prompt-regression, codemap, secrets).
- **Секреты**: проектные — в `.env` проекта; отдельный vault Codex; права ≤600.
- Задачи — из карточки Bitrix; перед testing читается delta требований/комментариев/макетов.

**slider-qa-docs** — принятая командная QA-база (не agent-промпты, не task-отчёты).
- Разделы: onboarding, qa-strategy, test-basis, checklists, test-cases, bug-reproductions, traceability, gaps, knowledge.
- **Правило актуальности**: `freshness_status`, `source`, `last_verified`, `acceptance_gate` + связь с областью/автотестом/объяснённым manual gap; current обновляется только после ACCEPTED stage; номера задач — только в provenance.
- Карта связей — trio `docs/codemap/codemap.{html,json,lock}` общим генератором control plane (docs-профиль: узлы по разделам, рёбра только из доказуемых связей).

**slider-autotests** — переносимый pytest-фреймворк (Python 3.12, pytest, HTTPX, Pydantic v2, Allure, psycopg read-only, Playwright UI smoke, k6).
- **Два набора**: `framework_tests/` (самопроверки; CI на push в `main`) и `tests/` (продукт, включая olddev).
- Маркеры `ai`/`ai_transport`/`ai_quality`; MCP-находка не покрытие, пока не станет pytest/manual-only/blocked.
- `pyproject.toml` (диапазоны) + `constraints.txt` (снимок); свой генератор codemap.

## Роль и границы

- Мы — **второй писатель**: управляем автотестами (`slider-autotests`) и документацией (`slider-qa-docs`), ориентир — единая цель: качество Slider AI. Опыт `slider-web-control-plane` перенимаем, но ведём свой контур (`profiles/slider/`), не мешая первому писателю.
- Ничего Slider-специфичного не попадает в ядро control plane; все данные и доки — в `profiles/slider/`.

## Что принимаем как есть

1. Разделение артефактов: control plane ≠ архив; исполняемое покрытие — `slider-autotests`; принятая база — `slider-qa-docs`; временное — `.reports/` (ignored).
2. Правило `freshness_status/source/last_verified/acceptance_gate` в каждом рабочем документе QA-базы.
3. Два набора тестов и запрет считать MCP-находку покрытием.
4. Ветки: в продуктовых репозиториях Редактора не создавать; task-ветки — только в `slider-autotests`.
5. Тройка codemap в `slider-qa-docs`/`slider-autotests` и её проверка перед коммитом.

## Что у нас иначе (и требует решения)

1. **Клиент**: у нас opencode (первый писатель — Codex). Нужно решить, переносим ли их `agents/slider-ai-qa`-промпты в наш opencode-контур или адаптируем их rules/skills.
2. **Генератор codemap**: у них общий `scripts/codemap-generate.mjs` в control plane; у нас — свой `tools/codemap/generate.py`. Для Slider-репозиториев надо выбрать один генератор, чтобы trio был совместим.
3. **Имя продукта**: в переписке звучит `slider-web-autotests`, фактически репозиторий — `pugachevigor/slider-autotests` (в реестре так и записано).
4. **Bitrix-интеграция**: у них read-only intake из Bitrix; у нас — Jira/AUSN-остатки; для Slider нужно решить источник задач (Bitrix?).
5. **Два писателя**: `slider-qa-docs` отмечен writable — нужен регламент (pull перед правкой, без force-push, ветки/MR?).

## Ближайшие шаги

1. Дочитать краткие разделы `docs/slider-ai/*` control plane (agent-testing-architecture, portable-paths-contract, gitlab-mcp-runbook).
2. Зафиксировать решения по 5 пунктам выше и оформить их в `profiles/slider/` (не в ядре).
3. Доклонировать оставшиеся продуктовые репозитории (`bootstrap --apply` для slider) и настроить индексацию.
