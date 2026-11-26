import { download } from "@/api/client"
import { filterParams, periodParams } from "@/api/params"
import { HgFileExport } from "@/components/dashboard/hugeicons"
import { DaTreeSelect } from "@/components/filters/da-tree-select"
import { MonthPicker } from "@/components/filters/month-picker"
import { OptionSelect } from "@/components/filters/option-select"
import { PeriodToggle } from "@/components/filters/period-toggle"
import { endOfMonth, startOfMonth } from "date-fns"
import { toast } from "sonner"

import { Button } from "@/components/ui/button"
import { SidebarTrigger } from "@/components/ui/sidebar"
import { TabsList, TabsTrigger } from "@/components/ui/tabs"
import { type DashboardTab, useDashboard } from "@/context/dashboard"
import { COST_LAUNCH, TODAY, ymd } from "@/data/dict"
import type { AccountSource, AccountType, Identity } from "@/data/types"
import { CURRENT_USER, canSeeCostTab } from "@/lib/auth"

const TABS: { value: DashboardTab; label: string }[] = [
  { value: "overview", label: "全景看板" },
  { value: "da", label: "DA 数据下钻" },
  { value: "users", label: "用户数据下钻" },
  { value: "cost", label: "费用看板" },
]

export function DashboardHeader() {
  const {
    tab,
    filters,
    setFilters,
    monthOptions,
    period,
    setPeriod,
    costMonth,
    setCostMonth,
  } = useDashboard()

  const tabs = TABS.filter((t) => t.value !== "cost" || canSeeCostTab(CURRENT_USER))
  const isDaAdmin = CURRENT_USER.role === "da_admin"

  return (
    <header className="sticky top-0 z-20 flex flex-col gap-2 rounded-t-xl border-b bg-background pt-3">
      <div className="flex items-center gap-2 px-6">
        {/* 侧边栏收起后（offcanvas）内部的触发器也随之消失，这里始终保留一个可点击的入口 */}
        <SidebarTrigger className="-ml-1" />
        <h1 className="flex-1 truncate text-base leading-6 font-medium">神笔小罗 · 使用数据看板</h1>
        <Button
          data-print="hide"
          onClick={() =>
            // PRD 4.x：导出 HTML 报告（后端按当前筛选与角色数据范围生成；周期取当前统计周期，费用 Tab 取统计月份）
            download("/report/html", {
              ...filterParams(filters),
              ...(tab === "cost"
                ? { start: ymd(startOfMonth(costMonth)), end: ymd(endOfMonth(costMonth)), mode: "mom" }
                : periodParams(period)),
            }).catch((e: Error) => toast.error(e.message))
          }
        >
          <HgFileExport />
          导出报告
        </Button>
      </div>

      <div className="flex flex-wrap items-center justify-between gap-y-2 px-6">
        <div className="flex flex-wrap items-center gap-4">
          <DaTreeSelect
            value={filters.daIds}
            onValueChange={(daIds) => setFilters({ daIds })}
            scopeIds={isDaAdmin ? CURRENT_USER.authorizedDaIds : undefined}
            disabled={isDaAdmin && CURRENT_USER.authorizedDaIds.length <= 1}
          />
          <OptionSelect<AccountType | "all">
            aria-label="账号类型"
            value={filters.accountType}
            onValueChange={(accountType) => setFilters({ accountType })}
            options={[
              { value: "all", label: "全部账号类型" },
              { value: "PLUS", label: "PLUS 账号" },
              { value: "SUPER", label: "Super 账号" },
            ]}
          />
          <OptionSelect<AccountSource | "all">
            aria-label="账号来源"
            value={filters.source}
            onValueChange={(source) => setFilters({ source })}
            options={[
              { value: "all", label: "全部账号来源" },
              { value: "采购", label: "采购" },
              { value: "免费", label: "免费" },
            ]}
          />
          <OptionSelect<Identity | "all">
            aria-label="用户身份"
            value={filters.identity}
            onValueChange={(identity) => setFilters({ identity })}
            options={[
              { value: "all", label: "全部用户" },
              { value: "客户", label: "客户" },
              { value: "员工", label: "员工" },
            ]}
          />
        </div>
        {tab === "cost" ? (
          <MonthPicker value={costMonth} onValueChange={setCostMonth} min={COST_LAUNCH} max={TODAY} />
        ) : (
          <PeriodToggle months={monthOptions} value={period} onValueChange={setPeriod} />
        )}
      </div>

      <TabsList variant="line" className="h-auto gap-0 px-6 pt-3 pb-0">
        {tabs.map((t) => (
          <TabsTrigger
            key={t.value}
            value={t.value}
            className="h-[25px] flex-none border-none px-2.5 pb-1 text-muted-foreground focus-visible:ring-0 focus-visible:outline-none data-active:text-foreground group-data-horizontal/tabs:after:bottom-0"
          >
            {t.label}
          </TabsTrigger>
        ))}
      </TabsList>
    </header>
  )
}
