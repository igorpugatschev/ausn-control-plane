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
 * failed» N.config). Поэтому экспортируется только фабрика; логика — в
 * tools/socraticode-plugin-core.mjs (вне .opencode/plugin/, использует тесты).
 */
import path from "node:path"
import {
  COMPOSE_FILE,
  PLUGIN_LOG,
  defaultRun,
  ensureInfra,
  ensureSocraticodeServer,
  writePluginLog,
} from "../../tools/socraticode-plugin-core.mjs"

const SERVICE = "socraticode-plugin"

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
