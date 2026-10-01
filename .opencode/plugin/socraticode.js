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
