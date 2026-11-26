import * as React from "react"
import { format, isSameMonth, startOfDay } from "date-fns"
import { zhCN } from "date-fns/locale"
import type { DateRange } from "react-day-picker"

import { Button } from "@/components/ui/button"
import { Calendar } from "@/components/ui/calendar"
import { Popover, PopoverContent, PopoverTrigger } from "@/components/ui/popover"
import { monthPeriod } from "@/context/dashboard"
import { LAST_DATA_DAY, PLATFORM_LAUNCH } from "@/data/dict"
import type { Period } from "@/data/types"
import { fmtDate } from "@/lib/format"
import { cn } from "@/lib/utils"

const segmentClass =
  "h-9 rounded-none border border-l-0 border-border bg-background px-2.5 text-sm font-medium text-foreground shadow-none first:rounded-l-lg first:border-l last:rounded-r-lg hover:bg-muted data-[active=true]:bg-muted"

/**
 * 月份 toggle：展示当前所处月份及前 2 个月 + 自定义周期按钮，默认选中当前所处月份。
 * 选择自定义周期后按钮文案变为所选区间。
 */
export function PeriodToggle({
  months,
  value,
  onValueChange,
}: {
  months: Date[]
  value: Period
  onValueChange: (period: Period) => void
}) {
  const [open, setOpen] = React.useState(false)
  const [draft, setDraft] = React.useState<DateRange | undefined>(
    value.kind === "custom" ? { from: value.start, to: value.end } : undefined
  )

  const applyRange = () => {
    if (!draft?.from) return
    onValueChange({
      kind: "custom",
      start: startOfDay(draft.from),
      end: startOfDay(draft.to ?? draft.from),
    })
    setOpen(false)
  }

  return (
    <div className="flex items-center" role="group" aria-label="统计周期">
      {months.map((m) => (
        <Button
          key={m.toISOString()}
          variant="outline"
          data-active={value.kind === "month" && isSameMonth(value.start, m)}
          className={segmentClass}
          onClick={() => onValueChange(monthPeriod(m))}
        >
          {format(m, "M")} 月
        </Button>
      ))}
      <Popover
        open={open}
        onOpenChange={(next) => {
          setOpen(next)
          if (next) {
            setDraft(value.kind === "custom" ? { from: value.start, to: value.end } : undefined)
          }
        }}
      >
        <PopoverTrigger asChild>
          <Button
            variant="outline"
            data-active={value.kind === "custom" || open}
            className={segmentClass}
          >
            {value.kind === "custom"
              ? `${fmtDate(value.start)} - ${fmtDate(value.end)}`
              : "自定义周期"}
          </Button>
        </PopoverTrigger>
        <PopoverContent align="end" className="w-auto p-0">
          <Calendar
            mode="range"
            numberOfMonths={2}
            locale={zhCN}
            selected={draft}
            onSelect={setDraft}
            defaultMonth={draft?.from ?? months[months.length - 2]}
            disabled={{ before: PLATFORM_LAUNCH, after: LAST_DATA_DAY }}
            startMonth={PLATFORM_LAUNCH}
            endMonth={LAST_DATA_DAY}
          />
          <div className="flex items-center justify-between gap-2 border-t px-3 py-2">
            <span className={cn("text-xs text-muted-foreground")}>
              {draft?.from
                ? `${fmtDate(draft.from)} - ${fmtDate(draft.to ?? draft.from)}`
                : "请选择开始与结束日期"}
            </span>
            <div className="flex gap-2">
              <Button size="sm" variant="outline" onClick={() => setOpen(false)}>
                取消
              </Button>
              <Button size="sm" disabled={!draft?.from} onClick={applyRange}>
                确定
              </Button>
            </div>
          </div>
        </PopoverContent>
      </Popover>
    </div>
  )
}
