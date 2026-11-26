import { format } from "date-fns"

import type { Period } from "@/data/types"

export const EMPTY = "—"

const intFmt = new Intl.NumberFormat("zh-CN", { maximumFractionDigits: 0 })
const moneyFmt = new Intl.NumberFormat("zh-CN", {
  minimumFractionDigits: 2,
  maximumFractionDigits: 2,
})

export function fmtInt(value: number | null | undefined) {
  if (value == null || Number.isNaN(value)) return EMPTY
  return intFmt.format(Math.round(value))
}

/** 金额，保留 2 位小数，千分位 */
export function fmtMoney(value: number | null | undefined) {
  if (value == null || Number.isNaN(value)) return EMPTY
  return moneyFmt.format(value)
}

export function fmtDecimal(value: number | null | undefined, digits = 1) {
  if (value == null || !Number.isFinite(value)) return EMPTY
  return value.toFixed(digits)
}

/** 比率 → 百分比字符串，ratio 为 0~1 */
export function fmtPct(ratio: number | null | undefined, digits = 1) {
  if (ratio == null || !Number.isFinite(ratio)) return EMPTY
  return `${(ratio * 100).toFixed(digits)}%`
}

export function safeRatio(numerator: number, denominator: number) {
  return denominator > 0 ? numerator / denominator : null
}

/** 环比：(cur - prev) / prev；prev 为 0 / 无数据时返回 null（显示「—」） */
export function momChange(current: number | null, previous: number | null) {
  if (current == null || previous == null || previous === 0) return null
  return (current - previous) / previous
}

/** 带符号的百分比，如 +2.6% / -5.4% */
export function fmtSignedPct(ratio: number | null | undefined, digits = 1) {
  if (ratio == null || !Number.isFinite(ratio)) return EMPTY
  const v = ratio * 100
  return `${v > 0 ? "+" : ""}${v.toFixed(digits)}%`
}

/** 百分点差（pp） */
export function fmtSignedPp(diff: number | null | undefined, digits = 1) {
  if (diff == null || !Number.isFinite(diff)) return EMPTY
  const v = diff * 100
  return `${v > 0 ? "+" : ""}${v.toFixed(digits)}pp`
}

export function fmtDate(date: Date | string | null | undefined, pattern = "yyyy/MM/dd") {
  if (!date) return EMPTY
  return format(typeof date === "string" ? new Date(date) : date, pattern)
}

export function fmtPeriod(period: Period) {
  return `${fmtDate(period.start)} - ${fmtDate(period.end)}`
}
