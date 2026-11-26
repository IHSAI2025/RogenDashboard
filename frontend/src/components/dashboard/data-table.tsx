import * as React from "react"
import {
  ArrowDownIcon,
  ArrowUpDownIcon,
  ArrowUpIcon,
  ChevronLeftIcon,
  ChevronRightIcon,
  ChevronsLeftIcon,
  ChevronsRightIcon,
} from "lucide-react"

import { Button } from "@/components/ui/button"
import {
  Select,
  SelectContent,
  SelectItem,
  SelectTrigger,
  SelectValue,
} from "@/components/ui/select"
import {
  Table,
  TableBody,
  TableCell,
  TableHead,
  TableHeader,
  TableRow,
} from "@/components/ui/table"
import { cn } from "@/lib/utils"

export type SortDir = "asc" | "desc"
export interface SortState {
  key: string
  dir: SortDir
}

export interface Column<T> {
  key: string
  header: React.ReactNode
  /** 分组表头（相邻同名列合并） */
  group?: string
  align?: "left" | "right" | "center"
  /** 返回排序值；不传则该列不可排序 */
  sortValue?: (row: T) => number | string | null
  cell: (row: T) => React.ReactNode
  className?: string
  headClassName?: string
  /** 固定在左侧 */
  sticky?: boolean
  width?: number
}

function compare(a: number | string | null, b: number | string | null) {
  // 空值始终排在最后
  if (a == null && b == null) return 0
  if (a == null) return 1
  if (b == null) return -1
  if (typeof a === "number" && typeof b === "number") return a - b
  return String(a).localeCompare(String(b), "zh-CN")
}

export function sortRows<T>(rows: T[], columns: Column<T>[], sort: SortState | null) {
  if (!sort) return rows
  const col = columns.find((c) => c.key === sort.key)
  if (!col?.sortValue) return rows
  const get = col.sortValue
  return [...rows].sort((x, y) => {
    const a = get(x)
    const b = get(y)
    if (a == null || b == null) return compare(a, b)
    const r = compare(a, b)
    return sort.dir === "asc" ? r : -r
  })
}

/** 列表头点击：降序 → 升序 → 恢复默认 */
export function nextSort(current: SortState | null, key: string, fallback: SortState | null): SortState | null {
  if (!current || current.key !== key) return { key, dir: "desc" }
  if (current.dir === "desc") return { key, dir: "asc" }
  return fallback && fallback.key !== key ? fallback : null
}

export function DataTable<T>({
  columns,
  rows,
  rowKey,
  sort,
  onSortChange,
  empty = "暂无数据",
  onRowClick,
  className,
  rowClassName,
}: {
  columns: Column<T>[]
  rows: T[]
  rowKey: (row: T) => string
  sort: SortState | null
  onSortChange: (key: string) => void
  empty?: React.ReactNode
  onRowClick?: (row: T) => void
  className?: string
  /** 数据行高度等样式覆盖，默认 h-11（44px）；设计稿行高约 53px，列数较多的表可传 "h-12" 等贴近设计稿 */
  rowClassName?: string
}) {
  const hasGroups = columns.some((c) => c.group)
  const groups: { label: string; span: number }[] = []
  if (hasGroups) {
    for (const col of columns) {
      const label = col.group ?? ""
      const last = groups[groups.length - 1]
      if (last && last.label === label && label) last.span += 1
      else groups.push({ label, span: 1 })
    }
  }

  const alignClass = (align?: Column<T>["align"]) =>
    align === "right" ? "text-right" : align === "center" ? "text-center" : "text-left"

  return (
    <div className={cn("relative w-full overflow-x-auto", className)}>
      <Table className="min-w-full">
        <TableHeader className="bg-muted">
          {hasGroups && (
            <TableRow className="border-b-0 hover:bg-transparent">
              {groups.map((g, i) => (
                <TableHead
                  key={i}
                  colSpan={g.span}
                  className="h-8 text-center text-xs font-medium text-foreground"
                >
                  {g.label}
                </TableHead>
              ))}
            </TableRow>
          )}
          <TableRow className="hover:bg-transparent">
            {columns.map((col) => {
              const active = sort?.key === col.key
              const SortIcon = !active ? ArrowUpDownIcon : sort!.dir === "asc" ? ArrowUpIcon : ArrowDownIcon
              return (
                <TableHead
                  key={col.key}
                  style={col.width ? { minWidth: col.width } : undefined}
                  className={cn(
                    "h-10 text-xs font-medium whitespace-nowrap text-foreground",
                    alignClass(col.align),
                    col.sticky && "sticky left-0 z-10 bg-muted",
                    col.headClassName
                  )}
                  aria-sort={active ? (sort!.dir === "asc" ? "ascending" : "descending") : undefined}
                >
                  {col.sortValue ? (
                    <button
                      type="button"
                      onClick={() => onSortChange(col.key)}
                      className={cn(
                        "inline-flex items-center gap-1 hover:text-primary",
                        col.align === "right" && "flex-row-reverse",
                        active && "text-primary"
                      )}
                    >
                      {col.header}
                      <SortIcon className={cn("size-3.5", !active && "text-muted-foreground")} />
                    </button>
                  ) : (
                    col.header
                  )}
                </TableHead>
              )
            })}
          </TableRow>
        </TableHeader>
        <TableBody>
          {rows.length === 0 ? (
            <TableRow className="hover:bg-transparent">
              <TableCell colSpan={columns.length} className="h-32 text-center text-sm text-muted-foreground">
                {empty}
              </TableCell>
            </TableRow>
          ) : (
            rows.map((row) => (
              <TableRow
                key={rowKey(row)}
                className={cn(rowClassName ?? "h-11", onRowClick && "cursor-pointer")}
                onClick={onRowClick ? () => onRowClick(row) : undefined}
              >
                {columns.map((col) => (
                  <TableCell
                    key={col.key}
                    className={cn(
                      "text-sm whitespace-nowrap",
                      alignClass(col.align),
                      col.sticky && "sticky left-0 z-10 bg-background",
                      col.className
                    )}
                  >
                    {col.cell(row)}
                  </TableCell>
                ))}
              </TableRow>
            ))
          )}
        </TableBody>
      </Table>
    </div>
  )
}

/** 设计稿分页：Rows per page / Page x of y / 首页 上一页 下一页 末页 */
export function TablePagination({
  page,
  pageSize,
  total,
  onPageChange,
  onPageSizeChange,
  pageSizeOptions = [10, 20, 50],
}: {
  page: number
  pageSize: number
  total: number
  onPageChange: (page: number) => void
  onPageSizeChange: (size: number) => void
  pageSizeOptions?: number[]
}) {
  const pageCount = Math.max(1, Math.ceil(total / pageSize))
  const current = Math.min(page, pageCount)
  return (
    <div className="flex items-center justify-end gap-8 px-6 text-sm">
      <span className="text-muted-foreground">共 {total.toLocaleString("zh-CN")} 条</span>
      <div className="flex items-center gap-2">
        <span className="font-medium">Rows per page</span>
        <Select value={String(pageSize)} onValueChange={(v) => onPageSizeChange(Number(v))}>
          <SelectTrigger className="w-[80px]">
            <SelectValue />
          </SelectTrigger>
          <SelectContent side="top">
            {pageSizeOptions.map((s) => (
              <SelectItem key={s} value={String(s)}>
                {s}
              </SelectItem>
            ))}
          </SelectContent>
        </Select>
      </div>
      <span className="font-medium">
        Page {current} of {pageCount}
      </span>
      <div className="flex items-center gap-2">
        <Button variant="outline" size="icon" disabled={current <= 1} onClick={() => onPageChange(1)} aria-label="首页">
          <ChevronsLeftIcon />
        </Button>
        <Button variant="outline" size="icon" disabled={current <= 1} onClick={() => onPageChange(current - 1)} aria-label="上一页">
          <ChevronLeftIcon />
        </Button>
        <Button variant="outline" size="icon" disabled={current >= pageCount} onClick={() => onPageChange(current + 1)} aria-label="下一页">
          <ChevronRightIcon />
        </Button>
        <Button variant="outline" size="icon" disabled={current >= pageCount} onClick={() => onPageChange(pageCount)} aria-label="末页">
          <ChevronsRightIcon />
        </Button>
      </div>
    </div>
  )
}

/** 排序 + 分页状态 */
export function useTableState<T>(
  rows: T[],
  columns: Column<T>[],
  defaultSort: SortState | null,
  initialPageSize = 10
) {
  const [sort, setSort] = React.useState<SortState | null>(defaultSort)
  const [page, setPage] = React.useState(1)
  const [pageSize, setPageSize] = React.useState(initialPageSize)

  const sorted = React.useMemo(() => sortRows(rows, columns, sort), [rows, columns, sort])
  const pageCount = Math.max(1, Math.ceil(sorted.length / pageSize))
  const safePage = Math.min(page, pageCount)
  const pageRows = sorted.slice((safePage - 1) * pageSize, safePage * pageSize)

  return {
    sort,
    setSort,
    onSortChange: (key: string) => {
      setSort((cur) => nextSort(cur, key, defaultSort))
      setPage(1)
    },
    sorted,
    pageRows,
    page: safePage,
    setPage,
    pageSize,
    setPageSize: (s: number) => {
      setPageSize(s)
      setPage(1)
    },
  }
}
