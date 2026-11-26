import * as React from "react"
import { ArrowDownLeftIcon, ArrowUpRightIcon, TrendingDownIcon, TrendingUpIcon } from "lucide-react"

import { Card } from "@/components/ui/card"
import { EMPTY, fmtSignedPct, fmtSignedPp } from "@/lib/format"
import { cn } from "@/lib/utils"

/* ------------------------------------------------------------------ */
/* 卡片 / 分区标题                                                      */
/* ------------------------------------------------------------------ */

/** 设计稿卡片：1px 边框 / 14px 圆角 / 上下 24px 内边距 */
export function DashCard({ className, ...props }: React.ComponentProps<typeof Card>) {
  return (
    <Card
      className={cn("gap-4 rounded-xl border bg-card py-6 shadow-none ring-0", className)}
      {...props}
    />
  )
}

export function CardTitleText({ className, ...props }: React.ComponentProps<"h3">) {
  return (
    <h3
      className={cn("text-base leading-6 font-semibold text-card-foreground", className)}
      {...props}
    />
  )
}

/** 卡片外的分区标题：左侧标题，右侧「数据周期：…」 */
export function SectionHeader({
  title,
  extra,
  level = "section",
  className,
}: {
  title: React.ReactNode
  extra?: React.ReactNode
  /** section：一级分区（18px 加粗）；group：二级分组（16px） */
  level?: "section" | "group"
  className?: string
}) {
  return (
    <div className={cn("flex items-center justify-between gap-4 px-6", className)}>
      <h2
        className={cn(
          "font-semibold text-foreground",
          level === "section" ? "text-base leading-6" : "text-base leading-6"
        )}
      >
        {title}
      </h2>
      {extra != null && (
        <div className="text-sm whitespace-nowrap text-muted-foreground">{extra}</div>
      )}
    </div>
  )
}

/* ------------------------------------------------------------------ */
/* 环比                                                                */
/* ------------------------------------------------------------------ */

/** 涨跌色：上升红 / 下降绿（全站统一，不区分指标好坏） */
export function trendColorClass(value: number) {
  return value > 0 ? "text-rise" : value < 0 ? "text-fall" : "text-muted-foreground"
}

/**
 * 环比徽标（lucide trending 图标 + 数值）。
 * tone=strong：主指标，图标与数值都着涨跌色；tone=muted：次级指标，只有图标着色、数值灰色。
 */
export function Trend({
  value,
  unit = "pct",
  tone = "muted",
  className,
}: {
  value: number | null | undefined
  unit?: "pct" | "pp"
  tone?: "strong" | "muted"
  className?: string
}) {
  if (value == null || !Number.isFinite(value)) {
    return <span className={cn("px-2 text-xs font-medium text-muted-foreground", className)}>{EMPTY}</span>
  }
  const Icon = value >= 0 ? TrendingUpIcon : TrendingDownIcon
  const text = unit === "pp" ? fmtSignedPp(value) : fmtSignedPct(value)
  const color = trendColorClass(value)
  return (
    <span
      className={cn(
        "inline-flex items-center gap-1 rounded-4xl px-2 py-0.5 text-xs leading-4 font-medium whitespace-nowrap",
        tone === "strong" ? color : "text-muted-foreground",
        className
      )}
    >
      <Icon className={cn("size-3", color)} />
      {text}
    </span>
  )
}

/** 账号及产品使用规模 tile 中的 20px 箭头 + 数值 */
export function TileDelta({ value }: { value: number | null | undefined }) {
  if (value == null || !Number.isFinite(value)) {
    return <span className="text-xs text-muted-foreground">{EMPTY}</span>
  }
  const Icon = value >= 0 ? ArrowUpRightIcon : ArrowDownLeftIcon
  const color = trendColorClass(value)
  return (
    <span className={cn("inline-flex items-center gap-1", color)}>
      <Icon className="size-5" strokeWidth={2.25} />
      <span className="text-xs leading-4 tracking-[-0.072px]">
        {`${Math.abs(value * 100).toFixed(1)}%`}
      </span>
    </span>
  )
}

/* ------------------------------------------------------------------ */
/* 图标 / 图例 / 分段条                                                 */
/* ------------------------------------------------------------------ */

/** 48px 浅蓝圆底 + 32px 图标 */
export function IconBubble({ children, className }: { children: React.ReactNode; className?: string }) {
  return (
    <div
      className={cn(
        "flex shrink-0 items-center justify-center rounded-[38px] bg-[#eff6ff] p-2 text-primary [&_svg]:size-8 [&_svg]:stroke-[1.75]",
        className
      )}
    >
      {children}
    </div>
  )
}

export function LegendItem({
  color,
  label,
  shape = "square",
  className,
}: {
  color: string
  label: React.ReactNode
  shape?: "square" | "dash"
  className?: string
}) {
  return (
    <span className={cn("inline-flex items-center gap-1 text-xs leading-4 text-card-foreground", className)}>
      {shape === "dash" ? (
        <span className="w-3 border-t border-dashed border-foreground" />
      ) : (
        <span className="size-2.5 shrink-0 rounded-[2px]" style={{ background: color }} />
      )}
      {label}
    </span>
  )
}

/** 两段占比条：上方图例 + 下方 4px 分段条（PLUS/Super、PPT/推文） */
export function SplitBar({
  items,
}: {
  items: [
    { label: string; value: number; color?: string },
    { label: string; value: number; color?: string },
  ]
}) {
  const [a, b] = items
  const total = a.value + b.value
  const aPct = total > 0 ? (a.value / total) * 100 : 50
  const fmt = (v: number) => v.toLocaleString("zh-CN")
  return (
    <div className="flex w-full flex-col gap-1">
      <div className="flex items-center justify-between text-xs leading-4">
        {[a, b].map((item, i) => (
          <span key={item.label} className="inline-flex items-center gap-1.5">
            <span
              className="size-3 rounded-[4px]"
              style={{ background: item.color ?? (i === 0 ? "var(--primary)" : "var(--indigo-5)") }}
            />
            <span className="text-muted-foreground">{item.label}</span>
            <span className="text-[#0f172a]">{fmt(item.value)}</span>
          </span>
        ))}
      </div>
      <div className="flex h-1 w-full items-center gap-0.5">
        <div
          className="h-full rounded-lg"
          style={{ width: `${aPct}%`, background: a.color ?? "var(--primary)" }}
        />
        <div
          className="h-full flex-1 rounded-lg"
          style={{ background: b.color ?? "var(--indigo-5)" }}
        />
      </div>
    </div>
  )
}

/** 灰底胶囊：如「Plus 1,026」 */
export function StatPill({ label, value }: { label: string; value: React.ReactNode }) {
  return (
    <span className="inline-flex h-[22px] items-center rounded-4xl bg-secondary px-2 text-xs leading-4 font-medium text-secondary-foreground">
      <span className="text-muted-foreground">{label}</span>&nbsp;{value}
    </span>
  )
}
