#!/usr/bin/env node
/**
 * Bootstrap control plane.
 * Режимы: --plan (по умолчанию), --check (read-only готовность), --apply (подготовка окружения).
 * --apply выполняется на целевой машине: клоны отсутствующих required-репозиториев, npm ci MCP-runtime,
 * docker compose up. Идемпотентно; ничего не удаляет; клиентские конфиги не пишет. Индексация SocratiCode
 * скриптом невозможна (нужны MCP-инструменты) и фиксируется как manual step.
 */
import { readFile, writeFile, mkdir } from "node:fs/promises"
import { existsSync, readFileSync } from "node:fs"
import { spawnSync } from "node:child_process"
import path from "node:path"

const isAbsolute = (p) => path.isAbsolute(p) || /^[a-zA-Z]:/.test(p)

export function parseEnvNames(text) {
  const names = new Set()
  for (const line of text.split(/\r?\n/)) {
    const m = /^([A-Za-z_][A-Za-z0-9_]*)=/.exec(line)
    if (m) names.add(m[1])
  }
  return names
}

export function loadWorkspace(configsDir) {
  return JSON.parse(readFileSync(path.join(configsDir, "workspace.json"), "utf8"))
}

// --- read-only проверки ---

export function checkWorkspace(configsDir, rootDir) {
  const manifest = loadWorkspace(configsDir)
  const issues = []
  for (const repo of manifest.repos ?? []) {
    if (isAbsolute(repo.path)) issues.push(`workspace: absolute path: ${repo.id}`)
    if (repo.required && !existsSync(path.resolve(rootDir, repo.path))) {
      issues.push(`workspace: отсутствует ${repo.id} -> ${repo.path} (git clone, см. REPOSITORIES.md)`)
    }
  }
  return issues
}

export async function checkEnv(configsDir, rootDir, provided) {
  const schema = JSON.parse(await readFile(path.join(configsDir, "env.schema.json"), "utf8"))
  let names = provided
  if (!names) {
    const envPath = path.join(rootDir, ".env")
    names = existsSync(envPath) ? parseEnvNames(await readFile(envPath, "utf8")) : new Set()
  }
  const missing = []
  for (const item of schema.vars ?? []) {
    if (item.required && !names.has(item.name)) {
      missing.push(`env: нет имени ${item.name} (заполни .env из .env.example)`)
    }
  }
  return missing
}

export async function checkMcp(configsDir, rootDir) {
  const manifest = JSON.parse(await readFile(path.join(configsDir, "mcp", "servers.json"), "utf8"))
  const expected = (manifest.servers ?? []).map((s) => s.name)
  const files = [".mcp.json", ".vscode/mcp.json", ".codex/config.toml", ".opencode/opencode.jsonc"]
  const issues = []
  for (const rel of files) {
    const filePath = path.join(rootDir, rel)
    if (!existsSync(filePath)) {
      issues.push(`mcp: нет файла ${rel}`)
      continue
    }
    const text = await readFile(filePath, "utf8")
    for (const name of expected) {
      if (!text.includes(`"${name}"`) && !text.includes(`[mcp_servers.${name}]`)) {
        issues.push(`mcp: ${rel} не содержит сервер ${name}`)
      }
    }
  }
  return issues
}

// --- планировщики --apply (чистые, без сайд-эффектов) ---

export function planClones(configsDir, rootDir) {
  const manifest = loadWorkspace(configsDir)
  const clones = []
  for (const repo of manifest.repos ?? []) {
    if (repo.required && !existsSync(path.resolve(rootDir, repo.path))) {
      clones.push({
        id: repo.id,
        action: "clone",
        command: ["git", "clone", repo.url, path.resolve(rootDir, repo.path)],
      })
    }
  }
  return clones
}

export function planNpm(rootDir) {
  const modules = path.join(rootDir, "tools", "mcp-runtime", "node_modules")
  if (existsSync(modules)) return null
  return { id: "mcp-runtime", action: "npm", command: ["npm", "ci", "--prefix", "tools/mcp-runtime"] }
}

export function planCompose(rootDir) {
  if (!existsSync(path.join(rootDir, "compose.socraticode.yaml"))) return null
  return {
    id: "qdrant",
    action: "compose",
    command: ["docker", "compose", "-f", "compose.socraticode.yaml", "up", "-d"],
  }
}

export function buildPlan(configsDir, rootDir) {
  return {
    rootDir,
    clones: planClones(configsDir, rootDir),
    npm: planNpm(rootDir),
    compose: planCompose(rootDir),
  }
}

export function applyPlan(plan, run, flags = {}) {
  const results = []
  const exec = (step, skip) => {
    if (skip) {
      results.push({ id: step.id, action: step.action, status: "skipped" })
      return
    }
    const res = run(step.command)
    results.push({ id: step.id, action: step.action, status: res && res.status === 0 ? "done" : "failed" })
  }
  for (const clone of plan.clones) exec(clone, flags.skipClone)
  if (plan.npm) exec(plan.npm, flags.skipNpm)
  if (plan.compose) exec(plan.compose, flags.skipCompose)
  return results
}

export function manualIndexSteps(configsDir, rootDir) {
  const manifest = loadWorkspace(configsDir)
  return (manifest.repos ?? [])
    .filter((repo) => repo.index && existsSync(path.resolve(rootDir, repo.path)))
    .map((repo) => `codebase_index(projectPath="<abs>/${repo.path}")`)
}

const defaultRun = (command) =>
  spawnSync(command[0], command.slice(1), { stdio: "inherit", shell: process.platform === "win32" })

async function writeReceipt(repoRoot, payload) {
  const dir = path.join(repoRoot, ".reports")
  await mkdir(dir, { recursive: true })
  const stamp = new Date().toISOString().replace(/[:.]/g, "-")
  await writeFile(path.join(dir, `bootstrap-${stamp}.json`), JSON.stringify(payload, null, 2) + "\n", "utf8")
}

async function main() {
  const args = process.argv.slice(2)
  const repoRoot = process.cwd()
  const configsDir = path.join(repoRoot, "configs")

  if (args.includes("--apply")) {
    const flags = {
      skipClone: args.includes("--skip-clone"),
      skipNpm: args.includes("--skip-npm"),
      skipCompose: args.includes("--skip-compose"),
    }
    const plan = buildPlan(configsDir, repoRoot)
    console.log(
      `bootstrap apply: клоны:${plan.clones.length}, npm:${plan.npm ? 1 : 0}, compose:${plan.compose ? 1 : 0}`,
    )
    const results = applyPlan(plan, defaultRun, flags)
    for (const r of results) console.log(`  - ${r.action} ${r.id}: ${r.status}`)
    const manual = manualIndexSteps(configsDir, repoRoot)
    if (manual.length > 0) {
      console.log("manual session step (индексация в сессии):")
      for (const step of manual) console.log(`  - ${step}`)
    }
    await writeReceipt(repoRoot, { mode: "apply", results, manual })
    if (results.some((r) => r.status === "failed")) process.exitCode = 1
    return
  }

  const mode = args.includes("--check") ? "check" : "plan"
  const workspace = checkWorkspace(configsDir, repoRoot)
  const env = await checkEnv(configsDir, repoRoot)
  const mcp = await checkMcp(configsDir, repoRoot)
  const issues = [...workspace, ...env, ...mcp]

  console.log(`bootstrap ${mode}: проверено — workspace:${workspace.length}, env:${env.length}, mcp:${mcp.length}`)
  for (const issue of issues) console.log(`  - ${issue}`)
  if (mode === "check") {
    await writeReceipt(repoRoot, { mode, workspace, env, mcp })
  }
  if (mode === "check" && issues.length > 0) process.exitCode = 1
}

main().catch((e) => {
  console.error(`bootstrap: ошибка ${e.message}`)
  process.exitCode = 1
})
