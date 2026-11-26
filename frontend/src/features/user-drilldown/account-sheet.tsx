import * as React from "react"
import { Bar, BarChart, CartesianGrid, XAxis, YAxis } from "recharts"
import { format } from "date-fns"

import { useApi } from "@/api/use-api"
import { EnabledBadge, SourceBadge, UsageStatusBadge } from "@/components/dashboard/account-badges"
import { SheetMetaGrid, SheetStat, SheetStatGrid } from "@/components/dashboard/sheet-kit"
import {
  type ChartConfig,
  ChartContainer,
  ChartLegend,
  ChartLegendContent,
  ChartTooltip,
  ChartTooltipContent,
} from "@/components/ui/chart"
import {
  Sheet,
  SheetContent,
  SheetDescription,
  SheetHeader,
  SheetTitle,
} from "@/components/ui/sheet"
import { Separator } from "@/components/ui/separator"
import { daName } from "@/data/dict"
import { maskPhone } from "@/lib/auth"
import { EMPTY, fmtDate, fmtInt } from "@/lib/format"

import type { UserRow, WeekPoint as ApiWeek } from "./types"

const WEEKS = 12

const chartConfig = {
  ppt: { label: "PPT", color: "var(--series-blue)" },
  tweet: { label: "推文", color: "var(--series-green)" },
} satisfies ChartConfig

interface WeekPoint {
  week: string
  range: string
  genPpt: number
  genTweet: number
  expPpt: number
  expTweet: number
}

/** 后端按「截至统计截止日的近 12 个滚动 7 日」统计成功生成与导出（账号越权返回 404） */
function toPoints(weeks: ApiWeek[]): WeekPoint[] {
  return weeks.map((w) => {
    const s = new Date(w.start.replaceAll("-", "/"))
    return {
      week: format(s, "MM/dd"),
      range: `${fmtDate(w.start)} - ${fmtDate(w.end)}`,
      genPpt: w.gen_ppt,
      genTweet: w.gen_tweet,
      expPpt: w.exp_ppt,
      expTweet: w.exp_tweet,
    }
  })
}

export function AccountSheet({
  row,
  end,
  open,
  onOpenChange,
}: {
  row: UserRow | null
  end: string | null
  open: boolean
  onOpenChange: (open: boolean) => void
}) {
  const weekly = useApi<{ points: ApiWeek[] }>(open && row && end ? `/vm/users/${row.id}/weekly` : null, { end })
  const data = React.useMemo(() => (weekly.data ? toPoints(weekly.data.points) : []), [weekly.data])

  return (
    <Sheet open={open} onOpenChange={onOpenChange}>
      <SheetContent className="w-full gap-0 overflow-y-auto data-[side=right]:sm:max-w-[640px]">
        {row && (
          <>
            <SheetHeader className="gap-2 border-b p-6">
              <div className="flex flex-wrap items-center gap-2">
                <SheetTitle className="text-lg font-semibold">{row.name}</SheetTitle>
                {row.state !== "—" && <UsageStatusBadge status={row.state} />}
                <EnabledBadge enabled={row.enabled} />
                {(row.source_tag === "采购" || row.source_tag === "免费") && <SourceBadge source={row.source_tag} />}
              </div>
              <SheetDescription asChild>
                <SheetMetaGrid
                  items={[
                    { label: "账号ID", value: String(row.id) },
                    { label: "联系电话", value: maskPhone(row.phone) },
                    { label: "所属DA", value: daName(row.da === "待映射" ? null : row.da) },
                    { label: "大区", value: row.region },
                    { label: "用户身份", value: row.identity },
                    { label: "账号类型", value: row.account_type },
                  ]}
                />
              </SheetDescription>
            </SheetHeader>

            <div className="flex flex-col gap-6 p-6">
              <SheetStatGrid>
                <SheetStat label="活跃天数" value={`${row.active_days} / ${row.period_days}`} />
                <SheetStat label="连续未使用天数" value={row.idle_days === null ? EMPTY : fmtInt(row.idle_days)} />
                <SheetStat label="最近使用日期" value={fmtDate(row.last_use)} />
                <SheetStat label="功能使用总次数" value={fmtInt(row.ops_total)} />
                <SheetStat label="总生成次数" value={fmtInt(row.gen_total)} />
                <SheetStat label="总导出次数" value={fmtInt(row.exp_total)} />
                <SheetStat label="最近成功生成" value={fmtDate(row.last_gen)} />
                <SheetStat label="备注" value={row.remark || EMPTY} small />
              </SheetStatGrid>

              <Separator />

              <div className="flex flex-col gap-1">
                <h4 className="text-base font-semibold">按周生成与导出趋势</h4>
                <p className="text-sm text-muted-foreground">
                  近 {WEEKS} 周，截至 {fmtDate(end)}
                </p>
              </div>

              {weekly.error ? (
                <p className="text-sm text-destructive">趋势加载失败：{weekly.error}</p>
              ) : weekly.loading && !weekly.data ? (
                <p className="text-sm text-muted-foreground">加载中…</p>
              ) : (
                <>
                  <TrendChart title="生成次数" data={data} pptKey="genPpt" tweetKey="genTweet" />
                  <TrendChart title="导出次数" data={data} pptKey="expPpt" tweetKey="expTweet" />
                </>
              )}

              <p className="text-xs text-muted-foreground">注：海报功能上线后加入海报生成与导出趋势。</p>
            </div>
          </>
        )}
      </SheetContent>
    </Sheet>
  )
}

function TrendChart({
  title,
  data,
  pptKey,
  tweetKey,
}: {
  title: string
  data: WeekPoint[]
  pptKey: keyof WeekPoint
  tweetKey: keyof WeekPoint
}) {
  const series = React.useMemo(
    () =>
      data.map((p) => ({ week: p.week, range: p.range, ppt: p[pptKey], tweet: p[tweetKey] })),
    [data, pptKey, tweetKey]
  )
  return (
    <div className="flex flex-col gap-2">
      <span className="text-sm font-medium">{title}</span>
      <ChartContainer config={chartConfig} className="aspect-auto h-[200px] w-full">
        <BarChart data={series} margin={{ top: 8, right: 8, left: -16, bottom: 0 }}>
          <CartesianGrid vertical={false} />
          <XAxis dataKey="week" tickLine={false} axisLine={false} tickMargin={8} fontSize={12} />
          <YAxis tickLine={false} axisLine={false} allowDecimals={false} fontSize={12} />
          <ChartTooltip
            cursor={false}
            content={
              <ChartTooltipContent
                labelFormatter={(_, payload) => payload?.[0]?.payload?.range ?? ""}
              />
            }
          />
          <ChartLegend content={<ChartLegendContent />} />
          <Bar dataKey="ppt" fill="var(--color-ppt)" radius={[4, 4, 0, 0]} />
          <Bar dataKey="tweet" fill="var(--color-tweet)" radius={[4, 4, 0, 0]} />
        </BarChart>
      </ChartContainer>
    </div>
  )
}
