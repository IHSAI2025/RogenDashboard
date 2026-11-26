import * as React from "react"

import { type Params, api } from "@/api/client"
import { useScopeParams } from "@/api/params"
import { DA_MAP, UNMAPPED_DA_LABEL } from "@/data/dict"
import type { AccountType } from "@/data/types"

/* ------------------------------------------------------------------ */
/* 维度                                                                */
/* ------------------------------------------------------------------ */

export type Dimension = "da" | "region" | "leader"

export const DIMENSION_LABEL: Record<Dimension, string> = {
  da: "DA",
  region: "大区",
  leader: "圈长",
}

/** 后端「待映射 DA」分组的 key */
export const UNMAPPED_KEY = "__unmapped__"

export function groupLabel(key: string, dim: Dimension) {
  if (dim === "da") return key === UNMAPPED_KEY ? UNMAPPED_DA_LABEL : (DA_MAP.get(key)?.name ?? key)
  return key
}

/** 带入（聚焦）的 DA / 大区 / 圈长 */
export interface Focus {
  dim: Dimension
  key: string
  label: string
}

/* ------------------------------------------------------------------ */
/* 指标（全部由后端 /api/vm/da/groups 计算，比率为 0~1）                    */
/* ------------------------------------------------------------------ */

export interface TypedRate {
  numerator: number
  denominator: number
  rate: number | null
}

export interface GroupMetrics {
  key: string
  label: string
  /** 已配置额度（仅 DA 维度有） */
  quota: number | null
  quotaByType: Record<AccountType, number> | null
  /** 累计开通（导入）账号数 */
  opened: number
  importRate: number | null
  importRateByType: Record<AccountType, number | null>
  effective: number
  active: number
  dormant: number
  silent: number
  activeRate: TypedRate
  silentRate: TypedRate
  activeRateByType: Record<AccountType, number | null>
  silentRateByType: Record<AccountType, number | null>
  featureTotal: number
  perActiveUsage: number | null
  genAccounts: number
  genConversion: number | null
  perCapitaGen: number | null
  gen: { ppt: number; tweet: number; poster: number; total: number }
  exp: { ppt: number; tweet: number; poster: number; total: number }
  exportRate: number | null
}

export interface GroupRow extends GroupMetrics {
  prev: GroupMetrics | null
}

export interface PlatformMetrics {
  activeRate: TypedRate
  perActiveUsage: number | null
}

const EMPTY_PLATFORM: PlatformMetrics = {
  activeRate: { numerator: 0, denominator: 0, rate: null },
  perActiveUsage: null,
}

/* 同一页面多张卡片会请求相同参数：短时缓存 promise 去重 */
const cache = new Map<string, { at: number; p: Promise<any> }>()
function cachedApi<T>(path: string, params: Params): Promise<T> {
  const key = `${path}?${JSON.stringify(params)}`
  const hit = cache.get(key)
  if (hit && Date.now() - hit.at < 15_000) return hit.p
  const p = api<T>(path, params)
  p.catch(() => cache.delete(key))
  cache.set(key, { at: Date.now(), p })
  return p
}

function useCached<T>(path: string | null, params: Params): { data: T | null; loading: boolean } {
  const key = `${path}?${JSON.stringify(params)}`
  const [state, setState] = React.useState<{ data: T | null; loading: boolean }>({ data: null, loading: !!path })
  React.useEffect(() => {
    if (!path) {
      setState({ data: null, loading: false })
      return
    }
    let off = false
    setState((s) => ({ ...s, loading: true }))
    cachedApi<T>(path, params)
      .then((data) => !off && setState({ data, loading: false }))
      .catch(() => !off && setState((s) => ({ ...s, loading: false })))
    return () => {
      off = true
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [key])
  return state
}

function withLabel(m: GroupMetrics, dim: Dimension): GroupMetrics {
  return { ...m, label: groupLabel(m.key, dim) }
}

function focusParams(focus?: Focus | null): Params {
  return focus ? { focus_dim: focus.dim, focus_key: focus.key } : {}
}

/** 按维度分组的指标（含上一周期，用于环比）。enabled=false 时不请求，返回空。 */
export function useGroups(
  dim: Dimension,
  opts: { focus?: Focus | null; includeUnmapped?: boolean; enabled?: boolean } = {}
): { rows: GroupRow[]; platform: PlatformMetrics; loading: boolean } {
  const scope = useScopeParams()
  const params = { ...scope, dim, include_unmapped: opts.includeUnmapped ? "true" : undefined, ...focusParams(opts.focus) }
  const { data, loading } = useCached<{ rows: any[]; platform: PlatformMetrics }>(opts.enabled === false ? null : "/vm/da/groups", params)
  const rows = React.useMemo<GroupRow[]>(
    () => (data?.rows ?? []).map((r) => ({ ...withLabel(r, dim), prev: r.prev ? withLabel({ ...r.prev, key: r.key }, dim) : null })),
    [data, dim]
  )
  return { rows, platform: data?.platform ?? EMPTY_PLATFORM, loading }
}

/* ------------------------------------------------------------------ */
/* 趋势                                                                */
/* ------------------------------------------------------------------ */

export type Granularity = "week" | "month" | "year"

export interface TrendPoint {
  label: string
  rangeLabel: string
  activeRate: number | null
  silentRate: number | null
  genTotal: number
}

/** 活跃率 / 沉默率 / 总生成次数趋势（随聚焦的 DA/大区/圈长变化） */
export function useTrend(granularity: Granularity, focus?: Focus | null): TrendPoint[] {
  const scope = useScopeParams()
  const { data } = useCached<{ points: TrendPoint[] }>("/vm/da/trend", { ...scope, granularity, ...focusParams(focus) })
  return data?.points ?? []
}

/** 后端导出（XLSX / CSV）：含分子分母、统计周期、筛选条件、数据截至、口径版本 */
export function exportParams(scope: Params, dim: Dimension, opts: { focus?: Focus | null; includeUnmapped?: boolean; filtersText: string }): Params {
  return { ...scope, dim, include_unmapped: opts.includeUnmapped ? "true" : undefined, filters_text: opts.filtersText, ...focusParams(opts.focus) }
}

/** 生成坐标轴「整齐」的区间 */
export function niceDomain(values: number[], step: number, pad = step / 2): [number, number] {
  if (!values.length) return [0, step * 4]
  const min = Math.min(...values) - pad
  const max = Math.max(...values) + pad
  return [Math.max(0, Math.floor(min / step) * step), Math.ceil(max / step) * step]
}
