import * as React from "react"
import { CircleXIcon, CloudIcon, RotateCcwIcon } from "lucide-react"

import { Button } from "@/components/ui/button"
import { cn } from "@/lib/utils"

/**
 * 图表 / 卡片的空态与报错态（design: 157:5316 空态白底、157:5340 报错）。
 * 32px 圆底图标 + 标题 + 可选说明（无则不展示）+ 可选「重试」按钮。
 */
export function ChartEmptyState({
  title = "暂无数据",
  description,
  action,
  className,
}: {
  title?: React.ReactNode
  description?: React.ReactNode
  action?: React.ReactNode
  className?: string
}) {
  return (
    <div className={cn("flex flex-col items-center justify-center gap-4 px-6 py-10", className)}>
      <div className="flex flex-col items-center gap-2">
        <span className="flex size-8 items-center justify-center rounded-lg bg-muted">
          <CloudIcon className="size-4 text-muted-foreground" />
        </span>
        <p className="text-center text-sm font-medium text-card-foreground">{title}</p>
        {description && (
          <p className="max-w-96 text-center text-sm text-muted-foreground">{description}</p>
        )}
      </div>
      {action}
    </div>
  )
}

export function ChartErrorState({
  title = "加载失败",
  description,
  onRetry,
  className,
}: {
  title?: React.ReactNode
  description?: React.ReactNode
  onRetry?: () => void
  className?: string
}) {
  return (
    <div className={cn("flex flex-col items-center justify-center gap-4 px-6 py-10", className)}>
      <div className="flex flex-col items-center gap-2">
        <span className="flex size-8 items-center justify-center rounded-lg bg-destructive/10">
          <CircleXIcon className="size-4 text-destructive" />
        </span>
        <p className="text-center text-sm font-medium text-card-foreground">{title}</p>
        {description && (
          <p className="max-w-96 text-center text-sm text-muted-foreground">{description}</p>
        )}
      </div>
      {onRetry && (
        <Button variant="outline" size="sm" onClick={onRetry}>
          <RotateCcwIcon />
          重试
        </Button>
      )}
    </div>
  )
}

/** 通用「重试」按钮（空态也可能需要，如维度切换无数据时的引导操作） */
export function RetryButton(props: React.ComponentProps<typeof Button>) {
  return (
    <Button variant="outline" size="sm" {...props}>
      <RotateCcwIcon />
      {props.children ?? "重试"}
    </Button>
  )
}
