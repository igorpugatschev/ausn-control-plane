# Промт для оптимизации переносимости ausn-control-plane

Ты управляешь репозиторием ausn-control-plane через OpenCode. Проведи evidence-led ревизию и реализуй улучшения, которые превращают текущую документированную настройку в воспроизводимый путь:

    clone → workspace bootstrap → dependencies → MCP install/configure
    → SocratiCode full index → capability check → first QA task

Работай до проверяемого результата. Не ограничивайся планом или редактурой README. Перед изменениями прочитай AGENTS.md, PROJECT_STATUS.md, README.md, REPOSITORIES.md, docs/mcp.md, docs/socraticode.md, актуальные skills и user prompts. Используй SocratiCode первым; dot-контент исследуй через context artifacts. Зафиксируй Git SHA и состояние индекса.

## Исходная сравнительная оценка

Сохрани сильные стороны проекта:

- contract-first QA loop, предметные skills и готовые user prompts;
- богатый набор корпоративных MCP и явные write boundaries;
- относительную модель расположения продуктовых репозиториев;
- SocratiCode для кода и context artifacts для Markdown/dot-контента;
- codemap и docgraph управляющего слоя;
- ретроспективы с происхождением правил;
- разделение control plane и ausn-qa-project.

Исправь подтверждённые системные пробелы:

1. README не проводит нового пользователя через полный clean-clone путь и содержит сессионно-зависимую команду запуска OpenCode.
2. Нет единого bootstrap-командного интерфейса с режимами plan/check/apply, итоговым машинночитаемым отчётом и безопасным повторным запуском.
3. Один MCP-набор вручную продублирован в .mcp.json, .codex/config.toml, .vscode/mcp.json и .opencode/opencode.jsonc; drift между клиентами не обнаруживается автоматическим gate.
4. Нет нейтрального machine-readable manifest репозиториев и их относительного размещения, из которого bootstrap может проверить или клонировать нужный workspace без абсолютных путей конкретного ПК.
5. .env.example намеренно отсутствует, поэтому невозможно автоматически проверить полный набор имён переменных без раскрытия значений.
6. Нет одной команды, которая устанавливает MCP runtime, валидирует client adapter, запускает разрешённую инфраструктуру SocratiCode, последовательно индексирует все нужные репозитории и дожидается terminal readiness.
7. Codemap генерируется хорошим собственным генератором, но финальная регенерация перед commit и read-only pre-commit check не обеспечены единым финализатором.
8. Правила в основном Markdown-based; мало исполняемых schema/validator gates, которые доказывают согласованность skills, prompts, client adapters и MCP.
9. Ретроспектива богата уроками, но процесс самообучения не измеряет эффект изменения навыка: вмешательства пользователя, false-positive failures, recovery success, time-to-first-evidence и предотвращённые ошибки.
10. PROJECT_STATUS.md, task reports, evidence и retrospectives растут как архив истории. Нужен lifecycle: Git хранит историю, active handoff содержит только данные для продолжения, reusable lessons переходят в skills/policy.
11. Основной UX привязан к OpenCode-командам и субагентам. OpenCode остаётся основным клиентом AUSN, но core policy и bootstrap должны работать также с Codex или другим MCP-совместимым клиентом. Автоматический межмодельный fallback не включать; primary client выбирает пользователь.
12. Нет доказанного clean-clone pilot на второй директории/машине, поэтому текущая переносимость остаётся заявлением.
13. Clean-clone probe воспроизвёл зависимость codemap от локального состояния:
    модель требует ignored ENVIRONMENT.md, .local и tmp, а docgraph без
    соседнего ausn-qa-project получает битые cross-repository ссылки. Генератор
    должен различать отсутствующий optional runtime path, обязательный tracked
    path и недоступный внешний repository, возвращая typed gap без записи
    заведомо неполной карты.

## Неподлежащие нарушению ограничения

- Не переносить в AUSN продуктовые имена, требования и QA-решения Slider.
- Не изменять read-only продуктовые репозитории разработчиков.
- Не выводить и не коммитить секреты. Tracked env-template содержит только имена, комментарии и безопасные placeholder-значения.
- Не хранить абсолютные пути пользователя в tracked-файлах. MCP API может получать абсолютный projectPath только после runtime-resolve относительно корня control plane.
- Не требовать конкретную модель. OpenCode — текущий primary client, но переносимый контракт описывает capabilities, а не поставщика модели.
- Не включать автоматическое делегирование или provider fallback. Переключение клиента выполняется пользователем и отражается в capability report.
- Не останавливать рабочие SocratiCode watchers, не запускать второго writer и не пересоздавать существующие индексы как обычный repair.
- Сохранять Windows как поддерживаемое окружение; bootstrap core лучше сделать кроссплатформенным на Node.js 22, с тонкими shell/PowerShell wrappers только при необходимости.
- Не заявлять готовность по зелёному smoke. Нужен clean-clone bounded pilot.

## Целевая архитектура

Создай минимальную архитектуру, уточнив имена по стилю репозитория:

1. configs/workspace.json — относительный registry: logical id, relative path от control-plane root, remote URL, required/optional, read-only/writable, default branch, index required, context artifacts required.
2. configs/mcp/servers.json — единственный нейтральный источник MCP: command/transport, обязательные env names, risk tier, required/optional, supported clients и health probe. Сгенерированные client configs не должны становиться независимыми источниками истины.
3. configs/env.schema.json и безопасный .env.example без значений секретов.
4. scripts/bootstrap.mjs с режимами --plan, --check, --apply, --client opencode|codex|vscode, --skip-clone и --skip-index.
5. Отдельные модули или подкоманды: dependency detection; workspace resolver; env-name validation; MCP renderer/installer; SocratiCode liveness recovery; последовательная индексация; client capability check; redacted receipt в ignored .reports/.
6. scripts/finalize-control-plane-change.mjs: после содержательных изменений регенерирует codemap/docgraph, запускает gates, имеет --check для CI/pre-commit; pre-commit read-only и не меняет staged content.
7. Machine-readable task/process state: requirements и scenario coverage, test-data ownership/cleanup, product verdict отдельно от Git delivery, skill-effect receipt и process metrics.

## Порядок реализации

### Фаза 0. Baseline

- Зафиксируй HEAD, branch, remote и dirty-state.
- Построй карту текущих точек входа, MCP-конфигов, skills, prompts и checks.
- Выполни secret scan без вывода найденных значений.
- Создай таблицу requirement → current evidence → gap → target gate.
- Не переписывай документы до завершения baseline.

### Фаза 1. Очистка входа

- Удали сессионно-зависимую команду из README.
- Перепиши README как короткий маршрут установки с одной основной командой.
- Документируй ожидаемое относительное дерево каталогов. Все ссылки на соседние репозитории вычисляй от repository root.
- Добавь troubleshooting только для наблюдаемых typed failures.

### Фаза 2. Workspace и env contracts

- Введи registry репозиториев и JSON Schema.
- Добавь валидатор: unique ids/paths, отсутствие absolute paths, корректные access modes, отсутствие конфликтов writable/read-only.
- Добавь env schema/example и проверку только имён/наличия.
- Не клонируй private repository, пока credentials/remote недоступны; верни typed gap с точной следующей командой.

### Фаза 3. MCP single source

- Инвентаризируй четыре текущих конфига.
- Введи canonical manifest и детерминированный renderer.
- Для каждого клиента сравни semantic parity, а не формат строк.
- Включи SocratiCode, Atlassian, GitLab, Mattermost, test SSH/PGDB/Graylog/Grafana и Playwright согласно required/optional policy.
- Реальный liveness probe обязателен: наличие записи в config не означает работоспособность MCP.
- При отсутствии SocratiCode: полный tool registry/lazy-load → probe → config/runtime → штатный reconnect → повторный probe. Пользователя привлекай только к шагу, недоступному из клиента.

### Фаза 4. Bootstrap и индексирование

- Реализуй идемпотентный bootstrap --plan/check/apply.
- Docker Desktop и OrbStack считай альтернативными providers Docker API.
- Не устанавливай GUI-программы молча; верни инструкцию и повторяемый check.
- После запуска SocratiCode индексируй required repositories строго последовательно.
- Для каждого дождись terminal status; progress не считать готовностью.
- Сохрани receipt: logical repo id, resolved path, Git SHA, index status, watcher status, timestamps, gaps. Секреты и Authorization исключить.
- Добавь bootstrap --check, который повторно подтверждает готовность без изменений.

### Фаза 5. Client-neutral execution

- Определи capability profile: MCP discovery, filesystem, shell, browser, approvals, skills, commands, subagents.
- Сохрани OpenCode commands/subagents как adapter.
- Вынеси core QA flow в client-neutral skills/references.
- Добавь adapter check для OpenCode и Codex. Недоступная capability должна давать typed gap/fallback, а не тихо менять процесс.
- Подготовленные user prompts должны ссылаться на core flow и не зависеть от скрытой session id или конкретной модели.

### Фаза 6. Codemap и executable gates

- Сохрани сильные стороны текущего tools/codemap/generate.py.
- Добавь тесты генератора: deterministic output, broken links, stale fingerprint, generated HTML/JSON parity, relative-path portability.
- Введи финализатор и tracked read-only pre-commit hook.
- Добавь общий smoke gate управляющего слоя: schemas, MCP parity, skills/prompts links, codemap/docgraph, forbidden absolute paths, secret-name policy и bootstrap unit tests.
- Финальную регенерацию выполняй после всех authored changes и до staging.

### Фаза 7. Контролируемое самообучение

- Не разрешай агенту автоматически переписывать policy после одного случая.
- На каждой завершённой QA-задаче сохраняй ignored receipt: использованный skill, trigger, изменённое решение, добавленные проверки, предотвращённую ошибку, friction и outcome.
- Измеряй time-to-first-product-evidence, обязательные вмешательства пользователя, автономно завершённые сценарии, false-positive failures, recovery attempts/success и повторные дефекты процесса.
- После 3–5 задач запускай review loop. Повторяемый урок продвигай в skill или policy только с evidence и regression gate.
- docs/retrospectives.md оставь как краткий reusable knowledge index. Task-specific chronology и raw evidence держи в ignored reports или Git history; PROJECT_STATUS.md содержит лишь continuation-ready handoff.

### Фаза 8. Clean-clone acceptance pilot

В новой временной директории, без использования текущих .local, venv, node_modules, generated configs и SocratiCode collections:

1. Клонируй control plane.
2. Выполни инструкцию README буквально.
3. Подставь отдельный безопасный env fixture только с тестовыми значениями.
4. Выполни bootstrap plan, apply и повторный check.
5. Проверь выбранный client adapter.
6. Проиндексируй bounded набор: control plane, ausn-ai, ausn-qa-project и один read-only product repo.
7. Дождись terminal indexing readiness.
8. Запусти один user prompt в dry-run/context-review режиме без external writes.
9. Удали временную копию/контейнеры только после сохранения redacted receipt.

Если pilot нельзя выполнить из-за private credentials, проведи максимально полный fixture-based pilot и верни BLOCKED_EXTERNAL_ACCESS для оставшейся части. Не называй проект переносимым без terminal PASS реального pilot.

## Обязательные тесты

- JSON Schema и negative fixtures для workspace/MCP/env manifests.
- Отсутствие tracked absolute user paths и session ids.
- Детерминированный рендер всех client configs.
- Semantic parity текущих required MCP.
- Bootstrap dry-run не меняет filesystem/config.
- Повторный apply идемпотентен.
- Missing dependency/env/repository/MCP даёт typed failure.
- Индексация ждёт terminal state и не считает 100% промежуточной фазы PASS.
- Codemap/docgraph checks и pre-commit не изменяют staged файлы.
- Canonical skills и client adapters не противоречат друг другу.
- Secret scan не выводит значения.

## Definition of Done

Работа завершена только когда:

- новый README описывает полный путь clone → first task;
- одна команда выполняет plan/check/apply;
- относительное размещение всех репозиториев задано manifest-ом;
- MCP имеют один canonical manifest и проверенные client adapters;
- SocratiCode liveness и полная индексация подтверждаются receipts;
- codemap/docgraph финализируются и проверяются перед commit;
- self-learning основан на измеримых receipts и review cadence;
- полный управляющий gate проходит;
- выполнен clean-clone pilot либо возвращён точный внешний blocker;
- PROJECT_STATUS.md обновлён как краткий handoff;
- изменения разбиты на небольшие логические commits и отправлены в текущий remote без force-push.

## Формат итогового отчёта

Сообщи:

1. итоговый portability verdict: PASS | PARTIAL | BLOCKED;
2. реализованные фазы и commits;
3. команды и результаты gates;
4. clean-clone pilot evidence;
5. проверенные adapters;
6. unresolved typed gaps;
7. метрики baseline для следующих 3–5 QA-задач;
8. какие исторические артефакты удалены, перенесены или сохранены и почему.

Не выдавай количество документов, skills, тестов или MCP за продуктовый результат само по себе. Главный критерий — воспроизводимый terminal путь нового пользователя от клона до первой безопасно подготовленной QA-задачи.
