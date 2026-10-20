/**
 * socraticode-opencode-plugin
 *
 * Гарантирует штатное присутствие MCP-сервера SocratiCode в конфиге opencode,
 * если пользователь не задал свою запись (пользователь приоритетнее).
 * При инициализации проверяет и при необходимости поднимает Qdrant и Ollama.
 *
 * ВАЖНО (opencode 1.18.33+): авто-загрузчик расценивает КАЖДЫЙ function-экспорт
 * модуля как legacy-плагин и вызывает его со своим PluginInput. Вспомогательные
 * экспорты резолвились в undefined и клали запуск opencode («plugin config hook
 * failed» N.config). Экспортируем V1-фабрику и V1/V2-определение; общая логика — в
 * tools/socraticode-plugin-core.mjs (вне .opencode/plugin/, использует тесты).
 */
import path from "node:path"
import {
  SOCRATICODE_SERVER,
  COMPOSE_FILE,
  PLUGIN_LOG,
  defaultRun,
  ensureInfra,
  ensureSocraticodeServer,
  writePluginLog,
} from "../../tools/socraticode-plugin-core.mjs"

const SERVICE = "socraticode-plugin"

function startInfrastructure(directory, log = async () => {}) {
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

export const socraticodePlugin = async ({ client, directory }) => {
  const log = async (level, message) => {
    try {
      await client?.app?.log?.({ body: { service: SERVICE, level, message } })
    } catch {
      // логирование не должно ломать плагин
    }
  }

  if (client) startInfrastructure(directory, log)

  return {
    config: async (config) => {
      const added = ensureSocraticodeServer(config)
      await log("info", added ? "MCP-запись socraticode добавлена" : "MCP-запись socraticode уже задана — не трогаю")
    },
  }
}

export default {
  id: "ausn.socraticode",
  server: socraticodePlugin,
  async setup(ctx) {
    startInfrastructure(ctx.location.directory)
    const registration = await ctx.mcp.transform((editor) => {
      if (editor.get("socraticode")) return
      const { enabled, ...server } = SOCRATICODE_SERVER
      editor.set("socraticode", { ...server, disabled: !enabled })
    })
    return () => registration.dispose()
  },
}
