/**
 * 字典与周期工具。原 mock.ts 的数据生成部分已移除——所有指标由后端计算（backend/app/metrics/engine.py）。
 * 这里只保留：由 /api/insight/meta 初始化的常量（DA 字典、数据截至日、上线日等）和纯日期工具。
 * 常量用 `export let`，启动时 initDict(meta) 赋值（main.tsx 在渲染前 await 完成），ES 模块 live binding 保证各处读到最新值。
 */
import { addDays, differenceInCalendarDays, endOfMonth, format, isBefore, min as minDate, startOfDay, startOfMonth } from "date-fns"

import type { AccountType, DaInfo, DaNode, Period } from "./types"

export interface Meta {
  as_of: string
  mock_fields: string[]
  poster_live: boolean
  metric_version: string
  fx_version: string
  role: string
  can_cost: boolean
  is_super: boolean
  managed_das: string[] | null
  cost_level: "da" | "region"
  da_groups: Record<string, string[]>
  launch_date: string
  default_month: string
  warn: { import: number; active: number; silent: number }
  regions: string[]
}

export const DA_NAMES: Record<string, string> = {
  BC: "乳腺癌 BC",
  LC: "肺癌 LC",
  GI: "肝癌 GI",
  HEMA: "血液肿瘤 HEMA",
  OPH: "眼科 OPH",
  "NS&RD": "神经科学 NS&RD",
  INF: "流感 INF",
  IMMU: "肾病免疫 IMMU",
  NMA: "全国准入 NMA",
  HSA: "大客户 HSA",
  MCE: "多渠道 MCE",
}

export const UNMAPPED_DA_LABEL = "待映射"
export const MONTHLY_BUDGET: Record<AccountType, number> = { PLUS: 600, SUPER: 1200 }

const parseDay = (s: string) => {
  const [y, m, d] = s.slice(0, 10).split("-").map(Number)
  return new Date(y, m - 1, d)
}

export let META: Meta
export let PLATFORM_LAUNCH: Date = new Date(2026, 6, 1)
export let COST_LAUNCH: Date = new Date(2026, 6, 1)
export let METRIC_VERSION = ""
export let COST_RATE_VERSION = ""
/** 数据截至时间 */
export let DATA_AS_OF: Date = new Date()
/** 最后一个有数据的自然日 */
export let LAST_DATA_DAY: Date = new Date()
/** 「今天」：数据截至日的下一天（本地数据截至 2026-08，不能用系统日期） */
export let TODAY: Date = startOfDay(new Date())
export let DA_TREE: DaNode[] = []
export let DA_LIST: DaInfo[] = []
export let DA_MAP = new Map<string, DaInfo>()
export let REGIONS: string[] = []
/** 全部 DA 叶子编码（initDict 后可用） */
export let ALL_DA_IDS: string[] = []

export function initDict(meta: Meta) {
  META = meta
  PLATFORM_LAUNCH = parseDay(meta.launch_date)
  COST_LAUNCH = PLATFORM_LAUNCH
  METRIC_VERSION = meta.metric_version
  COST_RATE_VERSION = meta.fx_version
  const [d, t] = meta.as_of.split(" ")
  const [hh, mm] = (t ?? "00:00").split(":").map(Number)
  const day = parseDay(d)
  DATA_AS_OF = new Date(day.getFullYear(), day.getMonth(), day.getDate(), hh, mm)
  LAST_DATA_DAY = day
  TODAY = addDays(day, 1)
  DA_TREE = Object.entries(meta.da_groups).map(([group, codes]) => ({
    id: `g-${group}`,
    name: group,
    children: codes.map((c) => ({ id: c, name: DA_NAMES[c] ?? c })),
  }))
  DA_LIST = Object.entries(meta.da_groups).flatMap(([group, codes]) =>
    codes.map((c) => ({ id: c, name: DA_NAMES[c] ?? c, groupId: `g-${group}`, groupName: group, quota: { PLUS: 0, SUPER: 0 } }))
  )
  DA_MAP = new Map(DA_LIST.map((x) => [x.id, x]))
  REGIONS = meta.regions
  ALL_DA_IDS = DA_LIST.map((x) => x.id)
}

export function daName(daId: string | null) {
  if (!daId) return UNMAPPED_DA_LABEL
  return DA_MAP.get(daId)?.name ?? DA_NAMES[daId] ?? UNMAPPED_DA_LABEL
}

/* ---------------- 周期（纯日期工具；口径与后端 metrics/engine.py 的 prev_range 一致） ---------------- */

export function periodKey(period: Period) {
  return `${format(period.start, "yyyyMMdd")}-${format(period.end, "yyyyMMdd")}`
}

/** 周期实际有数据的结束日（不晚于最后数据日） */
export function effectiveEnd(period: Period) {
  return minDate([period.end, LAST_DATA_DAY])
}

export function periodDays(period: Period) {
  return Math.max(0, differenceInCalendarDays(effectiveEnd(period), period.start) + 1)
}

/** 某周期的环比对比周期：月度=上月（当月未结束对比上月同期），自定义=前一个等长周期 */
export function previousPeriod(period: Period): Period {
  if (period.kind === "month") {
    const prevStart = startOfMonth(addDays(period.start, -1))
    const prevEnd = endOfMonth(prevStart)
    const end = effectiveEnd(period)
    if (isBefore(end, period.end)) {
      const sameDay = addDays(prevStart, differenceInCalendarDays(end, period.start))
      return { kind: "month", start: prevStart, end: minDate([sameDay, prevEnd]) }
    }
    return { kind: "month", start: prevStart, end: prevEnd }
  }
  const len = differenceInCalendarDays(period.end, period.start) + 1
  return { kind: "custom", start: addDays(period.start, -len), end: addDays(period.start, -1) }
}

export const ymd = (d: Date) => format(d, "yyyy-MM-dd")
