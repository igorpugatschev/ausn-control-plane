#!/usr/bin/env node
/**
 * Скаффолд нового профиля проекта: создаёт profiles/<id>/ и заготовку project.json.
 *
 * Использование:
 *   node scripts/new-project.mjs --id myservice --name "My Service"
 *   node scripts/new-project.mjs --id demo --name "Demo" --root <каталог> [--force]
 *
 * Значения (стенды, MCP, Jira, репозитории) нужно заполнить вручную — см. README профиля.
 */
import { existsSync, mkdirSync, readFileSync, writeFileSync } from "node:fs"
import path from "node:path"
import { validateProfile } from "../tools/profile.mjs"

const ID_RE = /^[a-z][a-z0-9-]*$/

export function scaffoldProject({ root, id, name, force = false }) {
  if (!ID_RE.test(id ?? "")) throw new Error(`Некорректный id профиля: ${id} (нужно [a-z][a-z0-9-]*)`)
  if (!name || !String(name).trim()) throw new Error("Не указано имя профиля (--name)")
  const profileDir = path.join(root, "profiles", id)
  const profileFile = path.join(profileDir, "project.json")
  if (existsSync(profileFile) && !force) {
    throw new Error(`Профиль уже существует: ${profileFile} (используйте --force для перезаписи)`)
  }
  const profile = {
    id,
    name: String(name).trim(),
    workspaceRoot: "..",
    repoPrefix: id,
    controlPlanePath: path.basename(path.resolve(root)),
    productRepo: `${id}-qa-project`,
    contextRepos: [],
    stands: {},
    mcp: {},
    jira: { projectKey: "" },
    zephyr: { folders: { backend: "Backend", frontend: "Frontend", common: "Общее" } },
    taxonomy: { casePrefix: "[AUTO]", locale: "ru" },
    models: { repos: ["control-plane"], system: "models/system.json" },
    workspace: "workspace.json",
  }
  const issues = validateProfile(profile)
  if (issues.length > 0) throw new Error(`Профиль невалиден: ${issues.join("; ")}`)

  for (const sub of ["skills", "docs", "models"]) mkdirSync(path.join(profileDir, sub), { recursive: true })
  writeFileSync(profileFile, JSON.stringify(profile, null, 2) + "\n", "utf8")
  writeFileSync(
    path.join(profileDir, "workspace.json"),
    JSON.stringify({ root: "..", repos: [] }, null, 2) + "\n",
    "utf8",
  )
  writeFileSync(
    path.join(profileDir, "README.md"),
    `# Профиль ${id}\n\nЗаполните \`project.json\`: стенды, эндпоинты MCP, Jira, список репозиториев.\n` +
      `Доменные навыки — в \`skills/\`, доки/отчёты — в \`docs/\`, модели codemap — в \`models/\`.\n` +
      `Активировать: \`configs/project.json\` → \`{"active": "${id}"}\` или env \`PROJECT_PROFILE=${id}\`.\n`,
    "utf8",
  )
  return { profileFile, profile }
}

function parseArgs(argv) {
  const args = { force: false }
  for (let i = 0; i < argv.length; i += 1) {
    const token = argv[i]
    if (token === "--force") args.force = true
    else if (token === "--id") args.id = argv[++i]
    else if (token === "--name") args.name = argv[++i]
    else if (token === "--root") args.root = argv[++i]
  }
  return args
}

function main() {
  const args = parseArgs(process.argv.slice(2))
  const root = path.resolve(args.root ?? process.cwd())
  try {
    const { profileFile } = scaffoldProject({ root, id: args.id, name: args.name, force: args.force })
    console.log(`создан профиль: ${profileFile}`)
    console.log("дальше: заполнить значения, активировать в configs/project.json, обновить runs (bootstrap --plan)")
  } catch (error) {
    console.error(`new-project: ${error.message}`)
    process.exitCode = 1
  }
}

if (import.meta.url === `file://${process.argv[1]}` || process.argv[1]?.endsWith("new-project.mjs")) {
  main()
}
