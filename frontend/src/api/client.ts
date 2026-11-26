/** 后端接口客户端。角色由请求头传递：生产环境由网关注入 X-Role / X-Managed-DAs，本地联调用侧边栏「身份」切换（localStorage）。
 *  数据范围由后端按这两个头校验，前端参数不构成权限边界。 */
import type { Role } from "@/data/types"

export interface Session {
  role: Role
  /** 逗号分隔的授权 DA 编码（DA 管理员 / 其他角色） */
  managed: string
}

const KEY = "rogen.session"
export function getSession(): Session {
  try {
    const s = JSON.parse(localStorage.getItem(KEY) || "")
    if (s?.role) return s
  } catch {
    /* ignore */
  }
  return { role: "super_admin", managed: "" }
}
export function setSession(s: Session) {
  localStorage.setItem(KEY, JSON.stringify(s))
}

export type Params = Record<string, string | number | boolean | null | undefined | string[]>

export function qs(p: Params): string {
  const u = new URLSearchParams()
  for (const [k, v] of Object.entries(p)) {
    if (v === undefined || v === null || v === "" || (Array.isArray(v) && v.length === 0)) continue
    u.set(k, Array.isArray(v) ? v.join(",") : String(v))
  }
  return u.toString()
}

function headers(): HeadersInit {
  const s = getSession()
  const h: Record<string, string> = { "X-Role": s.role }
  if (s.managed) h["X-Managed-DAs"] = s.managed
  return h
}

export async function api<T = any>(path: string, params: Params = {}, init: RequestInit = {}): Promise<T> {
  const query = qs(params)
  const res = await fetch(`/api${path}${query ? `?${query}` : ""}`, { ...init, headers: { ...headers(), ...(init.headers ?? {}) } })
  if (!res.ok) {
    let detail = res.statusText
    try {
      detail = (await res.json()).detail ?? detail
    } catch {
      /* ignore */
    }
    throw new Error(`${res.status} ${detail}`)
  }
  return res.json()
}

/** 带角色头下载导出文件（<a href> 不会带自定义请求头）。 */
export async function download(path: string, params: Params = {}) {
  const res = await fetch(`/api${path}?${qs(params)}`, { headers: headers() })
  if (!res.ok) throw new Error(`导出失败：${res.status}`)
  const cd = res.headers.get("content-disposition") ?? ""
  const m = /filename\*=UTF-8''([^;]+)/.exec(cd)
  const blob = await res.blob()
  const url = URL.createObjectURL(blob)
  const a = document.createElement("a")
  a.href = url
  a.download = m ? decodeURIComponent(m[1]) : "export"
  a.click()
  URL.revokeObjectURL(url)
}
