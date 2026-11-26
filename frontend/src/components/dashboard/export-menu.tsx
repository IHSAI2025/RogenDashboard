import { DownloadIcon } from "lucide-react"
import { toast } from "sonner"

import { Button } from "@/components/ui/button"
import {
  DropdownMenu,
  DropdownMenuContent,
  DropdownMenuItem,
  DropdownMenuLabel,
  DropdownMenuSeparator,
  DropdownMenuTrigger,
} from "@/components/ui/dropdown-menu"
import type { ExportFormat } from "@/lib/export"

/** 「下载」按钮：选择 XLSX / CSV 后导出 */
export function ExportMenu({
  onExport,
  label = "下载",
  disabled,
  hint,
}: {
  onExport: (format: ExportFormat) => void | Promise<void>
  label?: string
  disabled?: boolean
  /** 下拉中的说明，如「导出当前 Tab 与筛选范围内 120 个账号」 */
  hint?: string
}) {
  const run = async (format: ExportFormat) => {
    try {
      await onExport(format)
      toast.success(`已开始导出 ${format.toUpperCase()}`)
    } catch (err) {
      console.error(err)
      toast.error("导出失败，请稍后重试")
    }
  }
  return (
    <DropdownMenu>
      <DropdownMenuTrigger asChild>
        <Button disabled={disabled}>
          <DownloadIcon />
          {label}
        </Button>
      </DropdownMenuTrigger>
      <DropdownMenuContent align="end" className="w-56">
        {hint && (
          <>
            <DropdownMenuLabel className="text-xs font-normal text-muted-foreground">{hint}</DropdownMenuLabel>
            <DropdownMenuSeparator />
          </>
        )}
        <DropdownMenuItem onSelect={() => run("xlsx")}>导出 XLSX</DropdownMenuItem>
        <DropdownMenuItem onSelect={() => run("csv")}>导出 CSV</DropdownMenuItem>
      </DropdownMenuContent>
    </DropdownMenu>
  )
}
