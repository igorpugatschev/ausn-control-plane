import { test } from "node:test"
import assert from "node:assert/strict"
import path from "node:path"
import { fileURLToPath } from "node:url"
import { checkRendered, loadManifest, renderMcpJson, renderVscode } from "../../scripts/render-mcp.mjs"

const here = path.dirname(fileURLToPath(import.meta.url))
const repoRoot = path.resolve(here, "..", "..")
const configs = path.join(repoRoot, "configs")

test("рендер детерминирован", () => {
  assert.equal(
    JSON.stringify(renderMcpJson(loadManifest(configs))),
    JSON.stringify(renderMcpJson(loadManifest(configs))),
  )
})

test("рендер совпадает с .mcp.json и .vscode/mcp.json", async () => {
  assert.deepEqual(await checkRendered(configs, repoRoot), [])
})

test("vscode-рендер: type/cwd только у remote-серверов", () => {
  const servers = renderVscode(loadManifest(configs)).servers
  assert.equal(servers.socraticode.type, undefined)
  assert.equal(servers.atlassian.type, "stdio")
  assert.equal(servers.atlassian.cwd, "${workspaceFolder}")
})
