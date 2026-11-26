import { Button } from "@/components/ui/button"
import { cn } from "@/lib/utils"

/** 设计稿 Toggle 组：h-36，相邻按钮共用边框，选中项 bg-muted */
export function Segmented<T extends string>({
  value,
  onValueChange,
  options,
  className,
  "aria-label": ariaLabel,
}: {
  value: T
  onValueChange: (value: T) => void
  options: { value: T; label: string }[]
  className?: string
  "aria-label"?: string
}) {
  return (
    <div className={cn("flex items-center", className)} role="group" aria-label={ariaLabel}>
      {options.map((o) => (
        <Button
          key={o.value}
          variant="outline"
          aria-pressed={value === o.value}
          data-active={value === o.value}
          onClick={() => onValueChange(o.value)}
          className="h-9 rounded-none border-l-0 bg-background px-2.5 text-sm font-medium shadow-none first:rounded-l-lg first:border-l last:rounded-r-lg hover:bg-muted data-[active=true]:bg-muted"
        >
          {o.label}
        </Button>
      ))}
    </div>
  )
}
