---
description: Запускает статические проверки QA-проекта (ruff).
agent: build
---

Выполни команду из корня control plane. Путь QA-проекта — `../ausn/ausn-qa-project`
(локальный корень — в `ENVIRONMENT.md`).

```powershell
$ErrorActionPreference = 'Stop'
$qaProject = Resolve-Path -LiteralPath '..\ausn\ausn-qa-project' -ErrorAction Stop

Push-Location -LiteralPath $qaProject
try {
    & .\.venv\Scripts\python.exe -m ruff check src tests scripts
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
    & .\.venv\Scripts\python.exe -m ruff format src tests scripts --check
    if ($LASTEXITCODE -ne 0) { exit $LASTEXITCODE }
}
finally {
    Pop-Location
}
```

Полный quality gate продукта (encoding gate, contract-тесты, coverage) запускается отдельно:
`.\\.venv\\Scripts\\python.exe scripts\\tools\\audit_gate.py --full` в `../ausn/ausn-qa-project`.
