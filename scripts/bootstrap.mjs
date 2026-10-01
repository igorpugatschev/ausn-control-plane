#!/usr/bin/env node
/**
 * Read-only проверка готовности рабочего места (инкремент 1 переносимости).
 * Режимы: --plan (по умолчанию) и --check. Ничего не создаёт, не клонирует и не меняет.
 */
import { readFile, writeFile, mkdir } from "node:fs/promises"
import { existsSync, readFileSync } from "node:fs"
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

export function checkWorkspace(configsDir, rootDir) {
  const manifest = JSON.parse(readFileSync(path.join(configsDir, "workspace.json"), "utf8"))
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

async function main() {
  const args = process.argv.slice(2)
  const mode = args.includes("--check") ? "check" : "plan"
  const repoRoot = process.cwd()
  const configsDir = path.join(repoRoot, "configs")

  const workspace = checkWorkspace(configsDir, repoRoot)
  const env = await checkEnv(configsDir, repoRoot)
  const mcp = await checkMcp(configsDir, repoRoot)
  const issues = [...workspace, ...env, ...mcp]

  console.log(`bootstrap ${mode}: проверено — workspace:${workspace.length}, env:${env.length}, mcp:${mcp.length}`)
  for (const issue of issues) console.log(`  - ${issue}`)

  if (mode === "check") {
    const dir = path.join(repoRoot, ".reports")
    await mkdir(dir, { recursive: true })
    const stamp = new Date().toISOString().replace(/[:.]/g, "-")
    await writeFile(
      path.join(dir, `bootstrap-${stamp}.json`),
      JSON.stringify({ mode, workspace, env, mcp }, null, 2) + "\n",
      "utf8",
    )
  }
  if (mode === "check" && issues.length > 0) process.exitCode = 1
}

main().catch((e) => {
  console.error(`bootstrap: ошибка ${e.message}`)
  process.exitCode = 1
})
