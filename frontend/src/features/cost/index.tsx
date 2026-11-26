import * as React from "react"
import { format } from "date-fns"

import { download } from "@/api/client"
import { DashCard, SectionHeader } from "@/components/dashboard/primitives"
import { useDashboard } from "@/context/dashboard"
import { DATA_AS_OF } from "@/data/dict"
import type { ExportFormat } from "@/lib/export"
import { fmtDate, fmtMoney } from "@/lib/format"

import { AccountCostSheet } from "./account-cost-sheet"
import { type PersonRow, type RankRow, UNMAPPED_KEY, useCostSummary } from "./cost-data"
import { CostOverview } from "./cost-overview"
import { DaRanking } from "./da-ranking"
import { DailyTrendChart } from "./daily-trend-chart"
import { PersonDetail } from "./person-detail"

interface Preset {
  key: string
  level: RankRow["level"]
  label: string
}

/**
 * 费用看板：金额、预算、排行、明细、趋势全部由后端 /api/vm/cost/summary 按 PRD 5.x 口径计算并按角色裁剪
 * （超管按 DA 排行、DA 管理员按大区排行；其他角色无权访问）。前端只做展示、搜索与「带入」筛选。
 */
export function CostTab() {
  const { filters, costMonth } = useDashboard()
  const { data, loading, error, rank, level, params } = useCostSummary()

  const [preset, setPreset] = React.useState<Preset | null>(null)
  const [search, setSearch] = React.useState("")
  const [selected, setSelected] = React.useState<PersonRow | null>(null)
  const [sheetOpen, setSheetOpen] = React.useState(false)
  const detailRef = React.useRef<HTMLDivElement>(null)

  const allPersons = React.useMemo(() => data?.persons ?? [], [data])
  const persons = React.useMemo(() => {
    const q = search.trim().toLowerCase()
    return allPersons.filter((p) => {
      if (preset) {
        if (preset.level === "region" && p.region !== preset.key) return false
        if (preset.level === "da" && (p.daId ?? UNMAPPED_KEY) !== preset.key) return false
      }
      return !q || p.name.toLowerCase().includes(q) || p.id.toLowerCase().includes(q)
    })
  }, [allPersons, preset, search])

  // 全局筛选或统计月份变化后，带入条件可能失效，统一清空
  React.useEffect(() => {
    setPreset(null)
  }, [filters, costMonth])

  const pickRank = React.useCallback((row: RankRow) => {
    setPreset({ key: row.key, level: row.level, label: row.label })
    requestAnimationFrame(() => detailRef.current?.scrollIntoView({ behavior: "smooth", block: "start" }))
  }, [])

  const openAccount = React.useCallback((row: PersonRow) => {
    setSelected(row)
    setSheetOpen(true)
  }, [])

  const monthLabel = format(costMonth, "yyyy-MM")
  const periodText =
    (data
      ? `统计月份：${monthLabel}（${fmtDate(`${monthLabel}-01`)} - ${fmtDate(data.end)}）`
      : `统计月份：${monthLabel}`) + ` ｜ 数据截至：${data?.overview.asOf ?? fmtDate(DATA_AS_OF, "yyyy-MM-dd HH:mm")}`

  // 导出走后端：范围=当前全局筛选 + 统计月份，由服务端校验角色/脱敏手机号；导出合计与页面一致
  const handleExport = (formatType: ExportFormat) => download("/insight/export/cost", { ...params, fmt: formatType })

  if (error) {
    return <div className="px-6 py-10 text-center text-sm text-destructive">费用数据加载失败：{error}</div>
  }

  const pageSum = persons.reduce((s, p) => s + p.spend, 0)

  return (
    <div className={loading ? "flex flex-col gap-6 opacity-70 transition-opacity" : "flex flex-col gap-6"}>
      <section className="flex flex-col gap-3">
        <SectionHeader title="费用总览" extra={periodText} />
        <div className="px-6">
          <CostOverview data={data?.overview ?? null} partial={data?.partial ?? false} />
        </div>
      </section>

      <section className="px-6">
        <DaRanking rows={rank} level={level} activeKey={preset?.key ?? null} onPick={pickRank} />
      </section>

      <section className="px-6">
        <DashCard className="gap-4 px-6">
          <DailyTrendChart data={data?.daily.points ?? []} budget={data?.daily.budget ?? 0} monthLabel={monthLabel} />
        </DashCard>
      </section>

      <section className="px-6">
        <PersonDetail
          ref={detailRef}
          rows={persons}
          search={search}
          onSearchChange={setSearch}
          presetLabel={preset?.label ?? null}
          onClearPreset={() => setPreset(null)}
          onOpenAccount={openAccount}
          onExport={handleExport}
        />
        {data && (
          <p className="mt-2 text-xs text-muted-foreground">
            校验：本月花费 {fmtMoney(data.overview.spend)} 元 = {level === "da" ? "DA" : "大区"}排行合计{" "}
            {fmtMoney(data.totals.rank_sum)} = 个人明细合计 {fmtMoney(data.totals.detail_sum)}
            {preset || search.trim() ? `（当前表格已过滤，合计 ${fmtMoney(pageSum)}）` : ""}。
          </p>
        )}
      </section>

      <AccountCostSheet row={selected} month={costMonth} open={sheetOpen} onOpenChange={setSheetOpen} />
    </div>
  )
}
