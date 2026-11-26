import * as React from "react"
import { Brush, CartesianGrid, Line, LabelList, LineChart, XAxis, YAxis } from "recharts"

import { ChartLegendToggle, useSeriesToggle } from "@/components/dashboard/chart-legend"
import { CardTitleText } from "@/components/dashboard/primitives"
import { Card } from "@/components/ui/card"
import { type ChartConfig, ChartContainer, ChartTooltip } from "@/components/ui/chart"
import { PLATFORM_LAUNCH, LAST_DATA_DAY } from "@/data/dict"
import { fmtDate, fmtInt, fmtPct } from "@/lib/format"

import { useElementWidth } from "./bubble-labels"
import type { Granularity, TrendPoint } from "./data"
import { Segmented } from "./segmented"

const SERIES = [
  { key: "activeRatePct", label: "活跃率", color: "var(--series-green)", axis: "rate" },
  { key: "silentRatePct", label: "沉默率", color: "var(--series-blue)", axis: "rate" },
  { key: "genTotal", label: "总生成次数", color: "var(--series-orange)", axis: "count" },
] as const

const config = {
  activeRatePct: { label: "活跃率", color: "var(--series-green)" },
  silentRatePct: { label: "沉默率", color: "var(--series-blue)" },
  genTotal: { label: "总生成次数", color: "var(--series-orange)" },
} satisfies ChartConfig

/** 图例：虚线 + 方块标记 */
export function LineMarkerLegend({ color, label }: { color: string; label: string }) {
  return (
    <span className="inline-flex items-center gap-1 text-xs leading-4 text-card-foreground">
      <svg width="20" height="16" viewBox="0 0 20 16" aria-hidden>
        <line x1="0" y1="8" x2="20" y2="8" stroke={color} strokeWidth="1.5" strokeDasharray="3 2" />
        <rect x="6" y="4" width="8" height="8" rx="1" fill={color} />
      </svg>
      {label}
    </span>
  )
}

/** shadcn「Line Chart - Dots」风格：每个数据点一个圆点，描边用线条色、填充用背景色 */
function LineDot(props: { cx?: number; cy?: number; stroke?: string; index?: number }) {
  const { cx, cy, stroke } = props
  if (cx == null || cy == null) return null
  return <circle key={props.index} cx={cx} cy={cy} r={3} fill="var(--background)" stroke={stroke} strokeWidth={1.5} />
}

/** 每个数据点至少占用的像素宽度；用于限制 Brush 最小可拖动窗口，避免缩到只剩一两个点导致图表失真 */
const MIN_POINT_WIDTH = 64

/** 系列在数据中的最大值索引（忽略空值） */
function findPeakIndex(data: Record<string, unknown>[], key: string) {
  let idx = -1
  let max = -Infinity
  data.forEach((d, i) => {
    const v = d[key]
    if (typeof v === "number" && v > max) {
      max = v
      idx = i
    }
  })
  return idx
}

/**
 * 峰值浮动标签：默认（多条线同时展示）不显示；仅当图例只保留一条可见线，
 * 或鼠标悬停某个图例项时，在该线的最高点上方显示一个小圆点 + 数值标签。
 */
function makePeakLabel({
  peakIndex,
  color,
  formatValue,
}: {
  peakIndex: number
  color: string
  formatValue: (v: number) => string
}) {
  return function PeakLabel(props: { x?: number | string; y?: number | string; value?: unknown; index?: number }) {
    if (props.index !== peakIndex || props.value == null) return null
    const v = Number(props.value as number)
    const x = Number(props.x ?? 0)
    const y = Number(props.y ?? 0)
    return (
      <g style={{ pointerEvents: "none" }}>
        <circle cx={x} cy={y} r={3.5} fill={color} stroke="var(--background)" strokeWidth={1.5} />
        <text
          x={x}
          y={y - 12}
          textAnchor="middle"
          className="fill-foreground text-xs font-semibold"
          style={{ paintOrder: "stroke", stroke: "var(--background)", strokeWidth: 3 }}
        >
          {formatValue(v)}
        </text>
      </g>
    )
  }
}

function BrushTraveller(props: { x: number; y: number; width: number; height: number }) {
  const { x, y, width, height } = props
  return (
    <circle
      cx={x + width / 2}
      cy={y + height / 2}
      r={6}
      fill="white"
      stroke="var(--ring)"
      strokeWidth={1}
      className="cursor-ew-resize"
    />
  )
}

export function DaTrendCard({
  data,
  granularity,
  onGranularityChange,
  focusSlot,
}: {
  data: TrendPoint[]
  granularity: Granularity
  onGranularityChange: (g: Granularity) => void
  /** 「已带入：xxx」 */
  focusSlot?: React.ReactNode
}) {
  const chartData = data.map((d) => ({
    ...d,
    activeRatePct: d.activeRate == null ? null : +(d.activeRate * 100).toFixed(1),
    silentRatePct: d.silentRate == null ? null : +(d.silentRate * 100).toFixed(1),
  }))
  const { hidden, toggle } = useSeriesToggle()
  const [hoveredSeries, setHoveredSeries] = React.useState<string | null>(null)
  const [plotRef, plotWidth] = useElementWidth<HTMLDivElement>()
  const defaultWindow = granularity === "year" ? chartData.length : Math.min(chartData.length, 12)

  // Brush 最小可拖动窗口：按当前图表宽度能完整展示的点数，避免缩得只剩一两个点
  const minSpan = Math.max(2, Math.min(chartData.length, Math.ceil((plotWidth || 900) / MIN_POINT_WIDTH)))
  const [range, setRange] = React.useState(() => ({
    start: Math.max(0, chartData.length - defaultWindow),
    end: Math.max(0, chartData.length - 1),
  }))
  // 粒度切换或数据长度变化时，拖动范围回到默认窗口
  React.useEffect(() => {
    setRange({ start: Math.max(0, chartData.length - defaultWindow), end: Math.max(0, chartData.length - 1) })
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [granularity, chartData.length])

  const handleBrushChange = (next: { startIndex?: number; endIndex?: number }) => {
    let start = next.startIndex ?? range.start
    let end = next.endIndex ?? range.end
    if (end - start + 1 < minSpan) {
      // 根据哪一侧的手柄发生了移动，钳制另一侧以保住最小窗口
      if (start !== range.start) start = Math.max(0, end - minSpan + 1)
      else end = Math.min(chartData.length - 1, start + minSpan - 1)
    }
    setRange({ start, end })
  }

  const visibleKeys: string[] = SERIES.filter((s) => !hidden.has(s.key)).map((s) => s.key)
  // 仅剩一条可见线，或悬停某个图例项时才展示峰值标注；多条线同时展示时不标注（避免重叠）
  const highlightKey =
    visibleKeys.length === 1 ? visibleKeys[0] : hoveredSeries && visibleKeys.includes(hoveredSeries) ? hoveredSeries : null

  return (
    <Card className="gap-0 rounded-2xl border pt-0 pb-5 shadow-none ring-0">
      <div className="flex items-center justify-between gap-4 p-5">
        <div className="flex items-center gap-3">
          <CardTitleText>DA 周/月趋势</CardTitleText>
          {focusSlot}
        </div>
        <Segmented
          aria-label="时间粒度"
          value={granularity}
          onValueChange={onGranularityChange}
          options={[
            { value: "week", label: "按周" },
            { value: "month", label: "按月" },
            { value: "year", label: "按年" },
          ]}
        />
      </div>
      <div className="flex flex-col gap-4 px-9 pt-2">
        <div className="flex h-10 items-center justify-end gap-4">
          <span className="text-sm text-muted-foreground">
            数据周期：{fmtDate(PLATFORM_LAUNCH)}（上线）- {fmtDate(LAST_DATA_DAY)}
          </span>
          <ChartLegendToggle
            series={SERIES.map((s) => ({ ...s, marker: "dashed-line" as const }))}
            hidden={hidden}
            onToggle={toggle}
            onHoverChange={setHoveredSeries}
          />
        </div>
        <div ref={plotRef}>
          <ChartContainer config={config} className="aspect-auto h-[380px] w-full">
            <LineChart data={chartData} margin={{ top: 24, right: 8, bottom: 0, left: 0 }}>
              <CartesianGrid vertical={false} />
              <XAxis dataKey="label" tickLine={false} axisLine={false} tickMargin={10} minTickGap={16} />
              <YAxis
                yAxisId="rate"
                width={44}
                tickLine={false}
                axisLine={false}
                domain={[0, 100]}
                tickFormatter={(v: number) => `${v}%`}
              />
              <YAxis
                yAxisId="count"
                orientation="right"
                width={48}
                tickLine={false}
                axisLine={false}
                tickFormatter={(v: number) => (v >= 1000 ? `${+(v / 1000).toFixed(1)}k` : String(v))}
              />
              <ChartTooltip
                content={({ active, payload }) => {
                  const p = active ? (payload?.[0]?.payload as (typeof chartData)[number] | undefined) : undefined
                  if (!p) return null
                  return (
                    <div className="grid min-w-44 gap-1.5 rounded-lg border bg-background px-3 py-2 text-xs shadow-xl">
                      <div className="font-medium">{p.rangeLabel}</div>
                      {!hidden.has("activeRatePct") && (
                        <TooltipLine color="var(--series-green)" label="活跃率" value={fmtPct(p.activeRate)} />
                      )}
                      {!hidden.has("silentRatePct") && (
                        <TooltipLine color="var(--series-blue)" label="沉默率" value={fmtPct(p.silentRate)} />
                      )}
                      {!hidden.has("genTotal") && (
                        <TooltipLine color="var(--series-orange)" label="总生成次数" value={fmtInt(p.genTotal)} />
                      )}
                    </div>
                  )
                }}
              />
              {SERIES.map((s) => {
                const showPeak = highlightKey === s.key
                const idx = showPeak ? findPeakIndex(chartData, s.key) : -1
                return (
                  <Line
                    key={s.key}
                    yAxisId={s.axis}
                    dataKey={s.key}
                    hide={hidden.has(s.key)}
                    type="monotone"
                    stroke={s.color}
                    strokeWidth={1.5}
                    strokeDasharray="4 3"
                    dot={<LineDot />}
                    activeDot={{ r: 5 }}
                    connectNulls
                    isAnimationActive={false}
                  >
                    {idx >= 0 && (
                      <LabelList
                        dataKey={s.key}
                        content={makePeakLabel({
                          peakIndex: idx,
                          color: s.color,
                          formatValue: (v) => (s.axis === "rate" ? `${v}%` : fmtInt(v)),
                        })}
                      />
                    )}
                  </Line>
                )
              })}
              <Brush
                key={granularity}
                dataKey="label"
                height={12}
                travellerWidth={12}
                startIndex={range.start}
                endIndex={range.end}
                onChange={handleBrushChange}
                stroke="var(--primary)"
                fill="var(--muted)"
                traveller={(props) => <BrushTraveller {...(props as { x: number; y: number; width: number; height: number })} />}
                tickFormatter={() => ""}
              />
            </LineChart>
          </ChartContainer>
        </div>
      </div>
    </Card>
  )
}

function TooltipLine({ color, label, value }: { color: string; label: string; value: string }) {
  return (
    <div className="flex items-center justify-between gap-4">
      <span className="inline-flex items-center gap-1.5 text-muted-foreground">
        <span className="size-2 rounded-[2px]" style={{ background: color }} />
        {label}
      </span>
      <span className="font-medium tabular-nums">{value}</span>
    </div>
  )
}
