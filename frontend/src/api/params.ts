import * as React from "react"

import { useDashboard } from "@/context/dashboard"
import { ymd } from "@/data/dict"
import { ALL_DA_IDS, NO_DA } from "@/data/selectors"
import type { GlobalFilters, Period } from "@/data/types"

import type { Params } from "./client"

/** 全局筛选 → 后端公共查询参数（DA 用编码；「全部」不传；未选择 DA 传 __none__ 返回空集）。 */
export function filterParams(filters: GlobalFilters): Params {
  const noneSel = filters.daIds.includes(NO_DA)
  const allSel = filters.daIds.length === 0 || filters.daIds.length === ALL_DA_IDS.length
  return {
    das: noneSel ? "__none__" : allSel ? undefined : filters.daIds,
    account_types: filters.accountType === "all" ? undefined : filters.accountType,
    source_tag: filters.source === "all" ? undefined : filters.source,
    identity: filters.identity === "all" ? undefined : filters.identity,
  }
}

export function periodParams(period: Period): Params {
  return { start: ymd(period.start), end: ymd(period.end), mode: period.kind === "month" ? "mom" : "period" }
}

/** 当前「全局筛选 + 统计周期」对应的后端查询参数；各 Tab 的接口都在此基础上追加自己的参数。 */
export function useScopeParams(): Params {
  const { filters, period } = useDashboard()
  return React.useMemo(() => ({ ...filterParams(filters), ...periodParams(period) }), [filters, period])
}
