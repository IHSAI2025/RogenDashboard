import * as React from "react"
import { format, isAfter, isBefore, isSameMonth, startOfMonth } from "date-fns"
import { CalendarIcon, ChevronLeftIcon, ChevronRightIcon } from "lucide-react"

import { Button } from "@/components/ui/button"
import { Popover, PopoverContent, PopoverTrigger } from "@/components/ui/popover"
import { cn } from "@/lib/utils"

import { filterTriggerClass } from "./filter-trigger"

/**
 * 统计月份：选择年份 + 月份（YYYY-MM），按自然月计算；一期不支持自定义日期范围。
 */
export function MonthPicker({
  value,
  onValueChange,
  min,
  max,
}: {
  value: Date
  onValueChange: (month: Date) => void
  min: Date
  max: Date
}) {
  const [open, setOpen] = React.useState(false)
  const [year, setYear] = React.useState(value.getFullYear())

  return (
    <Popover
      open={open}
      onOpenChange={(next) => {
        setOpen(next)
        if (next) setYear(value.getFullYear())
      }}
    >
      <PopoverTrigger asChild>
        <button type="button" className={cn(filterTriggerClass, "w-[160px]")} aria-label="统计月份">
          <CalendarIcon className="size-4 text-muted-foreground" />
          <span className="flex-1 text-left">{format(value, "yyyy-MM")}</span>
        </button>
      </PopoverTrigger>
      <PopoverContent align="end" className="w-64 p-3">
        <div className="mb-2 flex items-center justify-between">
          <Button
            variant="ghost"
            size="icon-sm"
            aria-label="上一年"
            disabled={year <= min.getFullYear()}
            onClick={() => setYear((y) => y - 1)}
          >
            <ChevronLeftIcon />
          </Button>
          <span className="text-sm font-medium">{year} 年</span>
          <Button
            variant="ghost"
            size="icon-sm"
            aria-label="下一年"
            disabled={year >= max.getFullYear()}
            onClick={() => setYear((y) => y + 1)}
          >
            <ChevronRightIcon />
          </Button>
        </div>
        <div className="grid grid-cols-4 gap-1">
          {Array.from({ length: 12 }, (_, i) => {
            const month = new Date(year, i, 1)
            const disabled =
              isBefore(month, startOfMonth(min)) || isAfter(month, startOfMonth(max))
            const selected = isSameMonth(month, value)
            return (
              <Button
                key={i}
                size="sm"
                variant={selected ? "default" : "ghost"}
                disabled={disabled}
                onClick={() => {
                  onValueChange(month)
                  setOpen(false)
                }}
              >
                {i + 1} 月
              </Button>
            )
          })}
        </div>
      </PopoverContent>
    </Popover>
  )
}
