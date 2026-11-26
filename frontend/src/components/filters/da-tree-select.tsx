import * as React from "react"
import { ChevronDownIcon, ChevronRightIcon } from "lucide-react"

import { Checkbox } from "@/components/ui/checkbox"
import { Input } from "@/components/ui/input"
import { Popover, PopoverContent, PopoverTrigger } from "@/components/ui/popover"
import { DA_TREE } from "@/data/dict"
import { ALL_DA_IDS, NO_DA, describeDaFilter } from "@/data/selectors"
import type { DaNode } from "@/data/types"
import { cn } from "@/lib/utils"

import { FilterTrigger } from "./filter-trigger"

type CheckState = boolean | "indeterminate"

function leafIds(node: DaNode): string[] {
  return node.children?.length ? node.children.flatMap(leafIds) : [node.id]
}

function checkState(ids: string[], selected: Set<string>): CheckState {
  const hit = ids.filter((id) => selected.has(id)).length
  if (hit === 0) return false
  if (hit === ids.length) return true
  return "indeterminate"
}

/**
 * 所属 DA：树形多选，支持搜索、全选/取消全选。
 * value 为空数组表示「全部 DA」。
 */
export function DaTreeSelect({
  value,
  onValueChange,
  /** 限定可选范围（DA 管理员只出现授权 DA）；不传为全部 */
  scopeIds,
  disabled,
}: {
  value: string[]
  onValueChange: (ids: string[]) => void
  scopeIds?: string[]
  disabled?: boolean
}) {
  const [open, setOpen] = React.useState(false)
  const [query, setQuery] = React.useState("")
  const [expanded, setExpanded] = React.useState<Set<string>>(() => new Set([DA_TREE[0].id]))

  const scope = React.useMemo(() => new Set(scopeIds ?? ALL_DA_IDS), [scopeIds])
  const tree = React.useMemo(() => {
    const q = query.trim().toLowerCase()
    return DA_TREE.map((group) => {
      const children = (group.children ?? []).filter(
        (c) =>
          scope.has(c.id) &&
          (!q || c.name.toLowerCase().includes(q) || group.name.toLowerCase().includes(q))
      )
      return { ...group, children }
    }).filter((g) => g.children.length > 0)
  }, [query, scope])

  const allIds = React.useMemo(() => [...scope], [scope])
  // 空数组 = 全部
  const selected = React.useMemo(
    () => new Set(value.length ? value.filter((id) => id !== NO_DA) : allIds),
    [value, allIds]
  )

  const commit = (next: Set<string>) => {
    const ids = allIds.filter((id) => next.has(id))
    if (ids.length === 0) onValueChange([NO_DA])
    else onValueChange(ids.length === allIds.length ? [] : ids)
  }

  const toggleIds = (ids: string[], state: CheckState) => {
    const next = new Set(selected)
    if (state === true) ids.forEach((id) => next.delete(id))
    else ids.forEach((id) => next.add(id))
    commit(next)
  }

  const toggleExpand = (id: string) => {
    setExpanded((prev) => {
      const next = new Set(prev)
      if (next.has(id)) next.delete(id)
      else next.add(id)
      return next
    })
  }

  const allState = checkState(allIds, selected)
  const label = describeDaFilter(value)

  return (
    <Popover open={open} onOpenChange={setOpen}>
      <PopoverTrigger asChild disabled={disabled}>
        <FilterTrigger label={label} aria-label="所属DA" disabled={disabled} />
      </PopoverTrigger>
      <PopoverContent align="start" className="w-[193px] gap-0 p-1">
        <Input
          value={query}
          onChange={(e) => setQuery(e.target.value)}
          placeholder="Search"
          className="mb-1 h-8"
        />
        <div className="max-h-80 overflow-y-auto">
          <TreeRow
            label="全部"
            state={allState}
            onToggle={() => {
              // 全选 ↔ 取消全选
              commit(allState === true ? new Set() : new Set(allIds))
            }}
          />
          {tree.map((group) => {
            const ids = group.children.flatMap(leafIds)
            const isOpen = expanded.has(group.id) || query.trim().length > 0
            return (
              <React.Fragment key={group.id}>
                <TreeRow
                  label={group.name}
                  state={checkState(ids, selected)}
                  onToggle={() => toggleIds(ids, checkState(ids, selected))}
                  expandable
                  expanded={isOpen}
                  onExpand={() => toggleExpand(group.id)}
                />
                {isOpen &&
                  group.children.map((leaf) => (
                    <TreeRow
                      key={leaf.id}
                      label={leaf.name}
                      depth={1}
                      state={selected.has(leaf.id)}
                      onToggle={() => toggleIds([leaf.id], selected.has(leaf.id))}
                    />
                  ))}
              </React.Fragment>
            )
          })}
          {tree.length === 0 && (
            <p className="px-2 py-6 text-center text-sm text-muted-foreground">无匹配 DA</p>
          )}
        </div>
      </PopoverContent>
    </Popover>
  )
}

function TreeRow({
  label,
  state,
  onToggle,
  depth = 0,
  expandable,
  expanded,
  onExpand,
}: {
  label: string
  state: CheckState
  onToggle: () => void
  depth?: number
  expandable?: boolean
  expanded?: boolean
  onExpand?: () => void
}) {
  return (
    <div
      className={cn(
        "flex h-7 items-center gap-2 rounded-md pr-2 text-sm hover:bg-accent",
        depth === 0 ? "pl-1.5" : "pl-12"
      )}
    >
      {depth === 0 &&
        (expandable ? (
          <button
            type="button"
            onClick={onExpand}
            className="flex size-4 items-center justify-center text-muted-foreground"
            aria-label={expanded ? "收起" : "展开"}
          >
            {expanded ? (
              <ChevronDownIcon className="size-4" />
            ) : (
              <ChevronRightIcon className="size-4" />
            )}
          </button>
        ) : null)}
      <label className="flex flex-1 cursor-pointer items-center gap-2 truncate">
        <Checkbox checked={state} onCheckedChange={onToggle} />
        <span className="truncate">{label}</span>
      </label>
    </div>
  )
}
