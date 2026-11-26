import * as React from "react"
import { XIcon } from "lucide-react"

import { Button } from "@/components/ui/button"
import { cn } from "@/lib/utils"

/**
 * 设计稿中的分段切换（Toggle 组）：选中项 bg-muted。
 * size=default：h-9 / 14px（按周 | 按月 | 按年、DA | 大区 | 圈长）
 * size=sm：h-7 / 12px（雷达卡片右上角的 DA | 大区）
 */
export function Segmented<T extends string>({
  value,
  onValueChange,
  options,
  size = "default",
  className,
  "aria-label": ariaLabel,
}: {
  value: T
  onValueChange: (value: T) => void
  options: { value: T; label: string; disabled?: boolean }[]
  size?: "default" | "sm"
  className?: string
  "aria-label"?: string
}) {
  return (
    <div role="radiogroup" aria-label={ariaLabel} className={cn("flex items-center", className)}>
      {options.map((o) => (
        <button
          key={o.value}
          type="button"
          role="radio"
          aria-checked={o.value === value}
          disabled={o.disabled}
          data-active={o.value === value}
          onClick={() => onValueChange(o.value)}
          className={cn(
            "border border-l-0 border-border bg-background font-medium whitespace-nowrap text-foreground transition-colors first:rounded-l-lg first:border-l last:rounded-r-lg hover:bg-muted disabled:cursor-not-allowed disabled:text-muted-foreground disabled:hover:bg-background data-[active=true]:bg-muted",
            size === "default" ? "h-9 px-2.5 text-sm" : "h-7 px-2 text-xs font-semibold"
          )}
        >
          {o.label}
        </button>
      ))}
    </div>
  )
}

/** 「已带入：xxx ✕」 */
export function FocusChip({
  label,
  onClear,
  action,
}: {
  label: string
  onClear: () => void
  action?: React.ReactNode
}) {
  return (
    <div className="flex items-center gap-2">
      <span className="inline-flex h-7 items-center gap-1 rounded-4xl bg-[#eff6ff] pr-1 pl-2.5 text-xs font-medium text-primary">
        已带入：{label}
        <button
          type="button"
          onClick={onClear}
          aria-label="清除带入"
          className="flex size-5 items-center justify-center rounded-full hover:bg-primary/10"
        >
          <XIcon className="size-3" />
        </button>
      </span>
      {action}
    </div>
  )
}

export function FocusAction(props: React.ComponentProps<typeof Button>) {
  return <Button variant="link" size="xs" className="h-7 px-1" {...props} />
}
