import * as React from "react"
import { CalendarRangeIcon, GaugeIcon, PiggyBankIcon, WalletIcon } from "lucide-react"

import { DashCard, IconBubble, StatPill, Trend } from "@/components/dashboard/primitives"
import { Separator } from "@/components/ui/separator"
import { EMPTY, fmtInt, fmtMoney, fmtPct } from "@/lib/format"

import type { CostOverviewData } from "./cost-data"

/** 费用总览（PRD 5.2）。数值与环比均来自后端；上月无数据时环比显示「—」。 */
export function CostOverview({ data, partial }: { data: CostOverviewData | null; partial: boolean }) {
  const o = data
  const compareLabel = partial ? "较上月同期" : "较上月"
  return (
    <DashCard className="gap-6 px-6">
      <div className="flex items-stretch gap-6">
        <Metric
          label="本月花费（元）"
          icon={<WalletIcon />}
          value={o ? fmtMoney(o.spend) : EMPTY}
          trend={<Trend tone="strong" value={o?.spendMom} />}
          footer={
            <div className="flex flex-col gap-2">
              <div className="flex flex-wrap gap-2">
                <StatPill label="采购账号费用" value={o ? fmtMoney(o.purchaseSpend) : EMPTY} />
                <StatPill label="免费账号成本" value={o ? fmtMoney(o.freeSpend) : EMPTY} />
              </div>
              <span className="text-xs text-muted-foreground">
                {compareLabel} {o?.prevSpend == null ? EMPTY : fmtMoney(o.prevSpend)}
              </span>
            </div>
          }
        />
        <Divider />
        <Metric
          label="本月预算（元）"
          icon={<PiggyBankIcon />}
          value={o ? fmtInt(o.budget) : EMPTY}
          trend={<Trend tone="strong" value={o?.budgetMom} />}
          footer={
            <div className="flex flex-col gap-2">
              <span className="text-xs text-muted-foreground">
                {o ? `PLUS ${fmtInt(o.nPlus)}个 × 600 ｜ SUPER ${fmtInt(o.nSuper)}个 × 1200` : EMPTY}
                {o && o.unmappedBudget > 0 ? ` ｜ 待映射 ${fmtInt(o.unmappedBudget)}个（不计预算）` : ""}
              </span>
              <span className="text-xs text-muted-foreground">
                较上月整月 {o?.prevBudget == null ? EMPTY : fmtInt(o.prevBudget)}
              </span>
            </div>
          }
        />
        <Divider />
        <Metric
          label="预算使用率"
          icon={<GaugeIcon />}
          value={o ? fmtPct(o.rate) : EMPTY}
          trend={<Trend tone="strong" unit="pp" value={o?.rateDiff} />}
          footer={
            <div className="flex flex-wrap gap-2">
              <StatPill label="本月花费" value={o ? fmtMoney(o.rateNum) : EMPTY} />
              <StatPill label="本月预算" value={o ? fmtInt(o.rateDen) : EMPTY} />
            </div>
          }
        />
        <Divider />
        <Metric
          label="本年累计花费（元）"
          icon={<CalendarRangeIcon />}
          value={o ? fmtMoney(o.ytd) : EMPTY}
          footer={
            <div className="flex flex-col gap-2">
              <div className="flex flex-wrap gap-2">
                <StatPill label="采购账号费用" value={o ? fmtMoney(o.ytdPurchase) : EMPTY} />
                <StatPill label="免费账号成本" value={o ? fmtMoney(o.ytdFree) : EMPTY} />
              </div>
              <span className="text-xs text-muted-foreground">2026 年自平台上线日 2026/07/01 起算</span>
            </div>
          }
        />
      </div>
    </DashCard>
  )
}

function Divider() {
  return <Separator orientation="vertical" className="h-auto self-stretch" />
}

function Metric({
  label,
  icon,
  value,
  trend,
  footer,
}: {
  label: string
  icon: React.ReactNode
  value: string
  trend?: React.ReactNode
  footer: React.ReactNode
}) {
  return (
    <div className="flex min-w-0 flex-1 flex-col gap-6">
      <div className="flex items-start gap-4">
        <IconBubble>{icon}</IconBubble>
        <div className="flex min-w-0 flex-col gap-1.5">
          <span className="text-sm text-muted-foreground">{label}</span>
          <div className="flex flex-wrap items-baseline gap-1">
            <span className="text-xl leading-7 font-semibold tabular-nums">{value}</span>
            {trend}
          </div>
        </div>
      </div>
      <div className="mt-auto">{footer}</div>
    </div>
  )
}
