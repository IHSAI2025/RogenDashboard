import * as React from "react"

import { META } from "@/data/dict"

import { SectionHeader } from "@/components/dashboard/primitives"
import { useDashboard } from "@/context/dashboard"
import { isSingleDa, NO_DA } from "@/data/selectors"
import { AiInsightCard } from "@/features/overview/ai-insight-card"
import { fmtPeriod } from "@/lib/format"

import {
  type Dimension,
  type Focus,
  type Granularity,
  type GroupMetrics,
  type GroupRow,
  useGroups,
  useTrend,
} from "./data"
import { MetricsTableSection } from "./metrics-table"
import { FeatureRadarCard, HealthRadarCard, SILENT_ALERT } from "./radar-charts"
import { type RateRow, RateCompareCard } from "./rate-compare-card"
import { FocusAction, FocusChip, Segmented } from "./segmented"
import { DaTrendCard } from "./trend-card"

const RATE_DIM_OPTIONS: { value: Dimension; label: string }[] = [
  { value: "da", label: "DA" },
  { value: "region", label: "大区" },
  { value: "leader", label: "圈长" },
]

function delta(cur: number | null | undefined, prev: number | null | undefined) {
  return cur != null && prev != null ? cur - prev : null
}

function toRateRows(rows: GroupRow[], pick: (r: GroupMetrics) => Record<"PLUS" | "SUPER", number | null>): RateRow[] {
  return rows.map((r) => {
    const cur = pick(r)
    const prev = r.prev ? pick(r.prev) : null
    return {
      key: r.key,
      label: r.label,
      plus: cur.PLUS,
      super: cur.SUPER,
      plusDelta: delta(cur.PLUS, prev?.PLUS),
      superDelta: delta(cur.SUPER, prev?.SUPER),
    }
  })
}

export function DaDrilldownTab() {
  const { filters, setFilters, period, openUsers } = useDashboard()

  const singleDa = isSingleDa(filters.daIds) && !filters.daIds.includes(NO_DA)
  // 多 DA → 按 DA；单 DA → 按大区
  const defaultDim: Dimension = singleDa ? "region" : "da"

  const [activeDim, setActiveDim] = React.useState<Dimension>(defaultDim)
  const [silentDim, setSilentDim] = React.useState<Dimension>(defaultDim)
  const [healthDim, setHealthDim] = React.useState<Dimension>(defaultDim)
  const [featureDim, setFeatureDim] = React.useState<Dimension>(defaultDim)
  const [granularity, setGranularity] = React.useState<Granularity>("month")
  const [focus, setFocus] = React.useState<Focus | null>(null)

  // 上层筛选变化：维度回到默认，清除带入
  React.useEffect(() => {
    setActiveDim(defaultDim)
    setSilentDim(defaultDim)
    setHealthDim(defaultDim)
    setFeatureDim(defaultDim)
    setFocus(null)
  }, [defaultDim, filters])

  // 预警线取后端配置(META.warn，百分数)；沉默率预警线见 radar-charts 的 SILENT_ALERT
  const IMPORT_ALERT = (META?.warn.import ?? 40) / 100
  const ACTIVE_ALERT = (META?.warn.active ?? 40) / 100

  const tableDim: Dimension = singleDa || focus?.dim === "da" ? "region" : "da"

  // 各卡片的分组指标全部来自后端（同参数请求在 data.ts 内去重）
  const gImport = useGroups("da", { enabled: defaultDim === "da" })
  const gActive = useGroups(activeDim)
  const gSilent = useGroups(silentDim)
  const gHealth = useGroups(healthDim)
  const gFeature = useGroups(featureDim)
  const gTable = useGroups(tableDim, {
    focus,
    // 未选择具体 DA 时，无法映射 DA 的账号单列「待映射」行
    includeUnmapped: tableDim === "da" && filters.daIds.length === 0,
  })
  const platform = gHealth.platform

  /*
   * 导入率没有「圈长」和「大区」维度切换：维度跟随上层筛选自动决定——
   * 选择多个 DA 时按 DA 展示；选择单个 DA 时按大区展示，但大区没有导入率指标，展示空态。
   */
  const importRows = defaultDim === "da" ? toRateRows(gImport.rows, (r) => r.importRateByType) : []
  const activeRows = toRateRows(gActive.rows, (r) => r.activeRateByType)
  const silentRows = toRateRows(gSilent.rows, (r) => r.silentRateByType)

  const trend = useTrend(granularity, focus)

  const trendRef = React.useRef<HTMLDivElement>(null)

  const selectBubble = (dim: Dimension) => (row: GroupRow) => {
    setFocus({ dim, key: row.key, label: row.label })
    requestAnimationFrame(() =>
      trendRef.current?.scrollIntoView({ behavior: "smooth", block: "start" })
    )
  }

  const openUserDetail = () => {
    if (!focus) return
    if (focus.dim === "da") {
      setFilters({ daIds: [focus.key] })
      openUsers()
    } else {
      openUsers({ region: focus.key })
    }
  }

  const focusChip = focus ? (
    <FocusChip
      label={focus.label}
      onClear={() => setFocus(null)}
      action={focus.dim !== "leader" ? <FocusAction onClick={openUserDetail}>查看用户明细 →</FocusAction> : null}
    />
  ) : null

  const periodText = `数据周期：${fmtPeriod(period)}`

  return (
    <div className="flex flex-col gap-6">
      <div className="px-6">
        <AiInsightCard scope="da" />
      </div>

      <section className="flex flex-col gap-3">
        <SectionHeader title="三大率综合看板" extra={periodText} />
        <div className="flex flex-col gap-2.5 px-6">
          <RateCompareCard
            title="账号导入率对比"
            rows={importRows}
            threshold={IMPORT_ALERT}
            empty={defaultDim === "da" ? "当前筛选条件下暂无数据" : "大区维度暂无导入率数据"}
            emptyDescription={
              defaultDim === "da" ? undefined : "导入率仅按 DA 维度统计，请在上方筛选多个 DA 查看"
            }
          />
          <div className="grid gap-2.5 lg:grid-cols-2">
            <RateCompareCard
              title="账号活跃率对比"
              rows={activeRows}
              threshold={ACTIVE_ALERT}
              action={
                <Segmented aria-label="活跃率维度" value={activeDim} onValueChange={setActiveDim} options={RATE_DIM_OPTIONS} />
              }
            />
            <RateCompareCard
              title="账号沉默率对比"
              rows={silentRows}
              threshold={SILENT_ALERT}
              action={
                <Segmented aria-label="沉默率维度" value={silentDim} onValueChange={setSilentDim} options={RATE_DIM_OPTIONS} />
              }
            />
          </div>
        </div>
      </section>

      <section className="flex flex-col gap-3">
        <SectionHeader title="健康雷达" extra={periodText} />
        <div className="flex flex-col gap-3 px-6">
          <HealthRadarCard
            rows={gHealth.rows}
            dim={healthDim}
            onDimChange={setHealthDim}
            platformActiveRate={platform.activeRate.rate}
            onSelect={selectBubble(healthDim)}
          />
          <FeatureRadarCard
            rows={gFeature.rows}
            dim={featureDim}
            onDimChange={setFeatureDim}
            platformActiveRate={platform.activeRate.rate}
            platformPerActive={platform.perActiveUsage}
            onSelect={selectBubble(featureDim)}
          />
          <div ref={trendRef} className="scroll-mt-48">
            <DaTrendCard
              data={trend}
              granularity={granularity}
              onGranularityChange={setGranularity}
              focusSlot={focusChip}
            />
          </div>
        </div>
      </section>

      <MetricsTableSection
        rows={gTable.rows}
        dim={tableDim}
        period={period}
        filters={filters}
        focus={focus}
        includeUnmapped={tableDim === "da" && filters.daIds.length === 0}
        focusLabel={focus?.label}
        focusSlot={focusChip}
      />
    </div>
  )
}
