import { test } from "node:test"
import assert from "node:assert/strict"
import {
  ensureSocraticodeServer,
  ensureQdrant,
  ensureOllama,
  ensureInfra,
} from "../../.opencode/plugin/socraticode.js"

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

const noHttp = async () => false

test("ensureQdrant: если уже отвечает — не запускает docker", async () => {
  const calls = []
  const run = async (cmd) => { calls.push(cmd); return "true" }
  const result = await ensureQdrant(run, { httpOkFn: async () => true })
  assert.equal(result, "running")
  assert.deepEqual(calls, [])
})

test("ensureQdrant: поднимает контейнер и ждёт готовности", async () => {
  const calls = []
  const run = async (cmd) => { calls.push(cmd); return "" }
  let attempts = 0
  const httpOkFn = async () => { attempts += 1; return attempts >= 2 }
  const result = await ensureQdrant(run, { httpOkFn, timeoutMs: 2000, intervalMs: 10 })
  assert.equal(result, "started")
  assert.deepEqual(calls[0], ["docker", "start", "socraticode-qdrant"])
})

test("ensureQdrant: при полном провале возвращает fail и не бросает", async () => {
  const run = async () => { throw new Error("docker недоступен") }
  const result = await ensureQdrant(run, { httpOkFn: noHttp, timeoutMs: 50, intervalMs: 10 })
  assert.equal(result, "fail")
})

test("ensureOllama: если уже отвечает — не запускает serve", async () => {
  const calls = []
  const run = async (cmd) => { calls.push(cmd); return "" }
  const result = await ensureOllama(run, { httpOkFn: async () => true })
  assert.equal(result, "running")
  assert.deepEqual(calls, [])
})

test("ensureOllama: запускает serve и ждёт", async () => {
  const calls = []
  const run = async (cmd) => { calls.push(cmd); return "" }
  let attempts = 0
  const httpOkFn = async () => { attempts += 1; return attempts >= 2 }
  const result = await ensureOllama(run, { httpOkFn, timeoutMs: 2000, intervalMs: 10 })
  assert.equal(result, "started")
  assert.deepEqual(calls[0], ["ollama", "serve"])
})

test("ensureInfra: собирает оба статуса", async () => {
  const run = async () => ""
  const result = await ensureInfra(run, { httpOkFn: async () => true })
  assert.deepEqual(result, { qdrant: "running", ollama: "running" })
})
