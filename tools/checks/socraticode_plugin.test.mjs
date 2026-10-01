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
