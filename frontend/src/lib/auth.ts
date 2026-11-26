import { type Session, getSession, setSession } from "@/api/client"
import type { Role } from "@/data/types"

export interface CurrentUser {
  name: string
  email: string
  role: Role
  /** DA 管理员的授权 DA 编码；超级管理员为空 */
  authorizedDaIds: string[]
}

const NAMES: Record<Role, string> = { super_admin: "超级管理员", da_admin: "DA 管理员", other: "其他角色" }

/** 当前登录身份：生产由网关注入 X-Role / X-Managed-DAs；本地联调从 localStorage 读（侧边栏可切换）。 */
function build(s: Session): CurrentUser {
  return {
    name: NAMES[s.role],
    email: s.role === "super_admin" ? "全部 DA" : s.managed || "未授权 DA",
    role: s.role,
    authorizedDaIds: s.role === "super_admin" ? [] : s.managed.split(",").filter(Boolean),
  }
}

export const CURRENT_USER: CurrentUser = build(getSession())

export function switchRole(role: Role, managed = "BC") {
  setSession({ role, managed: role === "super_admin" ? "" : managed })
  location.reload()
}

export function canSeeCostTab(user: CurrentUser) {
  return user.role === "super_admin" || user.role === "da_admin"
}

export function canSeeFullPhone(user: CurrentUser) {
  return user.role === "super_admin"
}

/** 联系电话按数据权限脱敏（后端已脱敏下发，这里仅作兜底）：138****1234 */
export function maskPhone(phone: string, user: CurrentUser = CURRENT_USER) {
  if (canSeeFullPhone(user) || phone.length < 7 || phone.includes("*")) return phone
  return `${phone.slice(0, 3)}****${phone.slice(-4)}`
}
