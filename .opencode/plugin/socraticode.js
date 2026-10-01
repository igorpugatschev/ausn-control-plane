/**
 * socraticode-opencode-plugin
 *
 * Гарантирует штатное присутствие MCP-сервера SocratiCode в конфиге opencode,
 * если пользователь не задал свою запись (пользователь приоритетнее).
 * При инициализации проверяет и при необходимости поднимает Qdrant и Ollama.
 */

import { execFile } from "node:child_process"
import { appendFile, mkdir } from "node:fs/promises"
import path from "node:path"

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

const QDRANT_URL = "http://127.0.0.1:17333"
const OLLAMA_URL = "http://127.0.0.1:11434"
const COMPOSE_FILE = "compose.socraticode.yaml"
const READY_TIMEOUT_MS = 90000
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
    composePath = COMPOSE_FILE,
    timeoutMs = READY_TIMEOUT_MS,
    intervalMs = POLL_INTERVAL_MS,
    httpOkFn = httpOk,
  } = opts

  if (await httpOkFn(`${url}/readyz`)) return "running"

  let started = false
  try {
    await run(["docker", "compose", "-f", composePath, "up", "-d"])
    started = true
  } catch {
    started = false
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

const PLUGIN_LOG = path.join(".local", "socraticode", "plugin.log")

export async function writePluginLog(filePath, message) {
  try {
    await mkdir(path.dirname(filePath), { recursive: true })
    await appendFile(filePath, `${new Date().toISOString()} ${message}\n`, "utf8")
  } catch {
    // журнал — best effort; плагин не должен падать из-за него
  }
}

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
    const logFile = directory ? path.join(directory, PLUGIN_LOG) : PLUGIN_LOG
    ensureInfra(defaultRun, { composePath })
      .then(async ({ qdrant, ollama }) => {
        const summary = `Qdrant: ${qdrant}, Ollama: ${ollama}`
        await log("info", summary)
        await writePluginLog(logFile, summary)
      })
      .catch(async () => {
        await log("warn", "health-проверка Qdrant/Ollama не удалась")
        await writePluginLog(logFile, "health-проверка Qdrant/Ollama не удалась")
      })
  }

  return {
    config: async (config) => {
      const added = ensureSocraticodeServer(config)
      await log("info", added ? "MCP-запись socraticode добавлена" : "MCP-запись socraticode уже задана — не трогаю")
    },
  }
}

export default socraticodePlugin
