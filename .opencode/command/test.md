---
description: Запускает выбранный набор автотестов QA-проекта.
agent: build
---

Выполни команду из корня control plane. Путь QA-проекта — `../ausn/ausn-qa-project`
(локальный корень — в `ENVIRONMENT.md`).

```powershell
$ErrorActionPreference = 'Stop'
$qaProject = Resolve-Path -LiteralPath '..\ausn\ausn-qa-project' -ErrorAction Stop
$exitCode = 0

Push-Location -LiteralPath $qaProject
try {
    $argumentsText = @'
$ARGUMENTS
'@.Trim()
    switch ($argumentsText) {
        'smoke' { & .\.venv\Scripts\python.exe -m pytest -m smoke -v }
        'kafka' { & .\.venv\Scripts\python.exe -m pytest -m kafka -v }
        'all' { & .\.venv\Scripts\python.exe -m pytest -n 4 }
        '' { & .\.venv\Scripts\python.exe -m pytest -m smoke -v }
        default {
            if (-not $argumentsText.StartsWith('[') -or -not $argumentsText.EndsWith(']')) {
                throw 'Пользовательские аргументы pytest должны быть JSON-массивом строк.'
            }
            $parsed = $argumentsText | ConvertFrom-Json -ErrorAction Stop
            $pytestArguments = @(foreach ($argument in $parsed) { $argument })
            if ($pytestArguments | Where-Object { $_ -isnot [string] }) {
                throw 'Пользовательские аргументы pytest должны быть JSON-массивом строк.'
            }
            & .\.venv\Scripts\python.exe -m pytest @pytestArguments
        }
    }
    $exitCode = $LASTEXITCODE
}
finally {
    Pop-Location
}
exit $exitCode
```

Значения: `smoke`, `kafka`, `all` или пользовательские аргументы pytest JSON-массивом строк,
например `["tests/api/test_admin_panel.py", "-q"]`.
