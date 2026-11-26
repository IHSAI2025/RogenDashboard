import { Bar, CartesianGrid, ComposedChart, Line, ReferenceLine, XAxis, YAxis } from "recharts"

import { ChartLegendToggle, useSeriesToggle } from "@/components/dashboard/chart-legend"
import { ChartEmptyState } from "@/components/dashboard/chart-state"
import { type ChartConfig, ChartContainer, ChartTooltip } from "@/components/ui/chart"
import { EMPTY, fmtDate, fmtMoney, fmtPct, safeRatio } from "@/lib/format"

import type { DailyPoint } from "./cost-data"

type Source = "采购" | "免费"

/** 账号来源 → 堆叠柱。单个账号只会命中其中一种，调用方通过 sources 收窄 */
const SOURCE_SERIES: Record<Source, { key: "purchase" | "free"; label: string; color: string }> = {
  采购: { key: "purchase", label: "采购当日花费", color: "var(--chart-2)" },
  免费: { key: "free", label: "免费当日花费", color: "var(--chart-1)" },
}

const ALL_SOURCES: Source[] = ["采购", "免费"]

const chartConfig = {
  purchase: { label: "采购", color: "var(--chart-2)" },
  free: { label: "免费", color: "var(--chart-1)" },
  cumulative: { label: "累计花费", color: "var(--primary)" },
} satisfies ChartConfig

export function compactMoney(v: number) {
  if (Math.abs(v) >= 10000) return `${(v / 10000).toFixed(v >= 100000 ? 0 : 1)}万`
  return `${Math.round(v)}`
}

/**
 * 每日费用趋势：当日花费堆叠柱（左轴）+ 月初至当日累计花费折线（右轴）+ 预算参考线。
 * 不自带卡片外壳，由调用方决定包在 DashCard 还是抽屉的 section 里。
 */
export function DailyTrendChart({
  data,
  budget,
  monthLabel,
  title = "本月每日费用趋势",
  sources = ALL_SOURCES,
  height = 320,
  budgetLabel = "本月预算",
}: {
  data: DailyPoint[]
  budget: number
  monthLabel: string
  title?: string
  /** 参与堆叠的账号来源，单账号抽屉只传其自身来源 */
  sources?: Source[]
  height?: number
  budgetLabel?: string
}) {
  const bars = sources.map((s) => SOURCE_SERIES[s])
  const legend = useSeriesToggle()
  const hasData = data.some((d) => d.total != null)
  const maxCumulative = Math.max(budget, ...data.map((d) => d.cumulative ?? 0))

  const legendSeries = [
    ...bars.map((b) => ({ key: b.key, label: b.label, color: b.color, marker: "square" as const })),
    { key: "cumulative", label: "月初至当日累计花费", color: "var(--primary)", marker: "line" as const },
    ...(budget > 0
      ? [{ key: "budget", label: budgetLabel, color: "var(--foreground)", marker: "dash" as const }]
      : []),
  ]

  const visibleBars = bars.filter((b) => !legend.hidden.has(b.key))
  const showCumulative = !legend.hidden.has("cumulative")
  const showBudget = budget > 0 && !legend.hidden.has("budget")

  return (
    <div className="flex flex-col gap-4">
      <div className="flex flex-wrap items-center justify-between gap-x-4 gap-y-2">
        <h3 className="text-base leading-6 font-semibold text-card-foreground">{title}</h3>
        {hasData && (
          <ChartLegendToggle series={legendSeries} hidden={legend.hidden} onToggle={legend.toggle} />
        )}
      </div>
      {!hasData ? (
        <ChartEmptyState
          title="统计月份暂无费用数据"
          description="该月份早于平台或费用功能上线日期，或暂无花费记录"
        />
      ) : (
      <ChartContainer config={chartConfig} className="aspect-auto w-full" style={{ height }}>
        <ComposedChart data={data} margin={{ top: 16, right: 8, left: 8, bottom: 0 }}>
          <CartesianGrid vertical={false} />
          <XAxis
            dataKey="day"
            tickLine={false}
            axisLine={false}
            tickMargin={8}
            interval={0}
            tickFormatter={(d: number) => (d === 1 || d % 5 === 0 ? `${d}日` : "")}
          />
          <YAxis
            yAxisId="daily"
            tickLine={false}
            axisLine={false}
            width={56}
            tickFormatter={compactMoney}
          />
          <YAxis
            yAxisId="cumulative"
            orientation="right"
            tickLine={false}
            axisLine={false}
            width={60}
            domain={[0, Math.ceil(maxCumulative * 1.1)]}
            tickFormatter={compactMoney}
          />
          <ChartTooltip
            cursor={{ fill: "var(--muted)" }}
            content={(props) => (
              <DailyTooltip
                active={props.active}
                point={(props.payload?.[0]?.payload as DailyPoint | undefined) ?? null}
                budget={budget}
                bars={visibleBars}
                showCumulative={showCumulative}
              />
            )}
          />
          {visibleBars.map((b, i) => (
            <Bar
              key={b.key}
              yAxisId="daily"
              dataKey={b.key}
              stackId="spend"
              fill={b.color}
              maxBarSize={18}
              // 只有最上面一段收圆角
              radius={i === visibleBars.length - 1 ? [3, 3, 0, 0] : undefined}
              isAnimationActive={false}
            />
          ))}
          {showCumulative && (
            <Line
              yAxisId="cumulative"
              dataKey="cumulative"
              type="monotone"
              stroke="var(--color-cumulative)"
              strokeWidth={2}
              dot={false}
              connectNulls={false}
              isAnimationActive={false}
            />
          )}
          {showBudget && (
            <ReferenceLine
              yAxisId="cumulative"
              y={budget}
              stroke="var(--foreground)"
              strokeDasharray="4 4"
              label={{
                value: `${budgetLabel} ${fmtMoney(budget)}`,
                position: "insideTopRight",
                className: "fill-muted-foreground text-xs",
              }}
            />
          )}
        </ComposedChart>
      </ChartContainer>
      )}
      {hasData && (
        <p className="text-xs text-muted-foreground">
          统计月份 {monthLabel}；左轴为当日花费
          {bars.length > 1 ? "（按采购 / 免费堆叠）" : ""}，右轴为月初至当日累计花费。
        </p>
      )}
    </div>
  )
}

function DailyTooltip({
  active,
  point,
  budget,
  bars,
  showCumulative,
}: {
  active?: boolean
  point: DailyPoint | null
  budget: number
  bars: { key: "purchase" | "free"; label: string; color: string }[]
  showCumulative: boolean
}) {
  if (!active || !point) return null
  const noData = point.total == null
  return (
    <div className="grid min-w-44 gap-1.5 rounded-lg border bg-background px-2.5 py-1.5 text-xs shadow-xl">
      <div className="font-medium">{fmtDate(point.date)}</div>
      {noData ? (
        <div className="text-muted-foreground">暂无数据</div>
      ) : (
        <>
          <Row label="当日花费" value={fmtMoney(point.total)} strong />
          {bars.length > 1 &&
            bars.map((b) => (
              <Row key={b.key} label={`· ${b.label.replace("当日花费", "")}`} value={fmtMoney(point[b.key])} color={b.color} />
            ))}
          {showCumulative && (
            <>
              <Row label="累计花费" value={fmtMoney(point.cumulative)} strong />
              <Row
                label="累计占预算"
                value={budget > 0 ? fmtPct(safeRatio(point.cumulative ?? 0, budget)) : EMPTY}
              />
            </>
          )}
        </>
      )}
    </div>
  )
}

function Row({
  label,
  value,
  color,
  strong,
}: {
  label: string
  value: string
  color?: string
  strong?: boolean
}) {
  return (
    <div className="flex items-center justify-between gap-4">
      <span className="inline-flex items-center gap-1.5 text-muted-foreground">
        {color && <span className="size-2 rounded-[2px]" style={{ background: color }} />}
        {label}
      </span>
      <span className={strong ? "font-medium text-foreground tabular-nums" : "text-foreground tabular-nums"}>
        {value}
      </span>
    </div>
  )
}
