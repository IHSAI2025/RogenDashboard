import * as React from "react"
import { IconBrandDaysCounter, IconBulb } from "@tabler/icons-react"
import { ChevronRightIcon, MoonIcon, RocketIcon } from "lucide-react"

import { HgFileExport, HgZzz } from "@/components/dashboard/hugeicons"
import {
  CardTitleText,
  DashCard,
  IconBubble,
  StatPill,
  Trend,
} from "@/components/dashboard/primitives"
import { Button } from "@/components/ui/button"
import { Separator } from "@/components/ui/separator"
import { useDashboard } from "@/context/dashboard"
import { fmtDecimal, fmtInt, fmtPct, momChange } from "@/lib/format"
import { cn } from "@/lib/utils"

import { ppDiff, usePeriodSnapshots } from "./metrics"

export function PeriodSection() {
  const { setTab, openUsers } = useDashboard()
  const { current: cur, previous: prev } = usePeriodSnapshots()

  return (
    <div className="grid grid-cols-[376fr_752fr] gap-4 px-6">
      {/* 当期活跃情况 */}
      <PeriodCard
        title="当期活跃情况"
        action={{ label: "各 DA 情况", onClick: () => setTab("da") }}
        head={
          <HeadMetric
            icon={<IconBulb stroke={1.75} />}
            label="活跃率"
            value={fmtPct(cur.activeRate)}
            delta={ppDiff(cur.activeRate, prev.activeRate)}
            unit="pp"
          />
        }
      >
        <div className="flex flex-col gap-1.5">
          <SubMetric label="活跃账号数" value={fmtInt(cur.active)} delta={momChange(cur.active, prev.active)} />
          <SubMetric
            label="日均活跃账号"
            value={fmtInt(cur.dailyActive)}
            delta={momChange(cur.dailyActive, prev.dailyActive)}
          />
        </div>
      </PeriodCard>

      {/* 当期闲置预警 */}
      <PeriodCard
        title="当期闲置预警"
        action={{ label: "用户明细表", onClick: () => openUsers({ status: "休眠" }) }}
        head={
          <div className="flex items-center gap-4">
            <HeadMetric
              className="flex-1"
              icon={<MoonIcon strokeWidth={1.75} />}
              label="休眠率"
              value={fmtPct(cur.dormantRate)}
              valueClassName="text-2xl leading-8"
              delta={ppDiff(cur.dormantRate, prev.dormantRate)}
            unit="pp"
            />
            <HeadMetric
              className="flex-1"
              icon={<HgZzz />}
              label="沉默率"
              value={fmtPct(cur.silentRate)}
              delta={ppDiff(cur.silentRate, prev.silentRate)}
            unit="pp"
            />
          </div>
        }
      >
        <div className="grid grid-cols-2 gap-1.5">
          <SubMetric
            label="休眠账号数"
            value={fmtInt(cur.dormant)}
            delta={momChange(cur.dormant, prev.dormant)}
          />
          <SubMetric
            label="沉默账号数"
            value={fmtInt(cur.silent)}
            delta={momChange(cur.silent, prev.silent)}
          />
        </div>
        {/* 登录未使用：休眠 / 沉默账号中周期内登录过的账号，优先唤醒；点击跳转明细表 */}
        <div className="mt-1.5 grid grid-cols-2 gap-1.5">
          <button type="button" className="text-left" onClick={() => openUsers({ status: "休眠", loginUnused: true })}>
            <SubMetric
              label="休眠·登录未使用"
              value={fmtInt(cur.loginUnusedDormant)}
              delta={momChange(cur.loginUnusedDormant, prev.loginUnusedDormant)}
            />
          </button>
          <button type="button" className="text-left" onClick={() => openUsers({ status: "沉默", loginUnused: true })}>
            <SubMetric
              label="沉默·登录未使用"
              value={fmtInt(cur.loginUnusedSilent)}
              delta={momChange(cur.loginUnusedSilent, prev.loginUnusedSilent)}
            />
          </button>
        </div>
      </PeriodCard>

      {/* 当期使用效能 */}
      <PeriodCard
        title="当期使用效能"
        head={
          <HeadMetric
            icon={<IconBrandDaysCounter stroke={1.75} />}
            label="功能使用次数"
            value={fmtInt(cur.featureTotal)}
            delta={momChange(cur.featureTotal, prev.featureTotal)}
            gap="gap-1.5"
          />
        }
      >
        <div className="flex flex-col gap-1.5">
          <SubMetric
            justify
            label="日均使用次数"
            value={fmtInt(cur.dailyFeature)}
            delta={momChange(cur.dailyFeature, prev.dailyFeature)}
          />
          <SubMetric
            justify
            label="单活跃账号功能使用次数"
            value={fmtDecimal(cur.perActiveFeature)}
            delta={momChange(cur.perActiveFeature, prev.perActiveFeature)}
          />
        </div>
      </PeriodCard>

      {/* 当期生成情况 */}
      <PeriodCard
        title="当期生成情况"
        head={
          <div className="flex items-center gap-6">
            <HeadMetric
              className="flex-1"
              icon={<RocketIcon strokeWidth={1.75} />}
              label="当期生成数"
              value={fmtInt(cur.generation.total)}
              delta={momChange(cur.generation.total, prev.generation.total)}
              footer={
                <div className="flex items-center gap-2">
                  <StatPill label="PPT" value={fmtInt(cur.generation.ppt)} />
                  <StatPill label="推文" value={fmtInt(cur.generation.tweet)} />
                </div>
              }
            />
            <HeadMetric
              className="flex-1"
              icon={<HgFileExport size={32} />}
              label="当期导出数"
              value={fmtInt(cur.exports.total)}
              delta={momChange(cur.exports.total, prev.exports.total)}
              footer={
                <div className="flex items-center gap-2">
                  <StatPill label="PPT" value={fmtInt(cur.exports.ppt)} />
                  <StatPill label="推文" value={fmtInt(cur.exports.tweet)} />
                </div>
              }
            />
          </div>
        }
      >
        <div className="grid grid-cols-2 gap-1.5">
          <SubMetric
            label="日均生成次数"
            value={fmtDecimal(cur.dailyGeneration)}
            delta={momChange(cur.dailyGeneration, prev.dailyGeneration)}
          />
          <SubMetric
            label="人均生成次数"
            value={fmtDecimal(cur.perCapitaGeneration)}
            delta={momChange(cur.perCapitaGeneration, prev.perCapitaGeneration)}
          />
        </div>
      </PeriodCard>
    </div>
  )
}

function PeriodCard({
  title,
  action,
  head,
  children,
}: {
  title: string
  action?: { label: string; onClick: () => void }
  head: React.ReactNode
  children: React.ReactNode
}) {
  return (
    <DashCard className="relative">
      <CardTitleText className="px-6">{title}</CardTitleText>
      {action && (
        <Button
          variant="ghost"
          size="xs"
          className="absolute top-6 right-6 rounded-md text-card-foreground"
          onClick={action.onClick}
        >
          {action.label}
          <ChevronRightIcon data-icon="inline-end" />
        </Button>
      )}
      <div className="flex flex-col gap-1">
        <div className="px-6">{head}</div>
        <div className="flex h-4 items-center px-6">
          <Separator />
        </div>
        <div className="px-6">{children}</div>
      </div>
    </DashCard>
  )
}

function HeadMetric({
  icon,
  label,
  value,
  delta,
  footer,
  className,
  valueClassName,
  gap = "gap-4",
  unit = "pct",
}: {
  /** 率类指标环比为百分点差 */
  unit?: "pct" | "pp"
  icon: React.ReactNode
  label: string
  value: string
  delta: number | null
  footer?: React.ReactNode
  className?: string
  valueClassName?: string
  gap?: string
}) {
  return (
    <div className={cn("flex items-center", gap, className)}>
      <IconBubble>{icon}</IconBubble>
      <div className="flex flex-col gap-1.5">
        <span className="text-sm leading-5 text-muted-foreground">{label}</span>
        <div className="flex items-baseline gap-1">
          <span className={cn("text-xl leading-7 font-semibold whitespace-nowrap", valueClassName)}>
            {value}
          </span>
          <Trend value={delta} unit={unit} tone="strong" />
        </div>
        {footer}
      </div>
    </div>
  )
}

function SubMetric({
  label,
  value,
  delta,
  justify,
}: {
  label: string
  value: string
  delta: number | null
  /** 标签撑满，数值靠右（当期使用效能） */
  justify?: boolean
}) {
  return (
    <div className={cn("flex items-center gap-1.5", justify && "w-full")}>
      <span
        className={cn(
          "text-xs leading-4 text-muted-foreground",
          justify ? "min-w-0 flex-1" : "w-[88px] shrink-0"
        )}
      >
        {label}
      </span>
      <span className="text-sm leading-5 font-medium text-card-foreground">{value}</span>
      <Trend value={delta} />
    </div>
  )
}
