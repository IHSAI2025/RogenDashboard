import * as React from "react"
import { format } from "date-fns"
import { Bar, BarChart, CartesianGrid, ReferenceLine, XAxis, YAxis } from "recharts"

import { EnabledBadge, SourceBadge } from "@/components/dashboard/account-badges"
import { ChartEmptyState } from "@/components/dashboard/chart-state"
import { SheetMetaGrid, SheetStat, SheetStatGrid } from "@/components/dashboard/sheet-kit"
import { type ChartConfig, ChartContainer, ChartTooltip } from "@/components/ui/chart"
import { Separator } from "@/components/ui/separator"
import { Sheet, SheetContent, SheetDescription, SheetHeader, SheetTitle } from "@/components/ui/sheet"
import { META, daName } from "@/data/dict"
import { maskPhone } from "@/lib/auth"
import { EMPTY, fmtDate, fmtInt, fmtMoney, fmtPct } from "@/lib/format"

import { type MonthPoint, type PersonRow, useAccountCost } from "./cost-data"
import { compactMoney } from "./daily-trend-chart"

const chartConfig = {
  spend: { label: "月度花费", color: "var(--chart-2)" },
} satisfies ChartConfig

const FEATURE_COLORS = ["var(--chart-2)", "var(--chart-3)", "var(--chart-4)", "var(--muted-foreground)"]

export function AccountCostSheet({
  row,
  month,
  open,
  onOpenChange,
}: {
  row: PersonRow | null
  month: Date
  open: boolean
  onOpenChange: (open: boolean) => void
}) {
  return (
    <Sheet open={open} onOpenChange={onOpenChange}>
      <SheetContent side="right" className="w-[640px] gap-0 overflow-y-auto data-[side=right]:sm:max-w-[640px]">
        {row && <SheetBody row={row} month={month} />}
      </SheetContent>
    </Sheet>
  )
}

function SheetBody({ row, month }: { row: PersonRow; month: Date }) {
  const account = row
  const detail = useAccountCost(row.id, month)
  const budget = row.budget
  const months = React.useMemo(() => detail.data?.months ?? [], [detail.data])
  const features = React.useMemo(
    () => (detail.data?.byFunction ?? []).filter((f) => f.key !== "poster" || META?.poster_live),
    [detail.data]
  )
  const maxSpend = Math.max(budget ?? 0, ...months.map((m) => m.spend ?? 0))
  const hasMonthlyData = months.some((m) => m.spend != null)

  return (
    <>
      <SheetHeader className="gap-2 border-b p-6">
        <div className="flex flex-wrap items-center gap-2">
          <SheetTitle className="text-lg font-semibold">{account.name}</SheetTitle>
          <EnabledBadge enabled={account.enabled} />
          <SourceBadge source={account.source} />
        </div>
        <SheetDescription asChild>
          <SheetMetaGrid
            items={[
              { label: "账号ID", value: account.id },
              { label: "联系电话", value: maskPhone(account.phone) },
              { label: "所属DA", value: daName(account.daId) },
              { label: "大区", value: account.region },
              { label: "用户身份", value: account.identity },
              { label: "账号类型", value: account.accountType ?? "待映射" },
            ]}
          />
        </SheetDescription>
      </SheetHeader>

      <div className="p-6">
        <SheetStatGrid cols={3}>
          <SheetStat label={`${format(month, "M")}月花费（元）`} value={fmtMoney(row.spend)} />
          <SheetStat
            label="预算使用率"
            value={row.rate == null ? EMPTY : fmtPct(row.rate)}
            caption={row.budget == null ? undefined : `花费 ${fmtMoney(row.spend)} / 预算 ${fmtInt(row.budget)}`}
          />
          <SheetStat label="本年累计花费（元）" value={fmtMoney(row.ytd)} />
        </SheetStatGrid>
      </div>

      <Separator />

      <section className="flex flex-col gap-3 p-6">
        <div className="flex items-center justify-between">
          <h3 className="text-base font-semibold">近 12 个月逐月花费</h3>
          <span className="text-xs text-muted-foreground">
            月度预算：{budget == null ? "待映射" : `${account.accountType} ${fmtInt(budget)} 元`}
          </span>
        </div>
        {detail.loading && !detail.data ? (
          <div className="py-10 text-center text-sm text-muted-foreground">加载中…</div>
        ) : !hasMonthlyData ? (
          <ChartEmptyState
            title="近 12 个月暂无费用数据"
            description="平台上线（2026-07-01）后才有费用记录"
          />
        ) : (
        <ChartContainer config={chartConfig} className="aspect-auto h-[240px] w-full">
          <BarChart data={months} margin={{ top: 16, right: 8, left: 0, bottom: 0 }}>
            <CartesianGrid vertical={false} />
            <XAxis dataKey="label" tickLine={false} axisLine={false} tickMargin={8} />
            <YAxis
              tickLine={false}
              axisLine={false}
              width={48}
              domain={[0, Math.ceil(maxSpend * 1.15) || 100]}
              tickFormatter={compactMoney}
            />
            <ChartTooltip
              cursor={{ fill: "var(--muted)" }}
              content={(props) => {
                const p = props.payload?.[0]?.payload as MonthPoint | undefined
                if (!props.active || !p) return null
                return (
                  <div className="grid gap-1 rounded-lg border bg-background px-2.5 py-1.5 text-xs shadow-xl">
                    <span className="font-medium">{p.key}</span>
                    <span className="flex justify-between gap-4">
                      <span className="text-muted-foreground">月度花费</span>
                      <span className="tabular-nums">{p.spend == null ? EMPTY : fmtMoney(p.spend)}</span>
                    </span>
                    {budget != null && p.spend != null && (
                      <span className="flex justify-between gap-4">
                        <span className="text-muted-foreground">预算使用率</span>
                        <span className="tabular-nums">{fmtPct(p.spend / budget)}</span>
                      </span>
                    )}
                  </div>
                )
              }}
            />
            <Bar
              dataKey="spend"
              fill="var(--color-spend)"
              radius={[4, 4, 0, 0]}
              maxBarSize={28}
              label={(props: { x?: number | string; y?: number | string; width?: number | string; index?: number }) => {
                const p = props.index != null ? months[props.index] : undefined
                if (!p || p.spend != null) return <g />
                const x = Number(props.x ?? 0) + Number(props.width ?? 0) / 2
                return (
                  <text x={x} y={Number(props.y ?? 0) - 6} textAnchor="middle" className="fill-muted-foreground text-xs">
                    {EMPTY}
                  </text>
                )
              }}
            />
            {budget != null && (
              <ReferenceLine
                y={budget}
                stroke="var(--foreground)"
                strokeDasharray="4 4"
                label={{
                  value: `${account.accountType} 预算 ${fmtInt(budget)}`,
                  position: "insideTopRight",
                  className: "fill-muted-foreground text-xs",
                }}
              />
            )}
          </BarChart>
        </ChartContainer>
        )}
        {hasMonthlyData && (
          <p className="text-xs text-muted-foreground">平台上线（2026-07-01）前的月份显示「—」</p>
        )}
      </section>

      <Separator />

      <section className="flex flex-col gap-3 p-6">
        <h3 className="text-base font-semibold">本月花费按功能拆分</h3>
        <div className="flex flex-col gap-3">
          {features.map((f, i) => {
            const ratio = row.spend > 0 ? (f.ratio ?? 0) : 0
            return (
              <div key={f.key} className="flex flex-col gap-1.5">
                <div className="flex items-center justify-between text-sm">
                  <span className="inline-flex items-center gap-2">
                    <span className="size-2.5 rounded-[2px]" style={{ background: FEATURE_COLORS[i] }} />
                    {f.label}
                  </span>
                  <span className="tabular-nums">
                    {fmtMoney(f.amount)} 元
                    <span className="ml-3 inline-block w-12 text-right text-muted-foreground">
                      {row.spend > 0 ? fmtPct(ratio) : EMPTY}
                    </span>
                  </span>
                </div>
                <div className="h-1.5 w-full overflow-hidden rounded-full bg-muted">
                  <div
                    className="h-full rounded-full"
                    style={{ width: `${ratio * 100}%`, background: FEATURE_COLORS[i] }}
                  />
                </div>
              </div>
            )
          })}
        </div>
        <p className="text-xs text-muted-foreground">
          [TBD] 功能拆分依赖商汤按次回传 token，当前为估算口径。最近使用日期：{fmtDate(row.lastUsedDate)}
        </p>
      </section>
    </>
  )
}
