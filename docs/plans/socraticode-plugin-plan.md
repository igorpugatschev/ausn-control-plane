# SocratiCode Plugin Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Вернуть SocratiCode в штатный режим (всегда подключён) и добавить проектный плагин opencode, который гарантирует MCP-запись и сам поднимает/проверяет Qdrant и Ollama.

**Architecture:** Чистый ESM-плагин `.opencode/plugin/socraticode.js` (без зависимостей) с хуком `config` (идемпотентная гарантия записи `mcp.socraticode`, пользователь приоритетнее) и health-проверкой при инициализации (docker/ollama, таймауты, никогда не бросает). Правило «сначала поиск через SocratiCode» живёт в `AGENTS.md` (prompt-cache не ломается). Четыре конфига MCP возвращают сервер; `compose.socraticode.yaml` получает `restart: unless-stopped` как страховку.

**Tech Stack:** Node.js 24 (Bun-рантайм opencode), ESM `.js`, `node --test`, `node:child_process`, `fetch`; pytest/гейты Python в `.venv`; opencode plugin API (`config` hook, `client.app.log`).

**Spec:** `docs/plans/socraticode-plugin-design.md`

## Global Constraints

- Плагин — чистый ESM `.js`, **без новых npm-зависимостей**; точка входа — `.opencode/plugin/socraticode.js` (opencode подхватывает сам).
- Плагин **никогда не бросает** исключение и не блокирует старт сессии; таймауты ≤ 15 с; операции идемпотентны.
- Логирование только через `client.app.log({ body: { service: "socraticode-plugin", level, message } })`.
- **Никаких инъекций в системный промпт** (правило — в `AGENTS.md`).
- **Не копировать файлы/тексты вендора** (SocratiCode — AGPL-3.0-only); формулировки собственные.
- Версия сервера закреплена: `socraticode@1.14.0`.
- Документация и комментарии — на русском; не-ASCII только файлами UTF-8 (`write`/`edit`).
- Тесты/утилиты запускать через `.\.venv\Scripts\python.exe` и `node`; Windows PowerShell 5.1 — без кириллицы в inline-python.
- Гейты перед финалом: `tools/checks/mcp_parity.py`, `tools/codemap/generate.py --docs --all --check`, `--all --check`, `--system --check`, `node --check`, `node --test`.
- Коммиты: control plane — `origin` и `github`; `ausn-qa-project` — `origin`. Push сразу после коммита.

---

### Task 1: Вернуть сервер `socraticode` в четыре конфига MCP

**Files:**
- Modify: `.mcp.json` (вставить перед `"atlassian": {`)
- Modify: `.vscode/mcp.json` (вставить перед `"atlassian": {`)
- Modify: `.codex/config.toml` (вставить перед `[mcp_servers.atlassian]`)
- Modify: `.opencode/opencode.jsonc` (внутри `"mcp"`, перед `"atlassian": {`)
- Test: `tools/checks/mcp_parity.py` (готовый гейт)

**Interfaces:**
- Produces: во всех четырёх конфигах присутствует ключ `socraticode` с одинаковым смыслом (набор команд/переменных), гейт паритета зелёный — на это опираются задачи 2–3.

- [ ] **Step 1: Убедиться, что гейт сейчас зелёный без `socraticode`**

Run: `.\.venv\Scripts\python.exe tools\checks\mcp_parity.py`
Expected: `OK: конфигурации MCP совпадают по смыслу` (8 серверов).

- [ ] **Step 2: Добавить блок в `.mcp.json` (первым в `mcpServers`)**

```json
    "socraticode": {
      "command": "node",
      "args": [
        "-e",
        "process.env.TMP=process.env.TEMP=require('node:path').resolve('.local/socraticode/tmp'); const p=require('node:child_process').spawn('npx',['-y','socraticode@1.14.0'],{stdio:'inherit',shell:process.platform==='win32'}); p.on('exit',c=>process.exit(c??1));"
      ],
      "env": {
        "QDRANT_MODE": "external",
        "QDRANT_URL": "http://127.0.0.1:17333",
        "QDRANT_COLLECTION_PREFIX": "ausn_qa_",
        "EMBEDDING_PROVIDER": "ollama",
        "EMBEDDING_MODEL": "nomic-embed-text",
        "OLLAMA_MODE": "external",
        "OLLAMA_URL": "http://127.0.0.1:11434",
        "TMP": "./.local/socraticode/tmp",
        "TEMP": "./.local/socraticode/tmp",
        "SOCRATICODE_GLOBAL_CONFIG_DIR": "./.local/socraticode/context"
      }
    },
```

- [ ] **Step 3: Проверить, что гейт поймал дрейф**

Run: `.\.venv\Scripts\python.exe tools\checks\mcp_parity.py`
Expected: код возврата `1`, сообщение о расхождении (сервер есть не во всех файлах).

- [ ] **Step 4: Повторить блок в `.vscode/mcp.json`**

Тот же JSON-блок из шага 2, первым ключом в `mcpServers` (перед `"atlassian"`).

- [ ] **Step 5: Добавить секции в `.codex/config.toml` перед `[mcp_servers.atlassian]`**

```toml
[mcp_servers.socraticode]
command = "node"
args = ["-e", "process.env.TMP=process.env.TEMP=require('node:path').resolve('.local/socraticode/tmp'); const p=require('node:child_process').spawn('npx',['-y','socraticode@1.14.0'],{stdio:'inherit',shell:process.platform==='win32'}); p.on('exit',c=>process.exit(c??1));"]
startup_timeout_sec = 120
tool_timeout_sec = 600

[mcp_servers.socraticode.env]
QDRANT_MODE = "external"
QDRANT_URL = "http://127.0.0.1:17333"
QDRANT_COLLECTION_PREFIX = "ausn_qa_"
EMBEDDING_PROVIDER = "ollama"
EMBEDDING_MODEL = "nomic-embed-text"
OLLAMA_MODE = "external"
OLLAMA_URL = "http://127.0.0.1:11434"
SOCRATICODE_GLOBAL_CONFIG_DIR = "./.local/socraticode/context"

TEMP = "./.local/socraticode/tmp"
TMP = "./.local/socraticode/tmp"
```

- [ ] **Step 6: Добавить блок в `.opencode/opencode.jsonc` (внутри `"mcp"`, первым)**

```jsonc
    "socraticode": {
      "type": "local",
      "command": [
        "node",
        "-e",
        "process.env.TMP=process.env.TEMP=require('node:path').resolve('.local/socraticode/tmp'); const p=require('node:child_process').spawn('npx',['-y','socraticode@1.14.0'],{stdio:'inherit',shell:process.platform==='win32'}); p.on('exit',c=>process.exit(c??1));"
      ],
      "enabled": true,
      "environment": {
        "QDRANT_MODE": "external",
        "QDRANT_URL": "http://127.0.0.1:17333",
        "QDRANT_COLLECTION_PREFIX": "ausn_qa_",
        "EMBEDDING_PROVIDER": "ollama",
        "EMBEDDING_MODEL": "nomic-embed-text",
        "OLLAMA_MODE": "external",
        "OLLAMA_URL": "http://127.0.0.1:11434",
        "TMP": "./.local/socraticode/tmp",
        "TEMP": "./.local/socraticode/tmp",
        "SOCRATICODE_GLOBAL_CONFIG_DIR": "./.local/socraticode/context"
      }
    },
```

- [ ] **Step 7: Проверить валидность всех четырёх файлов и паритет**

Run: `.\.venv\Scripts\python.exe tools\checks\mcp_parity.py`
Expected: `OK: конфигурации MCP совпадают по смыслу`, 9 серверов.

- [ ] **Step 8: Коммит**

```bash
git add .mcp.json .vscode/mcp.json .codex/config.toml .opencode/opencode.jsonc
git commit -m "feat(mcp): вернуть socraticode в четыре конфига (штатный режим)"
git push origin main && git push github main
```

---

### Task 2: Плагин, часть 1 — гарантия MCP-записи (`config`-хук)

**Files:**
- Create: `.opencode/plugin/socraticode.js`
- Test: `tools/checks/socraticode_plugin.test.mjs`

**Interfaces:**
- Produces: `export function ensureSocraticodeServer(config) -> boolean` (true — добавил, false — не трогал);
  `export const socraticodePlugin = async ({ client }) => ({ config })` и `export default socraticodePlugin`.
  Задачи 3 и 6 опираются на эти имена.

- [ ] **Step 1: Написать падающий тест**

`tools/checks/socraticode_plugin.test.mjs`:

```js
import { test } from "node:test"
import assert from "node:assert/strict"
import { ensureSocraticodeServer } from "../../.opencode/plugin/socraticode.js"

test("подставляет запись mcp.socraticode, если её нет", () => {
  const cfg = {}
  assert.equal(ensureSocraticodeServer(cfg), true)
  assert.equal(cfg.mcp.socraticode.type, "local")
  assert.equal(cfg.mcp.socraticode.enabled, true)
  assert.equal(cfg.mcp.socraticode.environment.QDRANT_URL, "http://127.0.0.1:17333")
  assert.equal(cfg.mcp.socraticode.environment.QDRANT_MODE, "external")
})

test("не перезаписывает пользовательскую запись", () => {
  const cfg = { mcp: { socraticode: { type: "local", command: ["custom"], enabled: false } } }
  assert.equal(ensureSocraticodeServer(cfg), false)
  assert.deepEqual(cfg.mcp.socraticode.command, ["custom"])
  assert.equal(cfg.mcp.socraticode.enabled, false)
})

test("хук config применяет гарантию", async () => {
  const { socraticodePlugin } = await import("../../.opencode/plugin/socraticode.js")
  const hooks = await socraticodePlugin({ client: undefined })
  const cfg = { mcp: { atlassian: { type: "remote", url: "https://example" } } }
  await hooks.config(cfg)
  assert.equal(cfg.mcp.socraticode.type, "local")
  assert.equal(cfg.mcp.atlassian.url, "https://example")
})
```

- [ ] **Step 2: Убедиться, что тест падает**

Run: `node --test tools/checks/socraticode_plugin.test.mjs`
Expected: FAIL — `Cannot find module .../.opencode/plugin/socraticode.js`.

- [ ] **Step 3: Создать `.opencode/plugin/socraticode.js` (минимальная реализация)**

```js
/**
 * socraticode-opencode-plugin
 *
 * Гарантирует штатное присутствие MCP-сервера SocratiCode в конфиге opencode,
 * если пользователь не задал свою запись (пользователь приоритетнее).
 * Health-проверка Qdrant/Ollama — задача 3 (функции ensureQdrant/ensureOllama).
 */

const SERVICE = "socraticode-plugin"

const SOCRATICODE_SERVER = {
  type: "local",
  command: [
    "node",
    "-e",
    "process.env.TMP=process.env.TEMP=require('node:path').resolve('.local/socraticode/tmp'); const p=require('node:child_process').spawn('npx',['-y','socraticode@1.14.0'],{stdio:'inherit',shell:process.platform==='win32'}); p.on('exit',c=>process.exit(c??1));",
  ],
  enabled: true,
  environment: {
    QDRANT_MODE: "external",
    QDRANT_URL: "http://127.0.0.1:17333",
    QDRANT_COLLECTION_PREFIX: "ausn_qa_",
    EMBEDDING_PROVIDER: "ollama",
    EMBEDDING_MODEL: "nomic-embed-text",
    OLLAMA_MODE: "external",
    OLLAMA_URL: "http://127.0.0.1:11434",
    TMP: "./.local/socraticode/tmp",
    TEMP: "./.local/socraticode/tmp",
    SOCRATICODE_GLOBAL_CONFIG_DIR: "./.local/socraticode/context",
  },
}

export function ensureSocraticodeServer(config) {
  if (!config || typeof config !== "object") return false
  config.mcp = config.mcp || {}
  if (config.mcp.socraticode !== undefined) return false
  config.mcp.socraticode = SOCRATICODE_SERVER
  return true
}

export const socraticodePlugin = async ({ client }) => {
  const log = async (level, message) => {
    try {
      await client?.app?.log?.({ body: { service: SERVICE, level, message } })
    } catch {
      // логирование не должно ломать плагин
    }
  }

  return {
    config: async (config) => {
      const added = ensureSocraticodeServer(config)
      await log("info", added ? "MCP-запись socraticode добавлена" : "MCP-запись socraticode уже задана — не трогаю")
    },
  }
}

export default socraticodePlugin
```

- [ ] **Step 4: Убедиться, что тесты проходят**

Run: `node --test tools/checks/socraticode_plugin.test.mjs`
Expected: `pass 3`, `fail 0`.

- [ ] **Step 5: Проверить синтаксис**

Run: `node --check .opencode/plugin/socraticode.js`
Expected: без вывода (код 0).

- [ ] **Step 6: Коммит**

```bash
git add .opencode/plugin/socraticode.js tools/checks/socraticode_plugin.test.mjs
git commit -m "feat(plugin): socraticode — гарантия MCP-записи через config-хук"
git push origin main && git push github main
```

---

### Task 3: Плагин, часть 2 — health и авто-подъём Qdrant/Ollama

**Files:**
- Modify: `.opencode/plugin/socraticode.js`
- Modify: `tools/checks/socraticode_plugin.test.mjs`

**Interfaces:**
- Consumes: `ensureSocraticodeServer`, `socraticodePlugin` (Task 2).
- Produces: `export async function ensureQdrant(run, opts) -> "running"|"started"|"ok"|"fail"`;
  `export async function ensureOllama(run, opts) -> "running"|"started"|"fail"`;
  `export async function ensureInfra(run, opts) -> { qdrant, ollama }`.
  `run(cmd: string[]) -> Promise<string>` (отклоняется при ненулевом коде). Task 6 проверяет вживую.

- [ ] **Step 1: Дописать падающие тесты в `tools/checks/socraticode_plugin.test.mjs`**

```js
import { ensureQdrant, ensureOllama, ensureInfra } from "../../.opencode/plugin/socraticode.js"

const noHttp = async () => false

test("ensureQdrant: если уже отвечает — не запускает docker", async () => {
  const calls = []
  const run = async (cmd) => { calls.push(cmd); return "true" }
  const result = await ensureQdrant(run, { httpOkFn: async () => true })
  assert.equal(result, "running")
  assert.deepEqual(calls, [])
})

test("ensureQdrant: поднимает контейнер и ждёт готовности", async () => {
  const calls = []
  const run = async (cmd) => { calls.push(cmd); return "" }
  let attempts = 0
  const httpOkFn = async () => { attempts += 1; return attempts >= 2 }
  const result = await ensureQdrant(run, { httpOkFn, timeoutMs: 2000, intervalMs: 10 })
  assert.equal(result, "started")
  assert.deepEqual(calls[0], ["docker", "start", "socraticode-qdrant"])
})

test("ensureQdrant: при полном провале возвращает fail и не бросает", async () => {
  const run = async () => { throw new Error("docker недоступен") }
  const result = await ensureQdrant(run, { httpOkFn: noHttp, timeoutMs: 50, intervalMs: 10 })
  assert.equal(result, "fail")
})

test("ensureOllama: если уже отвечает — не запускает serve", async () => {
  const calls = []
  const run = async (cmd) => { calls.push(cmd); return "" }
  const result = await ensureOllama(run, { httpOkFn: async () => true })
  assert.equal(result, "running")
  assert.deepEqual(calls, [])
})

test("ensureOllama: запускает serve и ждёт", async () => {
  const calls = []
  const run = async (cmd) => { calls.push(cmd); return "" }
  let attempts = 0
  const httpOkFn = async () => { attempts += 1; return attempts >= 2 }
  const result = await ensureOllama(run, { httpOkFn, timeoutMs: 2000, intervalMs: 10 })
  assert.equal(result, "started")
  assert.deepEqual(calls[0], ["ollama", "serve"])
})

test("ensureInfra: собирает оба статуса", async () => {
  const run = async () => ""
  const result = await ensureInfra(run, { httpOkFn: async () => true })
  assert.deepEqual(result, { qdrant: "running", ollama: "running" })
})
```

- [ ] **Step 2: Убедиться, что новые тесты падают**

Run: `node --test tools/checks/socraticode_plugin.test.mjs`
Expected: FAIL — `ensureQdrant is not a function`.

- [ ] **Step 3: Дописать реализацию в конец `.opencode/plugin/socraticode.js`**

Добавить импорт в начало файла:

```js
import { execFile } from "node:child_process"
import path from "node:path"
```

Добавить функции (перед `socraticodePlugin`):

```js
const QDRANT_URL = "http://127.0.0.1:17333"
const OLLAMA_URL = "http://127.0.0.1:11434"
const QDRANT_CONTAINER = "socraticode-qdrant"
const COMPOSE_FILE = "compose.socraticode.yaml"
const READY_TIMEOUT_MS = 10000
const POLL_INTERVAL_MS = 500

const defaultRun = (cmd) =>
  new Promise((resolve, reject) => {
    execFile(cmd[0], cmd.slice(1), { windowsHide: true, timeout: 15000 }, (error, stdout) => {
      if (error) reject(error)
      else resolve(String(stdout))
    })
  })

async function httpOk(url, timeoutMs = 1500) {
  const controller = new AbortController()
  const timer = setTimeout(() => controller.abort(), timeoutMs)
  try {
    const response = await fetch(url, { signal: controller.signal })
    return response.ok
  } catch {
    return false
  } finally {
    clearTimeout(timer)
  }
}

const sleep = (ms) => new Promise((resolve) => setTimeout(resolve, ms))

export async function ensureQdrant(run, opts = {}) {
  const {
    url = QDRANT_URL,
    container = QDRANT_CONTAINER,
    composePath = COMPOSE_FILE,
    timeoutMs = READY_TIMEOUT_MS,
    intervalMs = POLL_INTERVAL_MS,
    httpOkFn = httpOk,
  } = opts

  if (await httpOkFn(`${url}/readyz`)) return "running"

  let started = false
  try {
    await run(["docker", "start", container])
    started = true
  } catch {
    try {
      await run(["docker", "compose", "-f", composePath, "up", "-d"])
      started = true
    } catch {
      started = false
    }
  }

  const deadline = Date.now() + timeoutMs
  while (Date.now() < deadline) {
    if (await httpOkFn(`${url}/readyz`)) return started ? "started" : "ok"
    await sleep(intervalMs)
  }
  return "fail"
}

export async function ensureOllama(run, opts = {}) {
  const {
    url = OLLAMA_URL,
    timeoutMs = READY_TIMEOUT_MS,
    intervalMs = POLL_INTERVAL_MS,
    httpOkFn = httpOk,
  } = opts

  if (await httpOkFn(`${url}/api/tags`)) return "running"

  try {
    run(["ollama", "serve"]).catch(() => {})
  } catch {
    // запуск — best effort
  }

  const deadline = Date.now() + timeoutMs
  while (Date.now() < deadline) {
    if (await httpOkFn(`${url}/api/tags`)) return "started"
    await sleep(intervalMs)
  }
  return "fail"
}

export async function ensureInfra(run, opts = {}) {
  const [qdrant, ollama] = await Promise.all([ensureQdrant(run, opts), ensureOllama(run, opts)])
  return { qdrant, ollama }
}
```

Изменить `socraticodePlugin`: принять `directory` и запустить health один раз (fire-and-forget):

```js
export const socraticodePlugin = async ({ client, directory }) => {
  const log = async (level, message) => {
    try {
      await client?.app?.log?.({ body: { service: SERVICE, level, message } })
    } catch {
      // логирование не должно ломать плагин
    }
  }

  if (client) {
    const composePath = directory ? path.join(directory, COMPOSE_FILE) : COMPOSE_FILE
    ensureInfra(defaultRun, { composePath })
      .then(({ qdrant, ollama }) => log("info", `Qdrant: ${qdrant}, Ollama: ${ollama}`))
      .catch(() => log("warn", "health-проверка Qdrant/Ollama не удалась"))
  }

  return {
    config: async (config) => {
      const added = ensureSocraticodeServer(config)
      await log("info", added ? "MCP-запись socraticode добавлена" : "MCP-запись socraticode уже задана — не трогаю")
    },
  }
}
```

- [ ] **Step 4: Убедиться, что все тесты проходят**

Run: `node --test tools/checks/socraticode_plugin.test.mjs`
Expected: `pass 9`, `fail 0`.

- [ ] **Step 5: Проверить синтаксис**

Run: `node --check .opencode/plugin/socraticode.js`
Expected: без вывода (код 0).

- [ ] **Step 6: Коммит**

```bash
git add .opencode/plugin/socraticode.js tools/checks/socraticode_plugin.test.mjs
git commit -m "feat(plugin): socraticode — health и авто-подъём Qdrant/Ollama"
git push origin main && git push github main
```

---

### Task 4: `restart: unless-stopped`, правило в `AGENTS.md`, рабочая таблица навыка

**Files:**
- Modify: `compose.socraticode.yaml` (сервис Qdrant)
- Modify: `AGENTS.md` (вернуть штатный режим, добавить правило поиска)
- Modify: `.agents/skills/ausn-socraticode/SKILL.md` (рабочая таблица)

**Interfaces:**
- Consumes: плагин (Tasks 2–3) как исполнитель авто-подъёма.
- Produces: постоянное правило «сначала поиск» в контексте агента; страховочная политика перезапуска контейнера.

- [ ] **Step 1: Добавить политику перезапуска в `compose.socraticode.yaml`**

В сервисе Qdrant добавить строку `restart: unless-stopped` (рядом с `ports`/`volumes`):

```yaml
    restart: unless-stopped
```

Применить политику к уже существующему контейнеру:

Run: `docker update --restart unless-stopped socraticode-qdrant`
Expected: имя контейнера в выводе.

- [ ] **Step 2: Вернуть штатный режим в `AGENTS.md`**

Найти все вхождения `по требованию` и заменить на штатный режим:

Run: `rg -n "по требованию" AGENTS.md`

Ожидаемые места: раздел «Конфигурация MCP» (строка про четыре файла), раздел «Индексация SocratiCode» (пункт про режим), «Настройка после клонирования» (пункт про compose).

Заменить формулировки на: сервер `socraticode` присутствует в четырёх конфигах и работает штатно; Qdrant/Ollama поднимаются автоматически (плагин `.opencode/plugin/socraticode.js`) и держатся за счёт `restart: unless-stopped`.

Отдельно вернуть `socraticode` первым в перечень серверов в пункте «Один и тот же набор серверов …» раздела «Конфигурация MCP»: было `(atlassian, gitlab, mattermost, test_ssh, test_pgdb, test_graylog, test_grafana, playwright)` → стало `(socraticode, atlassian, gitlab, mattermost, test_ssh, test_pgdb, test_graylog, test_grafana, playwright)`.

- [ ] **Step 3: Добавить правило «сначала поиск» в `AGENTS.md`**

В раздел «Работа с кодом» добавить пункт:

```markdown
### Поиск по индексированным репозиториям (SocratiCode)

Индексированные репозитории (`ausn-core`, `ausn-ai`, `ausn-control-plane`, `ausn-qa-project` и др. в `../ausn`)
исследуются **через SocratiCode**, а не чтением файлов наугад:

- разведка и незнакомый код — `codebase_search` (гибрид semantic+BM25 за один вызов);
- перед правкой/удалением — `codebase_graph_query` / `codebase_impact` (blast radius);
- связи функций — `codebase_symbol` / `codebase_symbols` / `codebase_flow`;
- навыки, субагенты, команды (dot-каталоги) — только `codebase_context_search`;
- если поиск пуст — `codebase_status`, при необходимости `codebase_index`/`codebase_update`.

**Исключение:** точная строка, идентификатор или регэксп — быстрее и точнее через `rg`/`ast-grep`
(позиция вендора SocratiCode).
```

- [ ] **Step 4: Дополнить навык `.agents/skills/ausn-socraticode/SKILL.md`**

Добавить раздел «Рабочая таблица»:

```markdown
## Рабочая таблица «задача → инструмент»

| Задача | Инструмент |
|---|---|
| Понять, где живёт функционал | `codebase_search` (широкий запрос) |
| Найти класс/функцию/тип по имени | `codebase_symbols query=…` |
| Что ломается при изменении X | `codebase_impact target=X` |
| Что делает точка входа | `codebase_flow entrypoint=X` |
| Кандидаты точек входа | `codebase_flow` (без аргументов) |
| Кто вызывает и что вызывает | `codebase_symbol name=X` |
| Что импортирует файл / кто зависит | `codebase_graph_query` |
| Циклические зависимости | `codebase_graph_circular` |
| Схемы БД, API-спеки, конфиги | `codebase_context` / `codebase_context_search` |
| Точная строка/идентификатор/регэксп | `rg` / `ast-grep` (исключение) |
| Индекс устарел | `codebase_status` → `codebase_update` |
```

- [ ] **Step 5: Коммит**

```bash
git add compose.socraticode.yaml AGENTS.md .agents/skills/ausn-socraticode/SKILL.md
git commit -m "docs(rules): штатный режим SocratiCode и правило поиска через него"
git push origin main && git push github main
```

---

### Task 5: Откат документации и вики

**Files:**
- Modify: `docs/socraticode.md`
- Modify: `docs/mcp.md`
- Modify: `PROJECT_STATUS.md`
- Modify (вика GitLab, проект `rcktsci/projects/ausn/integrator/ausn-control-plane`): `SocratiCode`, `MCP-servers`, `Getting-started`, `home`

**Interfaces:**
- Consumes: результат Tasks 1–4.
- Produces: документация и вики согласованы со штатным режимом.

- [ ] **Step 1: Переписать раздел режима в `docs/socraticode.md`**

Убрать сценарий «поднять/остановить под задачу» как обязательный. Явно указать: сервер в четырёх конфигах, работает штатно; Qdrant/Ollama поднимает плагин, контейнер с `restart: unless-stopped`; ручные команды нужны только для диагностики.

- [ ] **Step 2: Вернуть сервер в `docs/mcp.md`**

Заменить «восемь серверов по умолчанию» на «девять: `socraticode`, `atlassian`, …»; убрать оговорку про «по требованию».

- [ ] **Step 3: Обновить `PROJECT_STATUS.md`**

В разделе решений отменить запись от 2026-09-29 и зафиксировать новое решение 2026-10-01 (штатный режим + плагин + правило), со ссылкой на спеку и план.

- [ ] **Step 4: Обновить вики (4 страницы)**

Для каждой страницы получить текущий текст и заменить политику:

- `SocratiCode`: убрать «режим по требованию» и `up/down`; описать штатный режим, авто-подъём плагином, `restart: unless-stopped`; оставить рабочую таблицу «задача → инструмент» и границы (grep для точных строк).
- `MCP-servers`: «девять серверов», `socraticode` в наборе.
- `Getting-started`: вернуть индексацию в общие шаги (без «если нужно»).
- `home`: вернуть «девять серверов», убрать «по требованию».

- [ ] **Step 5: Проверить кодировки и граф документации**

Run: `rg -n "по требованию|up -d|down" docs/socraticode.md docs/mcp.md AGENTS.md`
Expected: остались только диагностические упоминания (в `docs/socraticode.md`), обязательных сценариев запуска/остановки нет; «по требованию» не встречается.
Run: `.\.venv\Scripts\python.exe tools\codemap\generate.py --docs --all`
Expected: `control-plane: … -> docs/codemap`.

- [ ] **Step 6: Коммит**

```bash
git add docs/socraticode.md docs/mcp.md PROJECT_STATUS.md docs/codemap
git commit -m "docs: откат политики «по требованию» — SocratiCode в штатном режиме"
git push origin main && git push github main
```

---

### Task 6: Финальная проверка (гейты + живой авто-подъём)

**Files:**
- Test: гейты и ручная проверка
- Modify: при необходимости — ничего (багфиксы в предыдущих файлах)

**Interfaces:**
- Consumes: всё выше.
- Produces: подтверждённый штатный режим.

- [ ] **Step 1: Тесты плагина и синтаксис**

Run: `node --check .opencode/plugin/socraticode.js`
Run: `node --test tools/checks/socraticode_plugin.test.mjs`
Expected: без вывода; `pass 9`, `fail 0`.

- [ ] **Step 2: Гейты репозитория**

Run: `.\.venv\Scripts\python.exe tools\checks\mcp_parity.py`
Run: `.\.venv\Scripts\python.exe tools\codemap\generate.py --all --check`
Run: `.\.venv\Scripts\python.exe tools\codemap\generate.py --docs --all --check`
Run: `.\.venv\Scripts\python.exe tools\codemap\generate.py --system --check`
Expected: все с кодом 0 (`OK`, `актуально`).

- [ ] **Step 3: Живая проверка авто-подъёма**

```bash
docker stop socraticode-qdrant
```

Затем запустить opencode из корня control plane и убедиться в логе плагина:
`Qdrant: started, Ollama: running` (или `...: running`), и что `codebase_health` отвечает без ручных `docker start`.

- [ ] **Step 4: Проверить, что поиск идёт через SocratiCode**

В новой сессии задать вопрос по индексированному репозиторию (например, «где реализован … в `ausn-core`») и убедиться, что вызов идёт через `codebase_search`/`codebase_symbol`, а не чтением файлов наугад.

- [ ] **Step 5: Финальный коммит (если были правки)**

```bash
git add -A
git commit -m "test(plugin): финальная проверка штатного режима SocratiCode"
git push origin main && git push github main
```
