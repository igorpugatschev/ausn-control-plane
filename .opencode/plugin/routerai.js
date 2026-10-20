import { readFileSync } from "node:fs"
import path from "node:path"
import { parseEnv } from "node:util"

// Ключ хранится только в корневом .env; в конфигурацию попадает во время запуска.
const routeraiPlugin = async ({ directory }) => ({
  config: async (config) => {
    const provider = config.provider?.routerai
    if (!provider) return
    const env = parseEnv(readFileSync(path.join(directory ?? process.cwd(), ".env"), "utf8"))
    const key = process.env.LLM_API_KEY || env.LLM_API_KEY
    if (!key) throw new Error("RouterAI: заполните LLM_API_KEY в корневом .env")
    provider.options.apiKey = key
  },
})

// Ключ остаётся в .env и передаётся провайдеру только в памяти процесса.
export default {
  id: "ausn.routerai",
  server: routeraiPlugin,
  async setup(ctx) {
    const registration = await ctx.provider.transform((editor) => {
      if (!editor.get("routerai")) return
      const env = parseEnv(readFileSync(path.join(ctx.location.directory, ".env"), "utf8"))
      const key = process.env.LLM_API_KEY || env.LLM_API_KEY
      if (!key) throw new Error("RouterAI: заполните LLM_API_KEY в корневом .env")
      editor.update("routerai", (provider) => {
        provider.settings = { ...provider.settings, apiKey: key }
      })
    })
    return () => registration.dispose()
  },
}
