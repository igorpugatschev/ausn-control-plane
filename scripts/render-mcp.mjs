#!/usr/bin/env node
/**
 * Рендер клиентских MCP-конфигов из канонического манифеста `configs/mcp/servers.json`.
 *
 * Инкремент 2 покрывает два «простых» клиента с полным набором данных в манифесте:
 * `.mcp.json` (mcpServers) и `.vscode/mcp.json` (servers, с client-специфичными `type`/`cwd`).
 * `.codex/config.toml` и `.opencode/opencode.jsonc` несут клиент-специфичные поля (таймауты, enabled)
 * и пока покрыты гейтом `mcp_parity.py` (манифест + семантическая сверка), рендер для них — отдельная задача.
 *
 * Режимы: --check (по умолчанию, сравнить рендер с файлами) и --write (записать файлы).
 */
import { readFile, writeFile } from "node:fs/promises"
import { existsSync, readFileSync } from "node:fs"
import path from "node:path"

export function loadManifest(configsDir) {
  return JSON.parse(readFileSync(path.join(configsDir, "mcp", "servers.json"), "utf8"))
}

export function renderMcpJson(manifest) {
  const servers = {}
  for (const server of manifest.servers) {
    servers[server.name] = {
      command: server.command,
      args: [...server.args],
      env: { ...(server.envValues ?? {}) },
    }
  }
  return { mcpServers: servers }
}

export function renderVscode(manifest) {
  const servers = {}
  for (const server of manifest.servers) {
    const entry = { command: server.command, args: [...server.args], env: { ...(server.envValues ?? {}) } }
    if (server.vscode) {
      if (server.vscode.type) entry.type = server.vscode.type
      if (server.vscode.cwd) entry.cwd = server.vscode.cwd
    }
    servers[server.name] = entry
  }
  return { servers }
}

export function renderAll(configsDir, rootDir) {
  const manifest = loadManifest(configsDir)
  return [
    { rel: ".mcp.json", value: renderMcpJson(manifest) },
    { rel: ".vscode/mcp.json", value: renderVscode(manifest) },
  ].map((item) => ({ ...item, file: path.join(rootDir, item.rel) }))
}

export async function checkRendered(configsDir, rootDir) {
  const issues = []
  for (const { rel, value, file } of renderAll(configsDir, rootDir)) {
    if (!existsSync(file)) {
      issues.push(`render: нет файла ${rel}`)
      continue
    }
    const actual = JSON.parse(await readFile(file, "utf8"))
    if (JSON.stringify(actual) !== JSON.stringify(value)) {
      issues.push(`render: ${rel} расходится с рендером из манифеста`)
    }
  }
  return issues
}

export async function writeRendered(configsDir, rootDir) {
  for (const { rel, value, file } of renderAll(configsDir, rootDir)) {
    await writeFile(file, JSON.stringify(value, null, 2) + "\n", "utf8")
    console.log(`написано: ${rel}`)
  }
}

async function main() {
  const args = process.argv.slice(2)
  const repoRoot = process.cwd()
  const configsDir = path.join(repoRoot, "configs")
  if (args.includes("--write")) {
    await writeRendered(configsDir, repoRoot)
    return
  }
  const issues = await checkRendered(configsDir, repoRoot)
  for (const issue of issues) console.log(`  - ${issue}`)
  if (issues.length === 0) console.log("OK: рендер совпадает с .mcp.json и .vscode/mcp.json")
  else process.exitCode = 1
}

main().catch((e) => {
  console.error(`render-mcp: ошибка ${e.message}`)
  process.exitCode = 1
})
