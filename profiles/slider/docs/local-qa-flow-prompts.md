# Slider QA — локально-первый флоу: короткие промты запуска

Источник — контракты `slider-web-control-plane` (`QA-LAUNCH.md`,
`agents/slider-ai-qa/prompts/*`). Отличие: этап `testing` идёт **на локальном
Docker-стенде** (`:8080`, canonical PG18, см. [local-first-qa-stand.md](local-first-qa-stand.md)),
а на `olddev` остаётся только регресс принятых задач.

## Этап 1. Контекст задачи

```text
Slider QA, режим context-review.
Задача: <Bitrix24 URL или ID>
1. Прочитай карточку и чат Bitrix (bitrix-task-read), связанные Yandex Wiki/Figma.
2. Определи ветку разработчика и её полный SHA в GitLab.
3. Собери scope, требования, макеты; зафиксируй deployment_candidate.
Остановись после handoff — деплой отдельно.
```

## Этап 2. Локальный деплой + тестирование до вердикта

```text
Slider QA, режим testing (локально, Docker).
Задача: <Bitrix24 ID>, ветка: <branch>, SHA: <sha>, компонент: <flask|landing|dashboard|pptx>
Деплой на локальный стенд выполни сам, без подтверждения:
  bash profiles/slider/scripts/local-deploy.sh <компонент> <sha>
Затем прогони полный QA-loop в scope задачи до PASS/FAIL/BLOCKED и краткого отчёта.
Доступ к контейнерам и логам — используй (docker exec / docker logs).
Merge в stage не делай; к delivery не переходи.
```

## Этап 3. Регресс принятых задач (olddev, по отдельной команде)

```text
Slider QA, режим stage-regression.
Задачи: <ID...>
Дождись моего подтверждения merge и сборки stage; сам сборку не запускай.
Выполни только короткий целевой smoke исправленных замечаний на olddev.
После моего приёмки — доставь автотесты. Полный QA-loop не повторяй.
```

## Одной строкой (быстрый старт)

```text
Slider QA: возьми задачу <ID>, задеплой её ветку локально (local-deploy.sh)
и прогони полный QA-loop до вердикта. Merge и olddev не трогай.
```

## Что нужно для старта на этой машине

- `slider-web-control-plane/.env` с доступами к контексту:
  `bitrix24_login`, `bitrix24_password` (Bitrix), при наличии —
  `yandex_wiki_oauth_token`/`yandex_wiki_org_id`, `figma_token`.
- Локальный стенд поднят (`:8080`) и `local-deploy.sh` (готовы).
