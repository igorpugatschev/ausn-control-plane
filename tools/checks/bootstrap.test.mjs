import { test } from "node:test"
import assert from "node:assert/strict"
import { readFile } from "node:fs/promises"
import path from "node:path"
import { fileURLToPath } from "node:url"
import { checkEnv, checkWorkspace, parseEnvNames } from "../../scripts/bootstrap.mjs"

const here = path.dirname(fileURLToPath(import.meta.url))
const repoRoot = path.resolve(here, "..", "..")
const configs = path.join(repoRoot, "configs")

test("parseEnvNames берёт только имена", () => {
  const names = parseEnvNames('A=1\n# c\nB="x"\n')
  assert.deepEqual([...names].sort(), ["A", "B"])
})

test("checkWorkspace на текущем репозитории без нарушений", () => {
  assert.deepEqual(checkWorkspace(configs, repoRoot), [])
})

test("checkEnv с пустым набором сообщает об отсутствующих именах", async () => {
  const issues = await checkEnv(configs, repoRoot, new Set())
  assert.ok(issues.length > 0)
  assert.ok(issues.every((issue) => typeof issue === "string"))
})

test("checkEnv с именами из схемы не находит пропусков", async () => {
  const schema = JSON.parse(await readFile(path.join(configs, "env.schema.json"), "utf8"))
  const names = new Set(schema.vars.filter((item) => item.required).map((item) => item.name))
  assert.deepEqual(await checkEnv(configs, repoRoot, names), [])
})
