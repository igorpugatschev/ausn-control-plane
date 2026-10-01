import { test } from "node:test"
import assert from "node:assert/strict"
import { mkdir, mkdtemp, writeFile } from "node:fs/promises"
import { tmpdir } from "node:os"
import path from "node:path"
import { fileURLToPath } from "node:url"
import { activeId, loadActive, validateProfile, workspaceRegistry } from "../profile.mjs"

const here = path.dirname(fileURLToPath(import.meta.url))
const repoRoot = path.resolve(here, "..", "..")

test("дефолтный профиль — ausn", () => {
  assert.equal(activeId(repoRoot), "ausn")
  assert.equal(loadActive(repoRoot).id, "ausn")
})

test("неизвестный профиль — ошибка", async () => {
  const root = await mkdtemp(path.join(tmpdir(), "prof-"))
  await mkdir(path.join(root, "configs"), { recursive: true })
  await writeFile(path.join(root, "configs", "project.json"), JSON.stringify({ active: "nope" }), "utf8")
  assert.throws(() => loadActive(root), /Профиль не найден/)
})

test("абсолютный путь — нарушение", () => {
  assert.ok(validateProfile({ id: "x", name: "X", workspaceRoot: "C:\\abs" }).length > 0)
  assert.deepEqual(validateProfile({ id: "x", name: "X", workspaceRoot: ".." }), [])
})

test("реестр репозиториев: по умолчанию общий configs/workspace.json", () => {
  assert.equal(workspaceRegistry(repoRoot), path.join(repoRoot, "configs", "workspace.json"))
})
