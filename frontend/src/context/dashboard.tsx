import * as React from "react"
import { addMonths, endOfMonth, startOfMonth } from "date-fns"

import { PLATFORM_LAUNCH, TODAY } from "@/data/dict"
import type { GlobalFilters, Period, UsageStatus } from "@/data/types"

export type DashboardTab = "overview" | "da" | "users" | "cost"

export interface UsersPreset {
  status?: UsageStatus | "all"
  /** 带入的大区（来自 DA 下钻点击气泡等） */
  region?: string
  /** 仅看「登录未使用」（休眠/沉默账号中本期登录过的） */
  loginUnused?: boolean
}

export interface CostPreset {
  /** 点击 DA 费用排行中的 DA/大区名称后带入个人费用明细 */
  daId?: string | null
  region?: string
}

interface DashboardContextValue {
  tab: DashboardTab
  setTab: (tab: DashboardTab) => void

  filters: GlobalFilters
  setFilters: (patch: Partial<GlobalFilters>) => void

  /** 月份 toggle 可选的 3 个月（前 2 个月 + 当月） */
  monthOptions: Date[]
  period: Period
  setPeriod: (period: Period) => void

  /** 费用看板统计月份 */
  costMonth: Date
  setCostMonth: (month: Date) => void

  usersPreset: UsersPreset
  openUsers: (preset?: UsersPreset) => void
}

const DashboardContext = React.createContext<DashboardContextValue | null>(null)

export function monthPeriod(month: Date): Period {
  return { kind: "month", start: startOfMonth(month), end: endOfMonth(month) }
}

export const DEFAULT_FILTERS: GlobalFilters = {
  daIds: [],
  accountType: "all",
  source: "all",
  identity: "all",
}

export function DashboardProvider({ children }: { children: React.ReactNode }) {
  const [tab, setTab] = React.useState<DashboardTab>("overview")
  const [filters, setFiltersState] = React.useState<GlobalFilters>(DEFAULT_FILTERS)
  const monthOptions = React.useMemo(
    // 前 2 个月 + 当月；平台上线(2026/07/01)之前的月份无数据，不展示
    () => [-2, -1, 0].map((n) => startOfMonth(addMonths(TODAY, n))).filter((m) => m >= startOfMonth(PLATFORM_LAUNCH)),
    []
  )
  const [period, setPeriod] = React.useState<Period>(() => monthPeriod(TODAY))
  const [costMonth, setCostMonth] = React.useState<Date>(() => startOfMonth(TODAY))
  const [usersPreset, setUsersPreset] = React.useState<UsersPreset>({})

  const setFilters = React.useCallback((patch: Partial<GlobalFilters>) => {
    setFiltersState((prev) => ({ ...prev, ...patch }))
  }, [])

  const openUsers = React.useCallback((preset: UsersPreset = {}) => {
    setUsersPreset({ ...preset })
    setTab("users")
    window.scrollTo({ top: 0, behavior: "smooth" })
  }, [])

  const value = React.useMemo(
    () => ({
      tab,
      setTab,
      filters,
      setFilters,
      monthOptions,
      period,
      setPeriod,
      costMonth,
      setCostMonth,
      usersPreset,
      openUsers,
    }),
    [tab, filters, setFilters, monthOptions, period, costMonth, usersPreset, openUsers]
  )

  return <DashboardContext.Provider value={value}>{children}</DashboardContext.Provider>
}

export function useDashboard() {
  const ctx = React.useContext(DashboardContext)
  if (!ctx) throw new Error("useDashboard must be used inside DashboardProvider")
  return ctx
}
