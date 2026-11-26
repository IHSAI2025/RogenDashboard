import * as React from "react"

import { cn } from "@/lib/utils"

/* ------------------------------------------------------------------ */
/* 系列显隐状态                                                         */
/* ------------------------------------------------------------------ */

/**
 * 图表系列显隐。点击图例切换，隐藏集合内的 key 不参与绘制。
 * 允许全部隐藏（图表留白），再次点击任意图例即可恢复。
 */
export function useSeriesToggle(initialHidden: readonly string[] = []) {
  const [hidden, setHidden] = React.useState<Set<string>>(() => new Set(initialHidden))

  const toggle = React.useCallback((key: string) => {
    setHidden((prev) => {
      const next = new Set(prev)
      if (next.has(key)) next.delete(key)
      else next.add(key)
      return next
    })
  }, [])

  const reset = React.useCallback(() => setHidden(new Set<string>()), [])

  return { hidden, toggle, reset }
}

/* ------------------------------------------------------------------ */
/* 图例标记                                                            */
/* ------------------------------------------------------------------ */

export type LegendMarkerShape =
  /** 实心圆角方块：柱状图 / 占比图（默认） */
  | "square"
  /** 实心圆点：散点 / 气泡图 */
  | "dot"
  /** 实线段：折线图 */
  | "line"
  /** 虚线段：参考线 / 预警线 */
  | "dash"
  /** 虚线 + 方块标记：带数据点的虚线折线 */
  | "dashed-line"

export function LegendMarker({ shape = "square", color }: { shape?: LegendMarkerShape; color: string }) {
  switch (shape) {
    case "dot":
      return <span className="size-2 shrink-0 rounded-full" style={{ background: color }} />
    case "line":
      return <span className="h-0.5 w-3.5 shrink-0 rounded-full" style={{ background: color }} />
    case "dash":
      return (
        <svg width={14} height={8} viewBox="0 0 14 8" className="shrink-0" aria-hidden>
          <line
            x1={0}
            y1={4}
            x2={14}
            y2={4}
            stroke={color || "currentColor"}
            strokeWidth={1.5}
            strokeDasharray="3 2"
          />
        </svg>
      )
    case "dashed-line":
      return (
        <svg width={20} height={10} viewBox="0 0 20 10" className="shrink-0" aria-hidden>
          <line x1={0} y1={5} x2={20} y2={5} stroke={color} strokeWidth={1.5} strokeDasharray="3 2" />
          <rect x={6} y={1} width={8} height={8} rx={1.5} fill={color} />
        </svg>
      )
    default:
      return <span className="size-2.5 shrink-0 rounded-[2px]" style={{ background: color }} />
  }
}

/* ------------------------------------------------------------------ */
/* 可点击图例                                                           */
/* ------------------------------------------------------------------ */

export interface LegendSeries {
  key: string
  label: React.ReactNode
  color: string
  marker?: LegendMarkerShape
  /** 标签右侧的附加信息，如占比数值 */
  meta?: React.ReactNode
}

/**
 * 可点击切换显隐的图表图例。
 * 隐藏态：标记降到 30% 不透明度 + 文字转灰并加删除线，并通过 aria-pressed 暴露状态。
 */
export function ChartLegendToggle({
  series,
  hidden,
  onToggle,
  onHoverChange,
  size = "sm",
  orientation = "horizontal",
  className,
  itemClassName,
}: {
  series: readonly LegendSeries[]
  hidden: ReadonlySet<string>
  onToggle: (key: string) => void
  /** 鼠标悬停某个图例项 / 移出时回调（如：趋势图悬停图例展示该指标峰值标注） */
  onHoverChange?: (key: string | null) => void
  size?: "sm" | "md"
  orientation?: "horizontal" | "vertical"
  className?: string
  itemClassName?: string
}) {
  return (
    <div
      role="group"
      aria-label="图例（点击切换显示）"
      className={cn(
        "flex",
        orientation === "horizontal"
          ? "flex-wrap items-center gap-x-4 gap-y-1"
          : "flex-col items-start gap-3",
        className
      )}
    >
      {series.map((item) => {
        const isHidden = hidden.has(item.key)
        return (
          <button
            key={item.key}
            type="button"
            aria-pressed={!isHidden}
            onClick={() => onToggle(item.key)}
            onMouseEnter={() => onHoverChange?.(item.key)}
            onMouseLeave={() => onHoverChange?.(null)}
            title={isHidden ? "点击显示" : "点击隐藏"}
            className={cn(
              "inline-flex cursor-pointer items-center gap-1.5 rounded-md px-1 py-0.5 leading-4 whitespace-nowrap",
              "transition-colors hover:bg-muted focus-visible:ring-[3px] focus-visible:ring-ring/50 focus-visible:outline-none",
              size === "sm" ? "text-xs" : "text-sm",
              isHidden ? "text-muted-foreground" : "text-card-foreground",
              itemClassName
            )}
          >
            <span className={cn("inline-flex items-center", isHidden && "opacity-30 grayscale")}>
              <LegendMarker shape={item.marker} color={item.color} />
            </span>
            <span className={cn(isHidden && "line-through decoration-muted-foreground/60")}>{item.label}</span>
            {item.meta != null && <span className="text-muted-foreground tabular-nums">{item.meta}</span>}
          </button>
        )
      })}
    </div>
  )
}
