import * as React from "react"
import { format } from "date-fns"
import { SearchIcon } from "lucide-react"
import { toast } from "sonner"

import { download } from "@/api/client"
import { useScopeParams } from "@/api/params"
import { useApi } from "@/api/use-api"
import { DataTable, TablePagination, useTableState } from "@/components/dashboard/data-table"
import { ExportMenu } from "@/components/dashboard/export-menu"
import { CardTitleText, DashCard } from "@/components/dashboard/primitives"
import { OptionSelect } from "@/components/filters/option-select"
import { Input } from "@/components/ui/input"
import { Tabs, TabsList, TabsTrigger } from "@/components/ui/tabs"
import { useDashboard } from "@/context/dashboard"
import { DATA_AS_OF, REGIONS } from "@/data/dict"
import type { UsageStatus } from "@/data/types"
import { fmtInt, fmtPeriod } from "@/lib/format"

import { AccountSheet } from "./account-sheet"
import { buildColumns } from "./columns"
import type { UserListResponse, UserRow } from "./types"

type StatusTab = UsageStatus | "all"

const STATUS_TABS: { value: StatusTab; label: string }[] = [
  { value: "all", label: "全部" },
  { value: "活跃", label: "活跃用户" },
  { value: "休眠", label: "休眠用户" },
  { value: "沉默", label: "沉默用户" },
]

function useDebounced<T>(value: T, ms = 300) {
  const [v, setV] = React.useState(value)
  React.useEffect(() => {
    const t = setTimeout(() => setV(value), ms)
    return () => clearTimeout(t)
  }, [value, ms])
  return v
}

export function UserDrilldownTab() {
  const { filters, period, usersPreset } = useDashboard()
  const scope = useScopeParams()

  const [status, setStatus] = React.useState<StatusTab>("all")
  const [region, setRegion] = React.useState<string>("all")
  const [enabled, setEnabled] = React.useState<string>("all")
  const [query, setQuery] = React.useState("")
  const [loginUnused, setLoginUnused] = React.useState(false)
  const [selected, setSelected] = React.useState<UserRow | null>(null)
  const [sheetOpen, setSheetOpen] = React.useState(false)

  // 其他 Tab 跳转过来时带入的状态 / 大区
  React.useEffect(() => {
    if (usersPreset.status) setStatus(usersPreset.status)
    setRegion(usersPreset.region ?? "all")
    setLoginUnused(!!usersPreset.loginUnused)
  }, [usersPreset])

  // 全部口径（使用状态、各率、导出）由后端计算并按角色裁剪 DA 范围；前端只传筛选条件
  const q = useDebounced(query.trim())
  const listParams = React.useMemo(
    () => ({
      ...scope,
      state: status,
      enabled: enabled === "all" ? undefined : enabled,
      region: region === "all" ? undefined : region,
      q: q || undefined,
      login_unused: loginUnused && (status === "休眠" || status === "沉默") ? true : undefined,
    }),
    [scope, status, enabled, region, q, loginUnused]
  )
  const { data, loading, error } = useApi<UserListResponse>("/vm/users/list", listParams)
  const rows = React.useMemo(() => data?.rows ?? [], [data])
  const counts = data?.counts ?? { all: 0, 活跃: 0, 休眠: 0, 沉默: 0 }
  const loginUnusedCounts = data?.loginUnusedCounts ?? { 休眠: 0, 沉默: 0 }

  const columns = React.useMemo(
    () =>
      buildColumns((row) => {
        setSelected(row)
        setSheetOpen(true)
      }),
    []
  )

  const table = useTableState(rows, columns, { key: "featureTotal", dir: "desc" })
  const { setPage } = table
  React.useEffect(() => {
    setPage(1)
  }, [status, region, enabled, q, filters, period, setPage])

  // 导出与页面一致：当前状态 Tab + 筛选范围，由后端生成（含筛选条件、数据截至时间、口径版本、分子分母）
  const handleExport = async (formatType: "xlsx" | "csv") => {
    try {
      await download("/vm/users/export", { ...listParams, fmt: formatType })
    } catch (e) {
      toast.error((e as Error).message)
    }
  }

  return (
    <div className="px-6">
      <DashCard className="gap-0 pt-6 pb-6">
        <div className="flex flex-wrap items-center gap-3 px-6 pb-4">
          <CardTitleText className="mr-auto">用户明细表</CardTitleText>
          <div className="relative">
            <SearchIcon className="pointer-events-none absolute top-1/2 left-2.5 size-4 -translate-y-1/2 text-muted-foreground" />
            <Input
              value={query}
              onChange={(e) => setQuery(e.target.value)}
              placeholder="按姓名或账号ID搜索"
              className="h-9 w-[200px] pl-8"
            />
          </div>
          <OptionSelect
            aria-label="大区"
            value={region}
            onValueChange={setRegion}
            className="w-[140px]"
            options={[
              { value: "all", label: "全部大区" },
              ...REGIONS.map((r) => ({ value: r, label: r })),
            ]}
          />
          <OptionSelect
            aria-label="可用状态"
            value={enabled}
            onValueChange={setEnabled}
            className="w-[140px]"
            options={[
              { value: "all", label: "全部可用状态" },
              { value: "正常", label: "正常" },
              { value: "停用", label: "停用" },
            ]}
          />
          <ExportMenu
            onExport={handleExport}
            disabled={rows.length === 0}
            hint={`导出当前 Tab 与筛选范围内 ${fmtInt(rows.length)} 个账号`}
          />
        </div>

        {/* 状态 Tab 独占一行，与标题行、筛选项分离 */}
        <div className="flex flex-wrap items-center justify-between gap-x-4 gap-y-2 px-6 pb-3">
          <Tabs value={status} onValueChange={(v) => setStatus(v as StatusTab)}>
            <TabsList className="h-9">
              {STATUS_TABS.map((t) => (
                <TabsTrigger key={t.value} value={t.value} className="px-2.5">
                  {t.label}
                  <span className="text-xs text-muted-foreground tabular-nums">
                    {fmtInt(counts[t.value])}
                  </span>
                </TabsTrigger>
              ))}
            </TabsList>
          </Tabs>
          {(status === "休眠" || status === "沉默") && (
            <label className="flex cursor-pointer items-center gap-1.5 text-sm">
              <input type="checkbox" checked={loginUnused} onChange={(e) => setLoginUnused(e.target.checked)} />
              仅看登录未使用
              <span className="text-xs text-muted-foreground tabular-nums">{fmtInt(loginUnusedCounts[status])}</span>
              <span className="text-xs text-muted-foreground">（导出即优先唤醒名单）</span>
            </label>
          )}
          <p className="text-xs text-muted-foreground">
            统计周期：{fmtPeriod(period)} ｜ 数据截至：{format(DATA_AS_OF, "yyyy-MM-dd HH:mm")} ｜
            口径：有使用记录（PubMed 检索 / 大纲 / 内容库分享 / 成功生成）为活跃，只登录不算使用；未使用且非沉默为休眠；
            周期内及连续 60 天无使用且开通满 60 天为沉默（仅判定有效账号）
          </p>
        </div>

        {error ? (
          <p className="px-6 py-6 text-sm text-destructive">数据加载失败：{error}</p>
        ) : loading && !data ? (
          <p className="px-6 py-10 text-center text-sm text-muted-foreground">加载中…</p>
        ) : null}
        <DataTable
          columns={columns}
          rows={table.pageRows}
          rowKey={(r) => String(r.id)}
          sort={table.sort}
          onSortChange={table.onSortChange}
          empty="当前筛选条件下暂无账号"
          className="border-y"
        />

        <div className="pt-4">
          <TablePagination
            page={table.page}
            pageSize={table.pageSize}
            total={rows.length}
            onPageChange={table.setPage}
            onPageSizeChange={table.setPageSize}
          />
        </div>
      </DashCard>

      <AccountSheet
        row={selected}
        end={data?.period.end ?? null}
        open={sheetOpen}
        onOpenChange={setSheetOpen}
      />
    </div>
  )
}
