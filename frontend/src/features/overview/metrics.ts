/**
 * 全景看板数据层：所有指标由后端计算（backend/app/insight/vm_overview.py → metrics/engine.py），
 * 这里只做请求、缓存与「加载中」占位。比率均为 0~1 小数，与 fmtPct 约定一致。
 */
import * as React from "react"
import { format } from "date-fns"

import { api } from "@/api/client"
import { useScopeParams } from "@/api/params"
import { useDashboard } from "@/context/dashboard"
import { PLATFORM_LAUNCH } from "@/data/dict"
import { LAST_DATA_DAY } from "@/data/dict"

/* ------------------------------------------------------------------ */
/* 类型                                                                */
/* ------------------------------------------------------------------ */

export interface TypeSplit {
  total: number
  plus: number
  super: number
}

export interface CumulativeSnapshot {
  /** 累计有效账号（累计开通 ∩ 可用状态=正常） */
  valid: TypeSplit
  activated: TypeSplit
  /** 累计开通账号数（含后续停用；PRD：开通即导入） */
  opened: TypeSplit
  quota: TypeSplit
  /** 累计导入率 = 累计开通账号 ÷ 配置额度 */
  importRate: number | null
  activationRate: number | null
  pendingActivation: number
  featureTotal: number
  generation: { total: number; ppt: number; tweet: number }
  exports: { total: number; ppt: number; tweet: number }
}

export interface PeriodSnapshot {
  valid: number
  active: number
  dormant: number
  silent: number
  activeRate: number | null
  dormantRate: number | null
  silentRate: number | null
  /** 登录未使用：休眠 / 沉默账号中周期内登录过的账号数 */
  loginUnusedDormant: number
  loginUnusedSilent: number
  dailyActive: number | null
  featureTotal: number
  dailyFeature: number | null
  perActiveFeature: number | null
  generation: { total: number; ppt: number; tweet: number }
  exports: { total: number; ppt: number; tweet: number }
  dailyGeneration: number | null
  perCapitaGeneration: number | null
  features: Record<"pubmed" | "outline" | "libraryShare" | "ppt" | "tweet" | "poster", number>
}

export interface FunctionRow {
  label: string
  value: number
  /** 占比：主模块=占主模块合计；子模块=组内占比 */
  ratio: number | null
  group?: string
}

export interface OverviewData {
  cumulative: Record<"all" | "core", { asOf: string; current: CumulativeSnapshot; previous: CumulativeSnapshot | null }>
  period: { current: PeriodSnapshot; previous: PeriodSnapshot | null }
  distribution: {
    types: { plus: number; super: number; unmapped: number }
    identities: { customer: number; staff: number }
  }
  functions: {
    core: FunctionRow[]
    subs: FunctionRow[]
    /** 子模块降序累计占比首次达到 50% 的最小 N */
    topN: number
    topShare: number | null
  }
  range: { start: string; end: string; prev: [string, string] | null }
}

/* ------------------------------------------------------------------ */
/* 占位（加载中 / 无对比周期）                                           */
/* ------------------------------------------------------------------ */

const zeroSplit = (): TypeSplit => ({ total: 0, plus: 0, super: 0 })

export const emptyCumulative = (): CumulativeSnapshot => ({
  valid: zeroSplit(),
  activated: zeroSplit(),
  opened: zeroSplit(),
  quota: zeroSplit(),
  importRate: null,
  activationRate: null,
  pendingActivation: 0,
  featureTotal: 0,
  generation: { total: 0, ppt: 0, tweet: 0 },
  exports: { total: 0, ppt: 0, tweet: 0 },
})

export const emptyPeriod = (): PeriodSnapshot => ({
  valid: 0,
  active: 0,
  dormant: 0,
  silent: 0,
  activeRate: null,
  dormantRate: null,
  silentRate: null,
  loginUnusedDormant: 0,
  loginUnusedSilent: 0,
  dailyActive: null,
  featureTotal: 0,
  dailyFeature: null,
  perActiveFeature: null,
  generation: { total: 0, ppt: 0, tweet: 0 },
  exports: { total: 0, ppt: 0, tweet: 0 },
  dailyGeneration: null,
  perCapitaGeneration: null,
  features: { pubmed: 0, outline: 0, libraryShare: 0, ppt: 0, tweet: 0, poster: 0 },
})

/** 率类指标的环比 = 百分点差（0~1 的差值，配合 Trend unit="pp"）；任一为空返回 null */
export function ppDiff(cur: number | null, prev: number | null) {
  return cur == null || prev == null ? null : cur - prev
}

/* ------------------------------------------------------------------ */
/* 请求 + 去重缓存：同一页面多个组件用同一组参数，只发一次请求                     */
/* ------------------------------------------------------------------ */

const TTL_MS = 30_000
const cache = new Map<string, { at: number; promise: Promise<OverviewData> }>()

function fetchOverview(params: Record<string, unknown>): Promise<OverviewData> {
  const key = JSON.stringify(params)
  const hit = cache.get(key)
  if (hit && Date.now() - hit.at < TTL_MS) return hit.promise
  const promise = api<OverviewData>("/vm/overview/snapshots", params as never)
  cache.set(key, { at: Date.now(), promise })
  promise.catch(() => cache.delete(key))
  return promise
}

function useOverviewData() {
  const params = useScopeParams()
  const key = JSON.stringify(params)
  const [state, setState] = React.useState<{ key: string; data: OverviewData | null }>({ key, data: null })
  React.useEffect(() => {
    let off = false
    fetchOverview(params)
      .then((data) => !off && setState({ key, data }))
      .catch(() => !off && setState({ key, data: null }))
    return () => {
      off = true
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [key])
  // 参数切换期间保留上一次数据，避免整页闪成 0
  return state.data
}

/* ------------------------------------------------------------------ */
/* Hooks                                                               */
/* ------------------------------------------------------------------ */

export function usePeriodSnapshots() {
  const data = useOverviewData()
  return React.useMemo(
    () => ({
      current: data?.period.current ?? emptyPeriod(),
      previous: data?.period.previous ?? emptyPeriod(),
      hasPrevious: !!data?.period.previous,
    }),
    [data]
  )
}

/** 累计存量：截至当前周期结束日 vs 截至上一周期结束日。scope：全平台(剔除测试) / 核心业务(再剔除非 DA) */
export function useCumulativeSnapshots(scope: "all" | "core") {
  const data = useOverviewData()
  return React.useMemo(() => {
    const c = data?.cumulative[scope]
    return {
      asOf: c ? new Date(c.asOf) : LAST_DATA_DAY,
      current: c?.current ?? emptyCumulative(),
      previous: c?.previous ?? emptyCumulative(),
      hasPrevious: !!c?.previous,
    }
  }, [data, scope])
}

/** 账号分布 / 功能使用分布 */
export function useDistribution() {
  const data = useOverviewData()
  return React.useMemo(() => data, [data])
}

export const LAUNCH_LABEL = `${format(PLATFORM_LAUNCH, "yyyy/MM/dd")} （上线）`
export const LAST_DAY = LAST_DATA_DAY

/** 趋势：按周/月/年，受 DA/类型/来源/身份筛选，不受统计周期限制（设计稿用 Brush 选可视窗口） */
export interface TrendRow {
  start: string
  end: string
  total: Record<"ppt" | "tweet" | "poster", number>
  perCapita: Record<"ppt" | "tweet" | "poster", number | null>
}

export function useGenerationTrend(granularity: "week" | "month" | "year") {
  const params = useScopeParams()
  const key = JSON.stringify([params, granularity])
  const [state, setState] = React.useState<{ key: string; rows: TrendRow[] | null }>({ key, rows: null })
  React.useEffect(() => {
    let off = false
    api<{ rows: TrendRow[] }>("/vm/overview/trend", { ...params, granularity } as never)
      .then((d) => !off && setState({ key, rows: d.rows }))
      .catch(() => !off && setState({ key, rows: [] }))
    return () => {
      off = true
    }
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [key])
  return state.key === key ? state.rows : null
}

export function useDashboardPeriod() {
  return useDashboard().period
}
