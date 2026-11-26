import * as React from "react"

import { type Column, DataTable, type SortState, nextSort, sortRows } from "@/components/dashboard/data-table"
import { CardTitleText, DashCard, Trend } from "@/components/dashboard/primitives"
import { Segmented } from "@/features/da-drilldown/segmented"
import { EMPTY, fmtInt, fmtMoney, fmtPct } from "@/lib/format"
import { cn } from "@/lib/utils"

import type { RankLevel, RankRow } from "./cost-data"

const SORT_PRESETS = [
  { value: "spend", label: "按本月花费" },
  { value: "rate", label: "按预算使用率" },
  { value: "perCapita", label: "按人均花费" },
] as const

const DEFAULT_SORT: SortState = { key: "spend", dir: "desc" }

export function DaRanking({
  rows,
  level,
  activeKey,
  onPick,
}: {
  rows: RankRow[]
  level: RankLevel
  activeKey: string | null
  onPick: (row: RankRow) => void
}) {
  const [sort, setSort] = React.useState<SortState | null>(DEFAULT_SORT)
  const levelLabel = level === "da" ? "DA" : "大区"

  const columns = React.useMemo<Column<RankRow>[]>(
    () => [
      {
        key: "label",
        header: levelLabel,
        sortValue: (r) => r.label,
        cell: (r) => (
          <button
            type="button"
            onClick={() => onPick(r)}
            className={cn(
              "font-medium text-primary hover:underline",
              r.unmapped && "text-muted-foreground",
              activeKey === r.key && "underline"
            )}
            title={`在个人费用明细中查看${r.label}`}
          >
            {r.label}
          </button>
        ),
      },
      { key: "accountCount", header: "账号数", align: "right", sortValue: (r) => r.accountCount, cell: (r) => fmtInt(r.accountCount) },
      { key: "budget", header: "本月预算", align: "right", sortValue: (r) => r.budget, cell: (r) => fmtInt(r.budget) },
      { key: "spend", header: "本月花费", align: "right", sortValue: (r) => r.spend, cell: (r) => fmtMoney(r.spend) },
      { key: "purchaseSpend", header: "采购账号费用", align: "right", sortValue: (r) => r.purchaseSpend, cell: (r) => fmtMoney(r.purchaseSpend) },
      { key: "freeSpend", header: "免费账号成本", align: "right", sortValue: (r) => r.freeSpend, cell: (r) => fmtMoney(r.freeSpend) },
      { key: "rate", header: "预算使用率", align: "right", sortValue: (r) => r.rate, cell: (r) => (r.rate == null ? EMPTY : `${fmtPct(r.rate)}（${fmtMoney(r.spend)}/${fmtInt(r.budget)}）`) },
      {
        key: "perCapita",
        header: "人均花费",
        align: "right",
        sortValue: (r) => r.perCapita,
        cell: (r) => (r.perCapita == null ? EMPTY : fmtMoney(r.perCapita)),
      },
      {
        key: "mom",
        header: "本月花费环比",
        align: "right",
        sortValue: (r) => r.mom,
        cell: (r) => <Trend value={r.mom} className="px-0" />,
      },
    ],
    [levelLabel, activeKey, onPick]
  )

  // 「待映射」单列一行，不参与排序，固定在末尾
  const mapped = rows.filter((r) => !r.unmapped)
  const unmapped = rows.filter((r) => r.unmapped)
  const displayRows = [...sortRows(mapped, columns, sort), ...unmapped]

  return (
    <DashCard className="gap-4">
      <div className="flex items-center justify-between gap-4 px-6">
        <div className="flex items-baseline gap-2">
          <CardTitleText>{level === "da" ? "DA费用排行" : "大区费用排行"}</CardTitleText>
          <span className="text-xs text-muted-foreground">点击{levelLabel}名称，下方个人费用明细自动带入该{levelLabel}</span>
        </div>
        <Segmented
          aria-label="排行排序"
          value={sort?.key ?? DEFAULT_SORT.key}
          onValueChange={(key) => setSort({ key, dir: "desc" })}
          options={[...SORT_PRESETS]}
        />
      </div>
      <DataTable
        columns={columns}
        rows={displayRows}
        rowKey={(r) => r.key}
        sort={sort}
        onSortChange={(key) => setSort((cur) => nextSort(cur, key, DEFAULT_SORT))}
        empty="当前筛选条件下暂无数据"
      />
      <p className="px-6 text-xs text-muted-foreground">
        人均花费 = 本月花费 ÷ 本月有花费的账号数；无法映射 DA 的账号单列「待映射」，不归入任何 DA。
      </p>
    </DashCard>
  )
}
