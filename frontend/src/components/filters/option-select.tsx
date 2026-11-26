import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select"
import { cn } from "@/lib/utils"

import { filterTriggerClass } from "./filter-trigger"

export interface Option<T extends string> {
  value: T
  label: string
}

/** 单选下拉（设计稿：选项列表 + 选中项右侧对勾） */
export function OptionSelect<T extends string>({
  value,
  onValueChange,
  options,
  className,
  "aria-label": ariaLabel,
}: {
  value: T
  onValueChange: (value: T) => void
  options: Option<T>[]
  className?: string
  "aria-label"?: string
}) {
  return (
    <Select value={value} onValueChange={(v) => onValueChange(v as T)}>
      <SelectTrigger aria-label={ariaLabel} className={cn(filterTriggerClass, "pr-2.5", className)}>
        <SelectValue />
      </SelectTrigger>
      <SelectContent position="popper" align="start" className="w-(--radix-select-trigger-width)">
        {options.map((o) => (
          <SelectItem key={o.value} value={o.value}>
            {o.label}
          </SelectItem>
        ))}
      </SelectContent>
    </Select>
  )
}
