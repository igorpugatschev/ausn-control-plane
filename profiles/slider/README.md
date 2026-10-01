# Профиль slider

Второй продукт (Slider). Данные профиля изолированы: сюда не переносятся АУСН-имена и решения.

## Что заполнить

1. `workspace.json` — реестр репозиториев: `id`, `path` (`../slider-web/<repo>`), `url`, `access`
   (`read-only`, кроме продукта QA), `required`, `index`, `contextArtifacts`, `defaultBranch`.
   Репозитории располагаются в `C:\rocketscience\slider-web\<repo>` (`repoPrefix: "slider-web"`).
2. `project.json` → `contextRepos` — идентификаторы репозиториев из `workspace.json`.
3. `project.json` → `stands`, `mcp.endpoints`, `jira.projectKey` — значения Slider.
4. `env` уже перечисляет требуемые имена переменных Slider (проверяет `bootstrap --check`).

## Активация

- `configs/project.json` → `{"active": "slider"}` или env `PROJECT_PROFILE=slider`.
- Проверка: `node scripts/bootstrap.mjs --check`, `python tools/checks/validate_manifests.py`.
- Доменные навыки — `skills/`, доки/отчёты — `docs/`, модели codemap — `models/`.

## GitLab и контур

- Корпоративный GitLab CE: `https://gitlab.slider-ai.ru`; OpenAPI swagger: `https://olddev.slider-ai.ru/openapi/swagger`.
- Креды — только в локальном `.env` (секция «Slider / корпоративные сервисы»).
