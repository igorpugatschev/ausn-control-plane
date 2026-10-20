import { test } from "node:test"
import assert from "node:assert/strict"
import { mkdtempSync, mkdirSync, writeFileSync, rmSync } from "node:fs"
import { tmpdir } from "node:os"
import path from "node:path"
import profile from "../../.opencode/plugin/profile.js"
import routerai from "../../.opencode/plugin/routerai.js"
import socraticode from "../../.opencode/plugin/socraticode.js"

test("точки входа совместимы с V2 и сохраняют V1 server", () => {
  const plugins = [profile, routerai, socraticode]
  assert.equal(new Set(plugins.map((plugin) => plugin.id)).size, 3)
  for (const plugin of plugins) {
    assert.equal(typeof plugin.setup, "function")
    assert.equal(typeof plugin.server, "function")
  }
})

test("V2 профиль регистрирует навыки выбранного профиля и освобождает transform", async (t) => {
  const root = mkdtempSync(path.join(tmpdir(), "ausn-v2-profile-"))
  const skillDir = path.join(root, "profiles", "test", "skills", "sample")
  mkdirSync(skillDir, { recursive: true })
  mkdirSync(path.join(root, "configs"))
  writeFileSync(path.join(root, "configs", "project.json"), JSON.stringify({ active: "test" }))
  // JSON — подмножество YAML; проверяем регистрацию, а не парсер рантайма Bun.
  writeFileSync(path.join(skillDir, "SKILL.md"), '---\n{"name":"sample","description":"Описание"}\n---\nТело навыка')
  const previousBun = globalThis.Bun
  const previousProfile = process.env.PROJECT_PROFILE
  delete process.env.PROJECT_PROFILE
  globalThis.Bun = { YAML: { parse: JSON.parse } }
  t.after(() => {
    globalThis.Bun = previousBun
    if (previousProfile === undefined) delete process.env.PROJECT_PROFILE
    else process.env.PROJECT_PROFILE = previousProfile
    rmSync(root, { recursive: true, force: true })
  })
  const skills = []
  let disposed = false
  const dispose = await profile.setup({
    location: { directory: root },
    skill: { transform: async (transform) => {
      transform({ get: () => undefined, add: (skill) => skills.push(skill) })
      return { dispose: () => { disposed = true } }
    } },
  })
  assert.equal(skills.length, 1)
  assert.equal(skills[0].id, "sample")
  assert.equal(skills[0].description, "Описание")
  assert.equal(skills[0].content, "Тело навыка")
  assert.equal(skills[0].path, path.join(skillDir, "SKILL.md"))
  await dispose()
  assert.equal(disposed, true)
})

test("V2 RouterAI читает ключ из .env в settings, сохраняя baseURL", async (t) => {
  const root = mkdtempSync(path.join(tmpdir(), "ausn-v2-router-"))
  writeFileSync(path.join(root, ".env"), "LLM_API_KEY=test-only-sentinel\n")
  const previousKey = process.env.LLM_API_KEY
  delete process.env.LLM_API_KEY
  t.after(() => {
    if (previousKey === undefined) delete process.env.LLM_API_KEY
    else process.env.LLM_API_KEY = previousKey
    rmSync(root, { recursive: true, force: true })
  })
  const provider = { settings: { baseURL: "https://example.invalid" } }
  let disposed = false
  const dispose = await routerai.setup({
    location: { directory: root },
    provider: { transform: async (transform) => {
      transform({ get: () => provider, update: (id, update) => {
        assert.equal(id, "routerai")
        update(provider)
      } })
      return { dispose: () => { disposed = true } }
    } },
  })
  assert.equal(provider.settings.apiKey, "test-only-sentinel")
  assert.equal(provider.settings.baseURL, "https://example.invalid")
  await dispose()
  assert.equal(disposed, true)
})

test("V2 RouterAI без провайдера не требует .env и ключ", async () => {
  await routerai.setup({ location: { directory: "/missing" }, provider: {
    transform: async (transform) => {
      transform({ get: () => undefined })
      return { dispose() {} }
    },
  } })
})
