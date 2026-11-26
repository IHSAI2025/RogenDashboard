import { Cell, Pie, PieChart } from "recharts"

import { ChartLegendToggle, useSeriesToggle } from "@/components/dashboard/chart-legend"
import { CardTitleText, DashCard } from "@/components/dashboard/primitives"
import { type ChartConfig, ChartContainer, ChartTooltip } from "@/components/ui/chart"
import { Separator } from "@/components/ui/separator"
import { useDashboard } from "@/context/dashboard"
import { META } from "@/data/dict"
import { fmtInt, fmtPct, fmtPeriod, safeRatio } from "@/lib/format"

import { useDistribution } from "./metrics"

/* ------------------------------------------------------------------ */
/* 账号分布                                                             */
/* ------------------------------------------------------------------ */

interface Slice {
  key: string
  label: string
  value: number
  color: string
}

function Donut({ title, slices: allSlices }: { title: string; slices: Slice[] }) {
  const { hidden, toggle } = useSeriesToggle()
  // 点击图例隐藏扇区后，占比按剩余可见扇区重新计算
  const slices = allSlices.filter((s) => !hidden.has(s.key))
  const total = slices.reduce((s, x) => s + x.value, 0)
  const config = Object.fromEntries(
    slices.map((s) => [s.key, { label: s.label, color: s.color }])
  ) satisfies ChartConfig
  return (
    <div className="flex flex-1 items-center justify-center gap-10">
      <div className="relative size-40 shrink-0">
        <ChartContainer config={config} className="aspect-square size-40">
          <PieChart>
            <ChartTooltip
              cursor={false}
              content={({ active, payload }) => {
                if (!active || !payload?.length) return null
                const p = payload[0].payload as Slice
                return (
                  <div className="rounded-lg border bg-background px-2.5 py-1.5 text-xs shadow-md">
                    <div className="flex items-center gap-1.5 font-medium">
                      <span className="size-2.5 rounded-[2px]" style={{ background: p.color }} />
                      {p.label}
                    </div>
                    <div className="mt-0.5 text-muted-foreground">
                      {fmtInt(p.value)} 个 · {fmtPct(safeRatio(p.value, total))}
                    </div>
                  </div>
                )
              }}
            />
            <Pie
              data={slices}
              dataKey="value"
              nameKey="label"
              innerRadius={48}
              outerRadius={80}
              startAngle={90}
              endAngle={-270}
              strokeWidth={0}
              isAnimationActive={false}
            >
              {slices.map((s) => (
                <Cell key={s.key} fill={s.color} />
              ))}
            </Pie>
          </PieChart>
        </ChartContainer>
        <span className="pointer-events-none absolute inset-0 flex items-center justify-center text-sm leading-5 text-muted-foreground">
          {title}
        </span>
      </div>
      <ChartLegendToggle
        orientation="vertical"
        className="gap-y-4"
        series={allSlices}
        hidden={hidden}
        onToggle={toggle}
      />
    </div>
  )
}

export function AccountDistributionCard() {
  const { period } = useDashboard()
  // 后端按统计截止日的累计开通账号（PRD 1.5），受全局筛选影响
  const dist = useDistribution()?.distribution
  const types = [
    { key: "plus", label: "Plus账号", value: dist?.types.plus ?? 0, color: "var(--chart-2)" },
    { key: "super", label: "Super账号", value: dist?.types.super ?? 0, color: "var(--chart-1)" },
  ]
  const identities = [
    { key: "customer", label: "客户", value: dist?.identities.customer ?? 0, color: "var(--mint-8)" },
    { key: "staff", label: "员工", value: dist?.identities.staff ?? 0, color: "var(--mint-5)" },
  ]

  return (
    <DashCard className="gap-6">
      <div className="flex items-center justify-between px-6">
        <CardTitleText>账号分布</CardTitleText>
        <span className="text-sm leading-5 text-muted-foreground">数据周期：{fmtPeriod(period)}</span>
      </div>
      <div className="flex items-center justify-center gap-5 px-6">
        <Donut title="账号类型" slices={types} />
        <Donut title="用户身份" slices={identities} />
      </div>
    </DashCard>
  )
}

/* ------------------------------------------------------------------ */
/* 功能使用分布图                                                        */
/* ------------------------------------------------------------------ */

function BarList({
  rows,
  labelWidth,
}: {
  rows: { label: string; value: number; ratio?: number | null }[]
  /** 标签列宽度，按该列最长标签设置，避免左右两图挤在一起 */
  labelWidth: number
}) {
  const max = Math.max(1, ...rows.map((r) => r.value))
  return (
    <div className="flex flex-col gap-2">
      {rows.map((r) => (
        <div key={r.label} className="flex items-center gap-2" title={`${r.label}：${fmtInt(r.value)} 次`}>
          <span
            className="shrink-0 truncate text-xs leading-4 text-[#64748b]"
            style={{ width: labelWidth }}
          >
            {r.label}
          </span>
          <div className="flex min-w-0 flex-1 items-center gap-2">
            <div
              className="h-[29px] rounded-[4px] bg-chart-2"
              style={{ width: `calc((100% - 48px) * ${r.value / max})`, minWidth: r.value > 0 ? 4 : 0 }}
            />
            <span className="text-xs whitespace-nowrap text-card-foreground">
              {r.value}
              {r.ratio != null && <span className="ml-1 text-muted-foreground">{fmtPct(r.ratio)}</span>}
            </span>
          </div>
        </div>
      ))}
    </div>
  )
}

export function FeatureDistributionCard() {
  const { period } = useDashboard()
  const fn = useDistribution()?.functions
  // 海报上线前不显示海报数据（PRD 三·0）
  const core = (fn?.core ?? []).filter((r) => META.poster_live || r.label !== "海报")
  // 子模块按 PRD：PPT（文献解读 / 学术创作Pro）、推文（医学科普 / 专业学术 / 指南/政策解读）；占比为组内占比
  const subs = (fn?.subs ?? []).map((r) => ({ ...r, label: `${r.group}·${r.label}` }))

  return (
    <DashCard className="gap-6">
      <div className="flex items-center justify-between px-6">
        <CardTitleText>功能使用分布图</CardTitleText>
        <div className="flex items-center gap-4">
          {fn?.topN ? (
            <>
              <span className="text-sm leading-5 font-medium text-primary">
                Top{fn.topN} 功能贡献达 {fmtPct(fn.topShare, 0)}
              </span>
              <Separator orientation="vertical" className="h-3" />
            </>
          ) : null}
          <span className="text-sm leading-5 text-muted-foreground">数据周期：{fmtPeriod(period)}</span>
        </div>
      </div>
      <div className="flex items-stretch gap-12 px-6">
        <div className="flex min-w-0 flex-1 flex-col gap-3">
          <span className="text-xs font-medium text-muted-foreground">核心功能</span>
          <div className="flex flex-1 flex-col justify-center">
            <BarList rows={core} labelWidth={40} />
          </div>
        </div>
        <Separator orientation="vertical" className="h-auto" />
        <div className="flex min-w-0 flex-1 flex-col gap-3">
          <span className="text-xs font-medium text-muted-foreground">细分功能（占比为组内占比）</span>
          <BarList rows={subs} labelWidth={110} />
        </div>
      </div>
    </DashCard>
  )
}
