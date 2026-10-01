import { test } from "node:test"
import assert from "node:assert/strict"
import path from "node:path"
import { fileURLToPath } from "node:url"
import { profilePlugin } from "../../.opencode/plugin/profile.js"

const here = path.dirname(fileURLToPath(import.meta.url))
const repoRoot = path.resolve(here, "..", "..")

test("плагин добавляет skills.paths активного профиля", async () => {
  const logs = []
  const client = { app: { log: async ({ body }) => logs.push(body) } }
  const hooks = await profilePlugin({ client, directory: repoRoot })
  const config = {}
  await hooks.config(config)
  assert.ok(config.skills.paths.includes(path.join(repoRoot, "profiles", "ausn", "skills")))
  assert.ok(logs.some((entry) => String(entry.message).includes("profiles/ausn/skills")))
})

test("плагин идемпотентен", async () => {
  const hooks = await profilePlugin({ client: undefined, directory: repoRoot })
  const config = { skills: { paths: [path.join(repoRoot, "profiles", "ausn", "skills")] } }
  await hooks.config(config)
  assert.equal(config.skills.paths.length, 1)
})
