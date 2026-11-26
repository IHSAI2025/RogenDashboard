import * as React from "react"
import { format } from "date-fns"
import { Brush, CartesianGrid, Line, LineChart, XAxis, YAxis } from "recharts"

import { ChartLegendToggle, useSeriesToggle } from "@/components/dashboard/chart-legend"
import { CardTitleText, DashCard } from "@/components/dashboard/primitives"
import { type ChartConfig, ChartContainer, ChartTooltip, ChartTooltipContent } from "@/components/ui/chart"
import { LAST_DATA_DAY, META } from "@/data/dict"
import { fmtDate } from "@/lib/format"

import { LAUNCH_LABEL, type TrendRow, useGenerationTrend } from "./metrics"
import { Segmented } from "./segmented"

type Granularity = "week" | "month" | "year"
type SeriesKey = "ppt" | "tweet" | "poster"

const SERIES: { key: SeriesKey; label: string; color: string }[] = [
  { key: "ppt", label: "PPT", color: "var(--series-green)" },
  { key: "tweet", label: "推文", color: "var(--series-blue)" },
  { key: "poster", label: "海报", color: "var(--series-orange)" },
]

const chartConfig = Object.fromEntries(
  SERIES.map((s) => [s.key, { label: s.label, color: s.color }])
) satisfies ChartConfig

const parse = (iso: string) => {
  const [y, m, d] = iso.split("-").map(Number)
  return new Date(y, m - 1, d)
}

/** 后端按周期返回起止日，这里只负责展示用的标签（与设计稿一致） */
function labelsOf(r: TrendRow, granularity: Granularity) {
  const d = parse(r.start)
  if (granularity === "week") return { label: format(d, "MM/dd"), fullLabel: `${format(d, "yyyy/MM/dd")} 当周` }
  if (granularity === "month") return { label: `${format(d, "M")} 月`, fullLabel: format(d, "yyyy 年 M 月") }
  return { label: format(d, "yyyy 年"), fullLabel: format(d, "yyyy 年") }
}

function SquareDot(props: { cx?: number; cy?: number; stroke?: string; payload?: unknown; value?: unknown }) {
  const { cx, cy, stroke, value } = props
  if (cx == null || cy == null || value == null) return null
  return <rect x={cx - 5} y={cy - 5} width={10} height={10} rx={2} fill={stroke} />
}

function BrushTraveller(props: { x?: number; y?: number; width?: number; height?: number }) {
  const { x = 0, y = 0, width = 0, height = 0 } = props
  return (
    <circle
      cx={x + width / 2}
      cy={y + height / 2}
      r={5.5}
      fill="#fff"
      stroke="var(--ring)"
      strokeWidth={1}
    />
  )
}

function compactTick(v: number) {
  if (Math.abs(v) >= 1000) return `${Math.round(v / 100) / 10}k`
  return String(v)
}

export function GenerationTrendCard({ metric }: { metric: "total" | "perCapita" }) {
  const [granularity, setGranularity] = React.useState<Granularity>("month")
  const { hidden, toggle } = useSeriesToggle()
  const rows = useGenerationTrend(granularity)
  // 海报上线前不显示海报数据
  const series = SERIES.filter((s) => META.poster_live || s.key !== "poster")

  const data = React.useMemo(
    () =>
      (rows ?? []).map((r) => ({
        ...labelsOf(r, granularity),
        ...(metric === "total"
          ? r.total
          : Object.fromEntries(
              Object.entries(r.perCapita).map(([k, v]) => [k, v == null ? null : Math.round(v * 10) / 10])
            )),
      })),
    [rows, granularity, metric]
  )

  const windowSize = granularity === "week" ? 12 : 6
  const startIndex = Math.max(0, data.length - windowSize)

  return (
    <DashCard className="gap-0 rounded-2xl py-0 pb-5">
      <div className="flex items-center justify-between p-5">
        <CardTitleText>{metric === "total" ? "核心功能生成总次数" : "核心功能人均生成次数"}</CardTitleText>
        <Segmented
          aria-label="时间粒度"
          value={granularity}
          onValueChange={setGranularity}
          options={[
            { value: "week", label: "按周" },
            { value: "month", label: "按月" },
            { value: "year", label: "按年" },
          ]}
        />
      </div>
      <div className="flex flex-col gap-4 px-5">
        <div className="flex h-10 flex-wrap items-center justify-end gap-x-4 gap-y-1">
          <span className="text-sm leading-5 whitespace-nowrap text-muted-foreground">
            数据周期：{LAUNCH_LABEL}- {fmtDate(LAST_DATA_DAY)}
          </span>
          <ChartLegendToggle
            series={series.map((s) => ({ ...s, marker: "dashed-line" as const }))}
            hidden={hidden}
            onToggle={toggle}
          />
        </div>
        <ChartContainer config={chartConfig} className="aspect-auto h-[380px] w-full">
          <LineChart data={data} margin={{ top: 8, right: 8, left: 0, bottom: 0 }}>
            <CartesianGrid vertical={false} stroke="var(--border)" />
            <XAxis
              dataKey="label"
              tickLine={false}
              axisLine={false}
              tickMargin={10}
              minTickGap={8}
            />
            <YAxis
              tickLine={false}
              axisLine={false}
              tickMargin={8}
              tickFormatter={compactTick}
              width={44}
            />
            <ChartTooltip
              content={
                <ChartTooltipContent
                  indicator="line"
                  labelFormatter={(_, payload) =>
                    (payload?.[0]?.payload as { fullLabel?: string } | undefined)?.fullLabel ?? ""
                  }
                />
              }
            />
            {series.map((s) => (
              <Line
                key={s.key}
                type="monotone"
                dataKey={s.key}
                name={s.label}
                hide={hidden.has(s.key)}
                stroke={s.color}
                strokeWidth={1.5}
                strokeDasharray="4 3"
                dot={data.length <= 40 ? <SquareDot /> : false}
                activeDot={{ r: 4, fill: s.color, strokeWidth: 0 }}
                connectNulls
                isAnimationActive={false}
              />
            ))}
            <Brush
              key={granularity}
              dataKey="label"
              height={12}
              travellerWidth={12}
              startIndex={startIndex}
              endIndex={data.length - 1}
              stroke="var(--primary)"
              fill="var(--muted)"
              tickFormatter={() => ""}
              traveller={<BrushTraveller />}
            />
          </LineChart>
        </ChartContainer>
      </div>
    </DashCard>
  )
}
