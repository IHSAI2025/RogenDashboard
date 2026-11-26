import * as React from "react"

import {
  type Column,
  DataTable,
  TablePagination,
  useTableState,
} from "@/components/dashboard/data-table"
import { ExportMenu } from "@/components/dashboard/export-menu"
import { CardTitleText, DashCard, Trend } from "@/components/dashboard/primitives"
import { download } from "@/api/client"
import { useScopeParams } from "@/api/params"
import { DATA_AS_OF, META } from "@/data/dict"
import type { GlobalFilters, Period } from "@/data/types"
import { describeFilters } from "@/data/selectors"
import type { ExportFormat } from "@/lib/export"
import { fmtDate, fmtDecimal, fmtInt, fmtPct } from "@/lib/format"

import { DIMENSION_LABEL, type Dimension, type Focus, type GroupRow, exportParams } from "./data"

function activeRateMom(r: GroupRow) {
  const cur = r.activeRate.rate
  const prev = r.prev?.activeRate.rate
  return cur != null && prev != null ? cur - prev : null
}

function buildColumns(dim: Dimension, asOf: string): Column<GroupRow>[] {
  const num = (
    key: string,
    header: string,
    group: string,
    get: (r: GroupRow) => number | null,
    render: (v: number | null) => React.ReactNode = fmtInt
  ): Column<GroupRow> => ({
    key,
    header,
    group,
    align: "right",
    sortValue: get,
    cell: (r) => render(get(r)),
  })

  return [
    {
      key: "label",
      header: DIMENSION_LABEL[dim],
      group: "",
      sticky: true,
      width: 140,
      sortValue: (r) => r.label,
      cell: (r) => <span className="font-medium">{r.label}</span>,
    },
    num("quota", "已配置额度", "账号资源", (r) => r.quota),
    num("opened", "累计开通账号数", "账号资源", (r) => r.opened),
    num("importRate", "额度导入率", "账号资源", (r) => r.importRate, (v) => fmtPct(v)),
    num("effective", "有效账号数", "使用状态", (r) => r.effective),
    num("active", "活跃账号数", "使用状态", (r) => r.active),
    num("activeRate", "活跃率", "使用状态", (r) => r.activeRate.rate, (v) => fmtPct(v)),
    num("featureTotal", "功能使用总次数", "功能使用", (r) => r.featureTotal),
    num("perActive", "单活跃账号功能使用次数", "功能使用", (r) => r.perActiveUsage, (v) => fmtDecimal(v)),
    num("genPpt", "PPT生成次数", "内容生成", (r) => r.gen.ppt),
    num("genTweet", "推文生成次数", "内容生成", (r) => r.gen.tweet),
    ...(META.poster_live ? [num("genPoster", "海报生成次数", "内容生成", (r) => r.gen.poster)] : []),
    num("genTotal", "总生成次数", "内容生成", (r) => r.gen.total),
    num("expPpt", "PPT导出次数", "内容导出", (r) => r.exp.ppt),
    num("expTweet", "推文导出次数", "内容导出", (r) => r.exp.tweet),
    ...(META.poster_live ? [num("expPoster", "海报导出次数", "内容导出", (r) => r.exp.poster)] : []),
    num("expTotal", "总导出次数", "内容导出", (r) => r.exp.total),
    num("exportRate", "导出率", "内容导出", (r) => r.exportRate, (v) => fmtPct(v)),
    num("dormant", "休眠账号数", "闲置预警", (r) => r.dormant),
    num("silent", "沉默账号数", "闲置预警", (r) => r.silent),
    num("silentRate", "沉默率", "闲置预警", (r) => r.silentRate.rate, (v) => fmtPct(v)),
    {
      key: "mom",
      header: "各指标环比",
      group: "",
      align: "right",
      sortValue: activeRateMom,
      cell: (r) => <Trend value={activeRateMom(r)} unit="pp" tone="strong" className="px-0" />,
    },
    {
      key: "asOf",
      header: "数据截至时间",
      group: "",
      align: "right",
      cell: () => asOf,
    },
  ]
}

export function MetricsTableCard({
  rows,
  dim,
  filters,
  focusLabel,
  focusSlot,
  focus,
  includeUnmapped,
}: {
  rows: GroupRow[]
  dim: Dimension
  period: Period
  filters: GlobalFilters
  focusLabel?: string
  focusSlot?: React.ReactNode
  /** 聚焦的 DA/大区/圈长（后端据此过滤导出） */
  focus?: Focus | null
  includeUnmapped?: boolean
}) {
  const asOf = fmtDate(DATA_AS_OF, "yyyy/MM/dd")
  const columns = React.useMemo(() => buildColumns(dim, asOf), [dim, asOf])
  const table = useTableState(rows, columns, { key: "activeRate", dir: "desc" })
  const scope = useScopeParams()

  // 导出由后端生成：含各率分子/分母、统计周期、筛选条件、数据截至时间、口径版本（与页面同一口径）
  const handleExport = (format: ExportFormat) =>
    download("/vm/da/export", {
      ...exportParams(scope, dim, {
        focus,
        includeUnmapped,
        filtersText: describeFilters(filters) + (focusLabel ? `；带入：${focusLabel}` : ""),
      }),
      fmt: format,
    })

  return (
    <DashCard className="gap-4 pt-0 pb-6">
      <div className="flex items-center justify-between gap-4 px-6 pt-6">
        <div className="flex items-center gap-3">
          <span className="text-sm text-muted-foreground">默认按照活跃率从高到低排序，可自行调整</span>
          {focusSlot}
        </div>
        <ExportMenu onExport={handleExport} hint={`导出当前筛选范围内 ${rows.length} 行`} />
      </div>
      <DataTable
        columns={columns}
        rows={table.pageRows}
        rowKey={(r) => r.key}
        sort={table.sort}
        onSortChange={table.onSortChange}
        empty="当前筛选条件下暂无数据"
      />
      <TablePagination
        page={table.page}
        pageSize={table.pageSize}
        total={rows.length}
        onPageChange={table.setPage}
        onPageSizeChange={table.setPageSize}
      />
    </DashCard>
  )
}

export function MetricsTableSection(props: React.ComponentProps<typeof MetricsTableCard>) {
  return (
    <section className="flex flex-col gap-3">
      <div className="px-6">
        <CardTitleText>多指标明细一览表</CardTitleText>
      </div>
      <div className="px-6">
        <MetricsTableCard {...props} />
      </div>
    </section>
  )
}
