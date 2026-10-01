import { test } from "node:test"
import assert from "node:assert/strict"
import { mkdir, mkdtemp, readFile, writeFile } from "node:fs/promises"
import { tmpdir } from "node:os"
import path from "node:path"
import { fileURLToPath } from "node:url"
import {
  applyPlan,
  buildPlan,
  checkEnv,
  checkWorkspace,
  parseEnvNames,
  planNpm,
} from "../../scripts/bootstrap.mjs"

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

test("checkEnv учитывает env-требования активного профиля", async () => {
  const root = await mkdtemp(path.join(tmpdir(), "profenv-"))
  const cfg = path.join(root, "configs")
  await mkdir(path.join(root, "profiles", "slider"), { recursive: true })
  await mkdir(cfg, { recursive: true })
  await writeFile(path.join(cfg, "env.schema.json"), JSON.stringify({ vars: [] }), "utf8")
  await writeFile(path.join(cfg, "project.json"), JSON.stringify({ active: "slider" }), "utf8")
  await writeFile(
    path.join(root, "profiles", "slider", "project.json"),
    JSON.stringify({ id: "slider", name: "Slider", env: ["SLIDER_TOKEN"] }),
    "utf8",
  )
  const issues = await checkEnv(cfg, root, new Set())
  assert.ok(issues.some((issue) => issue.includes("SLIDER_TOKEN")))
  assert.deepEqual(await checkEnv(cfg, root, new Set(["SLIDER_TOKEN"])), [])
})

test("buildPlan: отсутствующий required-репо попадает в клоны", async () => {
  const root = await mkdtemp(path.join(tmpdir(), "pilot-"))
  const cfg = path.join(root, "configs")
  await mkdir(cfg, { recursive: true })
  await mkdir(path.join(root, "present"), { recursive: true })
  const repo = (id) => ({
    id,
    path: id,
    url: `https://example/${id}.git`,
    access: "read-only",
    required: true,
    index: false,
    contextArtifacts: false,
    defaultBranch: "main",
  })
  await writeFile(
    path.join(cfg, "workspace.json"),
    JSON.stringify({ root: "..", repos: [repo("present"), repo("missing")] }),
    "utf8",
  )
  const plan = buildPlan(cfg, root)
  assert.deepEqual(plan.clones.map((c) => c.id), ["missing"])
})

test("planNpm: при наличии node_modules возвращает null, иначе — команду", async () => {
  const root = await mkdtemp(path.join(tmpdir(), "npm-"))
  assert.ok(planNpm(root))
  await mkdir(path.join(root, "tools", "mcp-runtime", "node_modules"), { recursive: true })
  assert.equal(planNpm(root), null)
})

test("applyPlan уважает skip-флаги и вызывает run только для не-пропущенных шагов", () => {
  const plan = {
    rootDir: ".",
    clones: [{ id: "x", action: "clone", command: ["git", "clone", "u", "p"] }],
    npm: { id: "mcp-runtime", action: "npm", command: ["npm", "ci"] },
    compose: { id: "qdrant", action: "compose", command: ["docker", "compose", "up", "-d"] },
  }
  let calls = 0
  const run = () => {
    calls += 1
    return { status: 0 }
  }
  const results = applyPlan(plan, run, { skipClone: true, skipNpm: false, skipCompose: true })
  assert.equal(calls, 1)
  assert.deepEqual(
    results.map((r) => r.status),
    ["skipped", "done", "skipped"],
  )
})

test("applyPlan: ненулевой статус -> failed", () => {
  const plan = {
    rootDir: ".",
    clones: [{ id: "x", action: "clone", command: ["git", "clone", "u", "p"] }],
    npm: null,
    compose: null,
  }
  const results = applyPlan(plan, () => ({ status: 1 }), {})
  assert.deepEqual(results, [{ id: "x", action: "clone", status: "failed" }])
})
