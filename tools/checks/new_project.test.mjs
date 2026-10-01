import { test } from "node:test"
import assert from "node:assert/strict"
import { existsSync } from "node:fs"
import { mkdtemp, readFile } from "node:fs/promises"
import { tmpdir } from "node:os"
import path from "node:path"
import { scaffoldProject } from "../../scripts/new-project.mjs"
import { validateProfile } from "../../tools/profile.mjs"

test("создаёт профиль с валидным project.json", async () => {
  const root = await mkdtemp(path.join(tmpdir(), "newproj-"))
  const { profileFile, profile } = scaffoldProject({ root, id: "demo", name: "Demo Service" })
  assert.ok(existsSync(profileFile))
  assert.deepEqual(validateProfile(profile), [])
  const written = JSON.parse(await readFile(profileFile, "utf8"))
  assert.equal(written.id, "demo")
  assert.ok(existsSync(path.join(root, "profiles", "demo", "skills")))
})

test("повторный запуск без --force отклоняется", async () => {
  const root = await mkdtemp(path.join(tmpdir(), "newproj2-"))
  scaffoldProject({ root, id: "demo", name: "Demo" })
  assert.throws(() => scaffoldProject({ root, id: "demo", name: "Demo" }), /уже существует/)
  assert.ok(scaffoldProject({ root, id: "demo", name: "Demo", force: true }).profileFile)
})

test("некорректный id отклоняется", async () => {
  const root = await mkdtemp(path.join(tmpdir(), "newproj3-"))
  assert.throws(() => scaffoldProject({ root, id: "Bad_Id", name: "X" }), /Некорректный id/)
})
