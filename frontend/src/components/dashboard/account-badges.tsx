import { Badge } from "@/components/ui/badge"
import type { AccountSource, UsageStatus } from "@/data/types"
import { cn } from "@/lib/utils"

/**
 * 账号相关的通用状态徽标：使用状态（活跃/休眠/沉默）、来源（采购/免费）、可用状态（可用/停用）。
 * 跨 Tab 共用（用户数据下钻的账号详情抽屉、费用看板的账号费用详情抽屉），保证视觉一致。
 */

const STATUS_STYLE: Record<UsageStatus, string> = {
  活跃: "bg-[#dcfce7] text-[#15803d]",
  休眠: "bg-[#fef3c7] text-[#b45309]",
  沉默: "bg-secondary text-muted-foreground",
}

export function UsageStatusBadge({ status }: { status: UsageStatus }) {
  return <Badge className={cn("rounded-4xl", STATUS_STYLE[status])}>{status}</Badge>
}

export function SourceBadge({ source }: { source: AccountSource }) {
  return (
    <Badge variant="outline" className={source === "采购" ? "border-primary/30 text-primary" : ""}>
      {source}
    </Badge>
  )
}

export function EnabledBadge({ enabled }: { enabled: boolean }) {
  return (
    <Badge
      variant={enabled ? "secondary" : "destructive"}
      className={enabled ? "text-[#15803d]" : ""}
    >
      {enabled ? "可用" : "停用"}
    </Badge>
  )
}
