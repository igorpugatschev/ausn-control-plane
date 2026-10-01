/**
 * profile-plugin: подключает навыки активного профиля проекта.
 * Регистрирует `profiles/<active>/skills` в config.skills.paths (opencode auto-discovers SKILL.md).
 * Активный профиль: env PROJECT_PROFILE -> configs/project.json -> ausn. Без инъекции в системный промпт.
 */
import { existsSync, readFileSync } from "node:fs"
import path from "node:path"

const SERVICE = "profile-plugin"

function activeProfileId(root) {
  if (process.env.PROJECT_PROFILE) return process.env.PROJECT_PROFILE.trim()
  const pointer = path.join(root, "configs", "project.json")
  if (existsSync(pointer)) return JSON.parse(readFileSync(pointer, "utf8")).active ?? "ausn"
  return "ausn"
}

export const profilePlugin = async ({ client, directory }) => {
  const root = directory ?? process.cwd()
  const id = activeProfileId(root)
  const skillsDir = path.join(root, "profiles", id, "skills")
  const log = async (level, message) => {
    try {
      await client?.app?.log?.({ body: { service: SERVICE, level, message } })
    } catch {
      // логирование не должно ломать плагин
    }
  }

  return {
    config: async (config) => {
      if (!existsSync(skillsDir)) return
      config.skills = config.skills || {}
      config.skills.paths = config.skills.paths || []
      if (!config.skills.paths.includes(skillsDir)) config.skills.paths.push(skillsDir)
      await log("info", `профиль ${id}: skills.paths += profiles/${id}/skills`)
    },
  }
}

export default profilePlugin
