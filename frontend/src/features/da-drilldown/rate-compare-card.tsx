import * as React from "react"
import { Bar, BarChart, CartesianGrid, LabelList, ReferenceLine, XAxis, YAxis } from "recharts"

import { ChartLegendToggle, useSeriesToggle } from "@/components/dashboard/chart-legend"
import { ChartEmptyState } from "@/components/dashboard/chart-state"
import { CardTitleText, DashCard, trendColorClass } from "@/components/dashboard/primitives"
import { type ChartConfig, ChartContainer, ChartTooltip } from "@/components/ui/chart"
import { EMPTY, fmtPct, fmtSignedPp } from "@/lib/format"
import { cn } from "@/lib/utils"

export interface RateRow {
  key: string
  label: string
  plus: number | null
  super: number | null
  /** 环比（百分点差） */
  plusDelta: number | null
  superDelta: number | null
}

const SERIES = [
  { key: "plus", label: "Plus账号", color: "var(--chart-2)" },
  { key: "super", label: "Super账号", color: "var(--chart-1)" },
] as const

const chartConfig = {
  plus: { label: "Plus账号", color: "var(--chart-2)" },
  super: { label: "Super账号", color: "var(--chart-1)" },
} satisfies ChartConfig

const ROW_HEIGHT = 44

/**
 * 账号导入率 / 活跃率 / 沉默率对比（shadcn 横向条形图）：
 * 柱尾只显示数值，环比放在 tooltip；竖向虚线为预警线；图例可点击显示/隐藏 Plus / Super。
 */
export function RateCompareCard({
  title,
  description,
  rows,
  threshold,
  action,
  empty,
  emptyDescription,
  className,
}: {
  title: string
  description?: string
  rows: RateRow[]
  threshold: number
  action?: React.ReactNode
  /** 空态标题，默认「当前筛选条件下暂无数据」 */
  empty?: string
  /** 空态说明（design 157:5316：无则不展示） */
  emptyDescription?: string
  className?: string
}) {
  const { hidden, toggle } = useSeriesToggle()
  const data = React.useMemo(
    () => rows.map((r) => ({ ...r, plusPct: pct(r.plus), superPct: pct(r.super) })),
    [rows]
  )
  const maxValue = Math.max(
    threshold * 100,
    ...data.flatMap((d) => [d.plusPct ?? 0, d.superPct ?? 0])
  )
  // 刻度上限取 20 的倍数，最多 100（导入率可能略超 100%）
  const domainMax = Math.max(20, Math.ceil(maxValue / 20) * 20)
  const visible = SERIES.filter((s) => !hidden.has(s.key))
  const height = Math.max(160, rows.length * ROW_HEIGHT + 48)

  return (
    <DashCard className={cn("gap-4 px-6", className)}>
      <div className="flex min-h-9 items-start justify-between gap-4">
        <div className="flex flex-col gap-1">
          <CardTitleText>{title}</CardTitleText>
          {description && <p className="text-sm text-muted-foreground">{description}</p>}
        </div>
        {action}
      </div>

      {rows.length === 0 ? (
        <ChartEmptyState title={empty ?? "当前筛选条件下暂无数据"} description={emptyDescription} />
      ) : (
        <>
          <ChartLegendToggle
            series={[...SERIES]}
            hidden={hidden}
            onToggle={toggle}
          />
          <div className="max-h-[480px] overflow-y-auto">
            <ChartContainer config={chartConfig} className="aspect-auto w-full" style={{ height }}>
              <BarChart
                data={data}
                layout="vertical"
                margin={{ top: 20, right: 48, bottom: 0, left: 0 }}
                barCategoryGap={visible.length > 1 ? 10 : 14}
                barGap={2}
              >
                <CartesianGrid horizontal={false} strokeDasharray="3 3" />
                <XAxis
                  type="number"
                  domain={[0, domainMax]}
                  tickFormatter={(v) => `${v}%`}
                  tickLine={false}
                  axisLine={false}
                  tickMargin={6}
                  fontSize={12}
                />
                <YAxis
                  type="category"
                  dataKey="label"
                  width={96}
                  tickLine={false}
                  axisLine={false}
                  tickMargin={8}
                  fontSize={12}
                  interval={0}
                />
                <ChartTooltip
                  cursor={{ fill: "var(--muted)", opacity: 0.6 }}
                  content={<RateTooltip threshold={threshold} hidden={hidden} />}
                />
                <ReferenceLine
                  x={threshold * 100}
                  stroke="var(--muted-foreground)"
                  strokeDasharray="4 4"
                  label={{
                    value: `预警线 ${fmtPct(threshold, 0)}`,
                    position: "top",
                    fill: "var(--muted-foreground)",
                    fontSize: 12,
                  }}
                />
                {visible.map((s) => (
                  <Bar
                    key={s.key}
                    dataKey={`${s.key}Pct`}
                    name={s.label}
                    fill={s.color}
                    radius={4}
                    maxBarSize={12}
                    isAnimationActive={false}
                  >
                    <LabelList
                      dataKey={`${s.key}Pct`}
                      position="right"
                      offset={6}
                      fontSize={11}
                      fill="var(--muted-foreground)"
                      formatter={(v: unknown) => (typeof v === "number" ? `${v.toFixed(1)}%` : EMPTY)}
                    />
                  </Bar>
                ))}
              </BarChart>
            </ChartContainer>
          </div>
        </>
      )}
    </DashCard>
  )
}

function pct(v: number | null) {
  return v == null ? null : Math.round(v * 1000) / 10
}

type RatePoint = RateRow & { plusPct: number | null; superPct: number | null }

function RateTooltip({
  active,
  payload,
  threshold,
  hidden,
}: {
  active?: boolean
  payload?: { payload: RatePoint }[]
  threshold: number
  hidden: Set<string>
}) {
  if (!active || !payload?.length) return null
  const row = payload[0].payload
  const items = SERIES.filter((s) => !hidden.has(s.key)).map((s) => ({
    ...s,
    value: s.key === "plus" ? row.plus : row.super,
    delta: s.key === "plus" ? row.plusDelta : row.superDelta,
  }))
  return (
    <div className="grid min-w-44 gap-1.5 rounded-lg border bg-background px-2.5 py-1.5 text-xs shadow-xl">
      <div className="font-medium">{row.label}</div>
      {items.map((it) => (
        <div key={it.key} className="flex items-center gap-2">
          <span className="size-2.5 shrink-0 rounded-[2px]" style={{ background: it.color }} />
          <span className="flex-1 text-muted-foreground">{it.label}</span>
          <span className="font-mono font-medium tabular-nums">{fmtPct(it.value)}</span>
          <span className={cn("w-16 text-right tabular-nums", it.delta != null && trendColorClass(it.delta))}>
            {it.delta == null ? EMPTY : fmtSignedPp(it.delta)}
          </span>
        </div>
      ))}
      <div className="border-t pt-1.5 text-muted-foreground">
        预警线 {fmtPct(threshold, 0)} · 右侧为环比（pp）
      </div>
    </div>
  )
}
