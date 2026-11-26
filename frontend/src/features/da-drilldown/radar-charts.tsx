import * as React from "react"
import {
  CartesianGrid,
  LabelList,
  ReferenceLine,
  Scatter,
  ScatterChart,
  XAxis,
  YAxis,
  ZAxis,
} from "recharts"

import { ChartLegendToggle, useSeriesToggle } from "@/components/dashboard/chart-legend"
import { ChartEmptyState } from "@/components/dashboard/chart-state"
import { CardTitleText, DashCard } from "@/components/dashboard/primitives"
import { Switch } from "@/components/ui/switch"
import { type ChartConfig, ChartContainer, ChartTooltip } from "@/components/ui/chart"
import { DATA_AS_OF } from "@/data/dict"
import { fmtDate, fmtDecimal, fmtInt, fmtPct } from "@/lib/format"
import { cn } from "@/lib/utils"

import { type Dimension, type GroupRow, niceDomain } from "./data"
import { type PlotGeometry, layoutBubbleLabels, makeBubbleLabel, useElementWidth } from "./bubble-labels"
import { Segmented } from "./segmented"

export const SILENT_ALERT = 0.3

const DIM_OPTIONS: { value: Dimension; label: string }[] = [
  { value: "da", label: "DA" },
  { value: "region", label: "大区" },
]

interface BubblePoint {
  key: string
  label: string
  x: number
  y: number
  z: number
  row: GroupRow
}

const MARGIN = { top: 16, right: 24, bottom: 28, left: 8 }
const Y_AXIS_WIDTH = 40

/* ------------------------------------------------------------------ */
/* 通用                                                                */
/* ------------------------------------------------------------------ */

function TooltipShell({ title, rows }: { title: string; rows: [string, React.ReactNode][] }) {
  return (
    <div className="grid min-w-52 gap-1.5 rounded-lg border bg-background px-3 py-2 text-xs shadow-xl">
      <div className="font-medium text-foreground">{title}</div>
      {rows.map(([k, v]) => (
        <div key={k} className="flex items-center justify-between gap-4">
          <span className="text-muted-foreground">{k}</span>
          <span className="font-medium text-foreground tabular-nums">{v}</span>
        </div>
      ))}
      <div className="pt-0.5 text-[11px] text-muted-foreground">点击气泡带入趋势图与明细表</div>
    </div>
  )
}

function RadarHeader({
  title,
  description,
  dim,
  onDimChange,
  extra,
}: {
  title: string
  description: string
  dim: Dimension
  onDimChange: (dim: Dimension) => void
  extra?: React.ReactNode
}) {
  return (
    <div className="flex items-start justify-between gap-4 px-6">
      <div className="flex flex-col gap-1.5">
        <CardTitleText>{title}</CardTitleText>
        <p className="text-sm text-muted-foreground">{description}</p>
      </div>
      <div className="flex items-center gap-4">
        {extra}
        <Segmented size="sm" aria-label="分析维度" value={dim} onValueChange={onDimChange} options={DIM_OPTIONS} />
      </div>
    </div>
  )
}

const CHART_HEIGHT = 340
const X_AXIS_HEIGHT = 30
const HEALTH_Z_RANGE: [number, number] = [220, 2400]

function pointFromEvent(data: unknown): BubblePoint | null {
  const d = data as { payload?: BubblePoint } & Partial<BubblePoint>
  if (d?.payload?.key) return d.payload
  if (d?.key) return d as BubblePoint
  return null
}

function refLineLabel(text: string, placement: "vertical" | "horizontal") {
  return function RefLabel(props: { viewBox?: { x?: number; y?: number; width?: number; height?: number } }) {
    const vb = props.viewBox ?? {}
    const x = vb.x ?? 0
    const y = vb.y ?? 0
    if (placement === "vertical") {
      return (
        <text x={x - 6} y={y + 14} textAnchor="end" className="fill-muted-foreground text-xs">
          {text}
        </text>
      )
    }
    return (
      <text x={x + (vb.width ?? 0) - 4} y={y - 6} textAnchor="end" className="fill-muted-foreground text-xs">
        {text}
      </text>
    )
  }
}

/* ------------------------------------------------------------------ */
/* DA 运营健康雷达                                                      */
/* ------------------------------------------------------------------ */

type HealthCategory = "highSilent" | "steady" | "highActive"

const HEALTH_META: Record<HealthCategory, { label: string; color: string }> = {
  highSilent: { label: "高沉默", color: "var(--bubble-red)" },
  steady: { label: "平稳", color: "var(--bubble-blue)" },
  highActive: { label: "高活跃", color: "var(--bubble-green)" },
}

const healthConfig = {
  highSilent: { label: "高沉默", color: "var(--bubble-red)" },
  steady: { label: "平稳", color: "var(--bubble-blue)" },
  highActive: { label: "高活跃", color: "var(--bubble-green)" },
} satisfies ChartConfig

export function HealthRadarCard({
  rows,
  dim,
  onDimChange,
  platformActiveRate,
  onSelect,
}: {
  rows: GroupRow[]
  dim: Dimension
  onDimChange: (dim: Dimension) => void
  /** 全平台活跃率（X 轴参考线） */
  platformActiveRate: number | null
  onSelect: (row: GroupRow) => void
}) {
  const avg = platformActiveRate ?? 0
  const points = rows
    .filter((r) => r.effective > 0 && r.activeRate.rate != null && r.silentRate.rate != null)
    .map<BubblePoint & { category: HealthCategory }>((r) => {
      const x = r.activeRate.rate! * 100
      const y = r.silentRate.rate! * 100
      const category: HealthCategory =
        r.silentRate.rate! >= SILENT_ALERT
          ? "highSilent"
          : r.activeRate.rate! >= avg + 0.05
            ? "highActive"
            : "steady"
      return { key: r.key, label: r.label, x, y, z: r.effective, row: r, category }
    })

  const xDomain = niceDomain([...points.map((p) => p.x), avg * 100], 10, 5)
  const yDomain = niceDomain([...points.map((p) => p.y), SILENT_ALERT * 100], 20, 5)

  const { hidden, toggle } = useSeriesToggle()
  const [hoveredKey, setHoveredKey] = React.useState<string | null>(null)
  const [showAllLabels, setShowAllLabels] = React.useState(false)
  const [plotRef, plotWidth] = useElementWidth<HTMLDivElement>()

  const visiblePoints = points.filter((p) => !hidden.has(p.category))
  const zValues = points.map((p) => p.z)
  const zDomain: [number, number] = [Math.min(...zValues, 0), Math.max(...zValues, 1)]
  const geometry: PlotGeometry = {
    width: plotWidth,
    height: CHART_HEIGHT,
    margin: MARGIN,
    yAxisWidth: Y_AXIS_WIDTH,
    xAxisHeight: X_AXIS_HEIGHT,
    xDomain,
    yDomain,
    zDomain,
    zRange: HEALTH_Z_RANGE,
  }
  const placements = showAllLabels
    ? new Map(visiblePoints.map((p) => [p.key, null]))
    : layoutBubbleLabels(visiblePoints, geometry)
  const hiddenLabelCount = showAllLabels ? 0 : [...placements.values()].filter((v) => v == null).length

  return (
    <DashCard className="gap-4">
      <RadarHeader
        title="DA 运营健康雷达"
        description="活跃率 × 沉默率，气泡大小表示账号数"
        dim={dim}
        onDimChange={onDimChange}
        extra={
          <label className="flex items-center gap-2 text-xs text-muted-foreground">
            <Switch size="sm" checked={showAllLabels} onCheckedChange={setShowAllLabels} />
            全部标签
          </label>
        }
      />
      <div className="flex flex-col gap-2 px-6">
        <div className="flex items-center justify-between text-xs text-muted-foreground">
          <span>沉默率 (%)</span>
          {hiddenLabelCount > 0 && <span>{hiddenLabelCount} 个标签因重叠已收起，悬停气泡查看</span>}
        </div>
        {points.length === 0 ? (
          <ChartEmptyState
            className="h-[320px]"
            title="当前筛选条件下暂无数据"
            description="请调整筛选条件或切换分析维度后重试"
          />
        ) : (
          <div ref={plotRef}>
            <ChartContainer config={healthConfig} className="aspect-auto w-full" style={{ height: CHART_HEIGHT }}>
              <ScatterChart margin={MARGIN}>
                <CartesianGrid />
                <XAxis
                  type="number"
                  dataKey="x"
                  domain={xDomain}
                  tickCount={7}
                  height={X_AXIS_HEIGHT}
                  tickLine={false}
                  axisLine={{ stroke: "var(--border)" }}
                  label={{ value: "活跃率 (%)", position: "insideBottom", offset: -20, className: "fill-muted-foreground text-xs" }}
                />
                <YAxis
                  type="number"
                  dataKey="y"
                  domain={yDomain}
                  width={Y_AXIS_WIDTH}
                  tickLine={false}
                  axisLine={{ stroke: "var(--border)" }}
                />
                <ZAxis type="number" dataKey="z" domain={zDomain} range={HEALTH_Z_RANGE} />
                <ReferenceLine
                  x={avg * 100}
                  stroke="var(--muted-foreground)"
                  strokeDasharray="4 4"
                  label={refLineLabel(`平均活跃线 ${fmtPct(avg, 0)}`, "vertical")}
                />
                <ReferenceLine
                  y={SILENT_ALERT * 100}
                  stroke="var(--muted-foreground)"
                  strokeDasharray="4 4"
                  label={refLineLabel(`高沉默警戒线 ${fmtPct(SILENT_ALERT, 0)}`, "horizontal")}
                />
                <ChartTooltip
                  cursor={false}
                  content={({ active, payload }) => {
                    const p = active ? (payload?.[0]?.payload as BubblePoint | undefined) : undefined
                    if (!p) return null
                    const r = p.row
                    return (
                      <TooltipShell
                        title={p.label}
                        rows={[
                          ["有效账号数", fmtInt(r.effective)],
                          ["活跃账号数", fmtInt(r.active)],
                          ["活跃率", `${fmtPct(r.activeRate.rate)}（${fmtInt(r.activeRate.numerator)}/${fmtInt(r.activeRate.denominator)}）`],
                          ["沉默账号数", fmtInt(r.silent)],
                          ["沉默率", `${fmtPct(r.silentRate.rate)}（${fmtInt(r.silentRate.numerator)}/${fmtInt(r.silentRate.denominator)}）`],
                          ["数据截至", fmtDate(DATA_AS_OF, "yyyy/MM/dd HH:mm")],
                        ]}
                      />
                    )
                  }}
                />
                {(Object.keys(HEALTH_META) as HealthCategory[]).map((cat) => {
                  const data = visiblePoints.filter((p) => p.category === cat)
                  return (
                    <Scatter
                      key={cat}
                      name={HEALTH_META[cat].label}
                      data={data}
                      fill={HEALTH_META[cat].color}
                      className="cursor-pointer"
                      shape={(props: { cx?: number; cy?: number; size?: number; payload?: BubblePoint }) => {
                        const r = Math.sqrt((props.size ?? 0) / Math.PI)
                        const dim = hoveredKey != null && props.payload?.key !== hoveredKey
                        return (
                          <circle
                            cx={props.cx}
                            cy={props.cy}
                            r={r}
                            fill={HEALTH_META[cat].color}
                            fillOpacity={dim ? 0.25 : 0.9}
                            stroke="var(--background)"
                            strokeWidth={1.5}
                            className="transition-[fill-opacity]"
                          />
                        )
                      }}
                      onMouseEnter={(d) => setHoveredKey(pointFromEvent(d)?.key ?? null)}
                      onMouseLeave={() => setHoveredKey(null)}
                      onClick={(d) => {
                        const p = pointFromEvent(d)
                        if (p) onSelect(p.row)
                      }}
                    >
                      <LabelList
                        dataKey="label"
                        content={makeBubbleLabel({
                          placements,
                          pointsByIndex: data,
                          hoveredKey,
                          showAll: showAllLabels,
                        })}
                      />
                    </Scatter>
                  )
                })}
              </ScatterChart>
            </ChartContainer>
          </div>
        )}
        <ChartLegendToggle
          className="justify-center"
          series={(Object.keys(HEALTH_META) as HealthCategory[]).map((k) => ({
            key: k,
            label: HEALTH_META[k].label,
            color: HEALTH_META[k].color,
            marker: "dot" as const,
          }))}
          hidden={hidden}
          onToggle={toggle}
        />
      </div>
    </DashCard>
  )
}

/* ------------------------------------------------------------------ */
/* DA 功能使用雷达                                                      */
/* ------------------------------------------------------------------ */

type Quadrant = "I" | "II" | "III" | "IV"

const QUADRANT_META: Record<Quadrant, { title: string; desc: string; color: string }> = {
  I: { title: "I. 核心驱动区", desc: "高渗透 / 高频使用 · 全面标杆", color: "var(--bubble-blue)" },
  II: { title: "II. 高潜深耕区", desc: "低人数 / 超高人均 · 隐形标杆", color: "var(--bubble-green)" },
  III: { title: "III. 观望培育区", desc: "基数小 / 使用低", color: "var(--bubble-gray)" },
  IV: { title: "IV. 唤醒推广区", desc: "基数大但人均低 · 亟需破冰", color: "var(--bubble-amber)" },
}

const featureConfig = {
  I: { label: "核心驱动区", color: "var(--bubble-blue)" },
  II: { label: "高潜深耕区", color: "var(--bubble-green)" },
  III: { label: "观望培育区", color: "var(--bubble-gray)" },
  IV: { label: "唤醒推广区", color: "var(--bubble-amber)" },
} satisfies ChartConfig

function QuadrantPill({ q, className, style }: { q: Quadrant; className?: string; style?: React.CSSProperties }) {
  const meta = QUADRANT_META[q]
  return (
    <div
      style={style}
      className={cn(
        "pointer-events-none absolute z-10 inline-flex items-center gap-1.5 rounded-md border bg-background px-2 py-1 text-xs whitespace-nowrap",
        className
      )}
    >
      <span className="size-2 rounded-[2px]" style={{ background: meta.color }} />
      <span className="font-semibold text-foreground">{meta.title}</span>
      <span className="text-muted-foreground">{meta.desc}</span>
    </div>
  )
}

export function FeatureRadarCard({
  rows,
  dim,
  onDimChange,
  platformActiveRate,
  platformPerActive,
  onSelect,
}: {
  rows: GroupRow[]
  dim: Dimension
  onDimChange: (dim: Dimension) => void
  platformActiveRate: number | null
  platformPerActive: number | null
  onSelect: (row: GroupRow) => void
}) {
  const refX = (platformActiveRate ?? 0) * 100
  const refY = platformPerActive ?? 0
  const points = rows
    .filter((r) => r.active > 0 && r.activeRate.rate != null && r.perActiveUsage != null)
    .map<BubblePoint & { quadrant: Quadrant }>((r) => {
      const x = r.activeRate.rate! * 100
      const y = r.perActiveUsage!
      const quadrant: Quadrant = x >= refX ? (y >= refY ? "I" : "IV") : y >= refY ? "II" : "III"
      return { key: r.key, label: r.label, x, y, z: r.featureTotal, row: r, quadrant }
    })

  const xDomain = niceDomain([...points.map((p) => p.x), refX], 10, 5)
  const yStep = refY > 40 ? 10 : 4
  const yDomain = niceDomain([...points.map((p) => p.y), refY], yStep, yStep / 2)

  // 象限标签定位在绘图区四角
  const plotLeft = MARGIN.left + Y_AXIS_WIDTH + 8
  const plotRight = MARGIN.right + 8
  const plotTop = MARGIN.top + 8
  const plotBottom = MARGIN.bottom + 30 + 8

  return (
    <DashCard className="gap-4">
      <RadarHeader
        title="DA功能使用雷达"
        description="使用广度（活跃渗透率）× 使用深度（人均使用次数），气泡大小表示用户基数"
        dim={dim}
        onDimChange={onDimChange}
      />
      <div className="flex flex-col gap-2 px-6">
        <span className="text-xs text-muted-foreground">单活跃账号功能使用次数（次/人）</span>
        {points.length === 0 ? (
          <ChartEmptyState
            className="h-[320px]"
            title="当前筛选条件下暂无数据"
            description="请调整筛选条件或切换分析维度后重试"
          />
        ) : (
          <div className="relative">
            <QuadrantPill q="II" style={{ left: plotLeft, top: plotTop }} />
            <QuadrantPill q="I" style={{ right: plotRight, top: plotTop }} />
            <QuadrantPill q="III" style={{ left: plotLeft, bottom: plotBottom }} />
            <QuadrantPill q="IV" style={{ right: plotRight, bottom: plotBottom }} />
            <ChartContainer config={featureConfig} className="aspect-auto h-[340px] w-full">
              <ScatterChart margin={MARGIN}>
                <CartesianGrid />
                <XAxis
                  type="number"
                  dataKey="x"
                  domain={xDomain}
                  tickLine={false}
                  axisLine={{ stroke: "var(--border)" }}
                  label={{ value: "活跃率 (%)", position: "insideBottom", offset: -20, className: "fill-muted-foreground text-xs" }}
                />
                <YAxis
                  type="number"
                  dataKey="y"
                  domain={yDomain}
                  width={Y_AXIS_WIDTH}
                  tickLine={false}
                  axisLine={{ stroke: "var(--border)" }}
                />
                <ZAxis type="number" dataKey="z" range={[220, 2000]} />
                <ReferenceLine
                  x={refX}
                  stroke="var(--muted-foreground)"
                  strokeDasharray="4 4"
                  label={refLineLabel(`全平台活跃率 ${fmtPct(platformActiveRate ?? 0, 0)}`, "vertical")}
                />
                <ReferenceLine
                  y={refY}
                  stroke="var(--muted-foreground)"
                  strokeDasharray="4 4"
                  label={refLineLabel(`全平台人均使用 ${fmtDecimal(platformPerActive ?? 0)} 次`, "horizontal")}
                />
                <ChartTooltip
                  cursor={false}
                  content={({ active, payload }) => {
                    const p = active ? (payload?.[0]?.payload as BubblePoint | undefined) : undefined
                    if (!p) return null
                    const r = p.row
                    return (
                      <TooltipShell
                        title={p.label}
                        rows={[
                          ["活跃账号数", fmtInt(r.active)],
                          ["活跃率", fmtPct(r.activeRate.rate)],
                          ["有效功能操作总次数", fmtInt(r.featureTotal)],
                          ["单活跃账号功能使用次数", fmtDecimal(r.perActiveUsage)],
                          ["内容生成账号数", fmtInt(r.genAccounts)],
                          ["生成转化率", fmtPct(r.genConversion)],
                          ["人均生成次数", fmtDecimal(r.perCapitaGen)],
                        ]}
                      />
                    )
                  }}
                />
                {(Object.keys(QUADRANT_META) as Quadrant[]).map((q) => (
                  <Scatter
                    key={q}
                    name={QUADRANT_META[q].title}
                    data={points.filter((p) => p.quadrant === q)}
                    fill={QUADRANT_META[q].color}
                    fillOpacity={0.95}
                    className="cursor-pointer"
                    onClick={(d) => {
                      const p = pointFromEvent(d)
                      if (p) onSelect(p.row)
                    }}
                  />
                ))}
              </ScatterChart>
            </ChartContainer>
          </div>
        )}
      </div>
    </DashCard>
  )
}
