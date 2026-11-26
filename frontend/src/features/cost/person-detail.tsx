import * as React from "react"
import { SearchIcon } from "lucide-react"

import { EnabledBadge, SourceBadge } from "@/components/dashboard/account-badges"
import { type Column, DataTable, TablePagination, useTableState } from "@/components/dashboard/data-table"
import { ExportMenu } from "@/components/dashboard/export-menu"
import { CardTitleText, DashCard } from "@/components/dashboard/primitives"
import { Input } from "@/components/ui/input"
import { daName } from "@/data/dict"
import { FocusChip } from "@/features/da-drilldown/segmented"
import { maskPhone } from "@/lib/auth"
import type { ExportFormat } from "@/lib/export"
import { EMPTY, fmtDate, fmtInt, fmtMoney } from "@/lib/format"

import type { PersonRow } from "./cost-data"

/** 「86%（516.00/600）」 */
export function fmtRateWithParts(row: Pick<PersonRow, "rate" | "spend" | "budget">) {
  if (row.budget == null || row.rate == null) return EMPTY
  return `${Math.round(row.rate * 100)}%（${fmtMoney(row.spend)}/${fmtInt(row.budget)}）`
}

const columns: Column<PersonRow>[] = [
  { key: "name", header: "姓名", sortValue: (r) => r.name, cell: () => null },
  { key: "id", header: "账号ID", sortValue: (r) => r.id, cell: (r) => r.id },
  { key: "phone", header: "联系电话", sortValue: (r) => r.phone, cell: (r) => maskPhone(r.phone) },
  { key: "da", header: "所属DA", sortValue: (r) => daName(r.daId), cell: (r) => daName(r.daId) },
  { key: "region", header: "大区", sortValue: (r) => r.region, cell: (r) => r.region },
  { key: "identity", header: "用户身份", sortValue: (r) => r.identity, cell: (r) => r.identity },
  {
    key: "type",
    header: "账号类型",
    sortValue: (r) => r.accountType,
    cell: (r) => r.accountType ?? <span className="text-muted-foreground">待映射</span>,
  },
  { key: "source", header: "账号来源标签", sortValue: (r) => r.source, cell: (r) => <SourceBadge source={r.source} /> },
  {
    key: "enabled",
    header: "可用状态",
    sortValue: (r) => (r.enabled ? 1 : 0),
    cell: (r) => <EnabledBadge enabled={r.enabled} />,
  },
  {
    key: "budget",
    header: "月度预算",
    align: "right",
    sortValue: (r) => r.budget,
    cell: (r) => (r.budget == null ? <span className="text-muted-foreground">待映射</span> : fmtInt(r.budget)),
  },
  { key: "spend", header: "本月花费", align: "right", sortValue: (r) => r.spend, cell: (r) => fmtMoney(r.spend) },
  { key: "rate", header: "预算使用率", align: "right", sortValue: (r) => r.rate, cell: (r) => fmtRateWithParts(r) },
  { key: "ytd", header: "本年累计花费", align: "right", sortValue: (r) => r.ytd, cell: (r) => fmtMoney(r.ytd) },
  { key: "lastUsed", header: "最近使用日期", sortValue: (r) => r.lastUsedDate, cell: (r) => fmtDate(r.lastUsedDate) },
]

export const PERSON_DEFAULT_SORT = { key: "spend", dir: "desc" } as const

export const PersonDetail = React.forwardRef<
  HTMLDivElement,
  {
    rows: PersonRow[]
    search: string
    onSearchChange: (value: string) => void
    presetLabel: string | null
    onClearPreset: () => void
    onOpenAccount: (row: PersonRow) => void
    onExport: (format: ExportFormat) => void | Promise<void>
  }
>(function PersonDetail(
  { rows, search, onSearchChange, presetLabel, onClearPreset, onOpenAccount, onExport },
  ref
) {
  const cols = React.useMemo<Column<PersonRow>[]>(() => {
    const link = (r: PersonRow, text: string) => (
      <button
        type="button"
        data-open-sheet="cost"
        className="font-medium text-primary hover:underline"
        onClick={() => onOpenAccount(r)}
      >
        {text}
      </button>
    )
    return columns.map((c) => {
      if (c.key === "name") return { ...c, cell: (r: PersonRow) => link(r, r.name) }
      if (c.key === "id") return { ...c, cell: (r: PersonRow) => link(r, r.id) }
      return c
    })
  }, [onOpenAccount])
  const table = useTableState(rows, cols, { ...PERSON_DEFAULT_SORT })

  React.useEffect(() => {
    table.setPage(1)
    // 筛选 / 搜索 / 带入条件变化时回到第一页
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [rows])

  return (
    <DashCard ref={ref} className="scroll-mt-48 gap-4">
      <div className="flex flex-wrap items-center justify-between gap-3 px-6">
        <div className="flex items-center gap-3">
          <CardTitleText>个人费用明细</CardTitleText>
          {presetLabel && <FocusChip label={presetLabel} onClear={onClearPreset} />}
        </div>
        <div className="flex items-center gap-2">
          <div className="relative">
            <SearchIcon className="pointer-events-none absolute top-1/2 left-2.5 size-4 -translate-y-1/2 text-muted-foreground" />
            <Input
              value={search}
              onChange={(e) => onSearchChange(e.target.value)}
              placeholder="按姓名或账号ID搜索"
              className="h-8 w-56 pl-8"
            />
          </div>
          <ExportMenu
            label="导出 XLSX / CSV"
            hint="导出当前筛选条件下的 DA/大区汇总与个人明细（XLSX 两个 Sheet / CSV 两个文件），数据与页面一致"
            onExport={onExport}
          />
        </div>
      </div>
      <DataTable
        columns={cols}
        rows={table.pageRows}
        rowKey={(r) => r.id}
        sort={table.sort}
        onSortChange={table.onSortChange}
        empty="当前筛选条件下暂无账号"
      />
      {rows.length > 0 && (
        <TablePagination
          page={table.page}
          pageSize={table.pageSize}
          total={rows.length}
          onPageChange={table.setPage}
          onPageSizeChange={table.setPageSize}
        />
      )}
    </DashCard>
  )
})
