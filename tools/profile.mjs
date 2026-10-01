/**
 * Загрузка активного профиля проекта (зеркало tools/profile.py).
 * Активный профиль: env PROJECT_PROFILE -> configs/project.json -> ausn.
 */
import { existsSync, readFileSync } from "node:fs"
import path from "node:path"

export function activeId(root) {
  if (process.env.PROJECT_PROFILE) return process.env.PROJECT_PROFILE.trim()
  const pointer = path.join(root, "configs", "project.json")
  if (existsSync(pointer)) return JSON.parse(readFileSync(pointer, "utf8")).active ?? "ausn"
  return "ausn"
}

export function loadActive(root) {
  const file = path.join(root, "profiles", activeId(root), "project.json")
  if (!existsSync(file)) throw new Error(`Профиль не найден: ${file}`)
  return JSON.parse(readFileSync(file, "utf8"))
}

export function workspaceRegistry(root) {
  const profile = loadActive(root)
  const relative = profile.workspace
  if (relative) {
    const candidate = path.join(root, "profiles", profile.id ?? "", relative)
    if (existsSync(candidate)) return candidate
  }
  return path.join(root, "configs", "workspace.json")
}

export function validateProfile(profile) {
  const issues = []
  for (const key of ["id", "name"]) if (!profile?.[key]) issues.push(`profile: обязательное поле ${key}`)
  for (const key of ["workspaceRoot", "controlPlanePath", "productRepo"]) {
    const value = profile?.[key] ?? ""
    if (value && (value.startsWith("/") || value.includes(":"))) {
      issues.push(`profile: ${key} должен быть относительным: ${value}`)
    }
  }
  if (profile?.env !== undefined && (!Array.isArray(profile.env) || profile.env.some((item) => typeof item !== "string"))) {
    issues.push("profile: env должен быть списком имён переменных")
  }
  return issues
}
