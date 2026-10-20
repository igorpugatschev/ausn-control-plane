/**
 * profile-plugin: подключает навыки активного профиля проекта.
 * Регистрирует `profiles/<active>/skills` в config.skills.paths (opencode auto-discovers SKILL.md).
 * Активный профиль: env PROJECT_PROFILE -> configs/project.json -> ausn. Без инъекции в системный промпт.
 */
import { existsSync, readFileSync, readdirSync } from "node:fs"
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

// V2 регистрирует навыки через домен skill; V1 сохраняет прежний config-хук.
export default {
  id: "ausn.profile",
  server: profilePlugin,
  async setup(ctx) {
    const root = ctx.location.directory
    const skillsDir = path.join(root, "profiles", activeProfileId(root), "skills")
    if (!existsSync(skillsDir)) return
    const skills = readdirSync(skillsDir, { withFileTypes: true })
      .filter((entry) => entry.isDirectory())
      .map((entry) => path.join(skillsDir, entry.name, "SKILL.md"))
      .filter((file) => existsSync(file))
      .map((file) => {
        const text = readFileSync(file, "utf8")
        const match = text.match(/^---\r?\n([\s\S]*?)\r?\n---\r?\n([\s\S]*)$/)
        if (!match) throw new Error(`Некорректный frontmatter: ${file}`)
        // OpenCode работает на Bun: штатный YAML-парсер без новой зависимости.
        const metadata = Bun.YAML.parse(match[1])
        return { id: metadata.name, name: metadata.name, description: metadata.description,
          path: file, content: match[2] }
      })
    const registration = await ctx.skill.transform((editor) => {
      for (const skill of skills) {
        if (!editor.get(skill.id)) editor.add(skill)
      }
    })
    return () => registration.dispose()
  },
}
