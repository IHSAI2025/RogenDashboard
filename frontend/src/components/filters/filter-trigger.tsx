import * as React from "react"
import { ChevronDownIcon } from "lucide-react"

import { cn } from "@/lib/utils"

/** 设计稿 NativeSelect 外观：h-36 / w-193 / rounded-md / shadow-xs */
export const filterTriggerClass =
  "flex h-9 w-[193px] items-center gap-2 overflow-hidden rounded-md border border-border bg-background px-2.5 text-sm shadow-xs outline-none transition-colors hover:bg-muted/40 focus-visible:border-ring focus-visible:ring-3 focus-visible:ring-ring/50 data-[state=open]:border-ring"

export const FilterTrigger = React.forwardRef<
  HTMLButtonElement,
  React.ComponentProps<"button"> & { label: React.ReactNode }
>(function FilterTrigger({ label, className, ...props }, ref) {
  return (
    <button ref={ref} type="button" className={cn(filterTriggerClass, className)} {...props}>
      <span className="flex-1 truncate text-left">{label}</span>
      <ChevronDownIcon className="size-4 shrink-0 text-foreground" />
    </button>
  )
})
