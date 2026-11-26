/**
 * 费用看板数据类型与接口取数。所有金额/预算/使用率/排行/趋势均由后端按 PRD 5.x 口径计算
 * （backend/app/insight/cost.py → /api/vm/cost/*），前端只做展示；DA 范围由后端按角色裁剪。
 */
import { addMonths, format, startOfMonth } from "date-fns"

import { useApi } from "@/api/use-api"
import { filterParams } from "@/api/params"
import { daName, UNMAPPED_DA_LABEL } from "@/data/dict"
import type { AccountSource, AccountType, Identity } from "@/data/types"
import { useDashboard } from "@/context/dashboard"

export const UNMAPPED_KEY = "__unmapped__"

export type RankLevel = "da" | "region"

export interface CostOverviewData {
  spend: number
  prevSpend: number | null
  spendMom: number | null
  purchaseSpend: number
  freeSpend: number
  unlabeledSpend: number
  budget: number
  prevBudget: number | null
  budgetMom: number | null
  nPlus: number
  nSuper: number
  unmappedBudget: number
  rate: number | null
  prevRate: number | null
  rateDiff: number | null
  rateNum: number
  rateDen: number
  ytd: number
  ytdPurchase: number
  ytdFree: number
  accountCount: number
  spenders: number
  asOf: string
  fxVersion: string
}

export interface RankRow {
  key: string
  label: string
  level: RankLevel
  unmapped: boolean
  accountCount: number
  budget: number
  spend: number
  purchaseSpend: number
  freeSpend: number
  rate: number | null
  perCapita: number | null
  mom: number | null
  spenders: number
}

export interface PersonRow {
  id: string
  name: string
  phone: string
  /** null = 待映射 */
  daId: string | null
  region: string
  identity: Identity
  accountType: AccountType | null
  source: AccountSource
  enabled: boolean
  budget: number | null
  spend: number
  rate: number | null
  ytd: number
  lastUsedDate: string | null
}

export interface DailyPoint {
  day: number
  date: string
  purchase: number | null
  free: number | null
  total: number | null
  cumulative: number | null
}

export interface CostSummary {
  month: string
  /** 统计月份未结束（花费类环比对比上月同期，预算对比上月整月） */
  partial: boolean
  end: string
  level: RankLevel
  overview: CostOverviewData
  rank: (Omit<RankRow, "level" | "label"> & { label: string })[]
  persons: PersonRow[]
  daily: { points: DailyPoint[]; budget: number }
  totals: { rank_sum: number; detail_sum: number }
}

export interface MonthPoint {
  key: string
  label: string
  /** null = 平台上线前，显示「—」 */
  spend: number | null
}

export interface AccountCostDetail {
  id: string
  budget: number | null
  accountType: AccountType | null
  months: MonthPoint[]
  byFunction: { key: string; label: string; amount: number; ratio: number | null }[]
  note: string
}

/** 费用看板公共查询参数：统计月份 + 全局筛选（后端另按角色裁剪） */
export function useCostParams() {
  const { filters, costMonth } = useDashboard()
  return { month: format(startOfMonth(costMonth), "yyyy-MM"), ...filterParams(filters) }
}

export function useCostSummary() {
  const params = useCostParams()
  const state = useApi<CostSummary>("/vm/cost/summary", params)
  const data = state.data
  const level: RankLevel = data?.level ?? "da"
  const rank: RankRow[] = (data?.rank ?? []).map((r) => ({
    ...r,
    level,
    label: level === "region" ? r.label : r.unmapped ? UNMAPPED_DA_LABEL : daName(r.key),
  }))
  return { ...state, params, rank, level }
}

export function useAccountCost(accountId: string | null, month: Date) {
  return useApi<AccountCostDetail>(accountId ? `/vm/cost/account/${accountId}` : null, {
    month: format(startOfMonth(month), "yyyy-MM"),
  })
}

export const prevMonthOf = (month: Date) => startOfMonth(addMonths(month, -1))
