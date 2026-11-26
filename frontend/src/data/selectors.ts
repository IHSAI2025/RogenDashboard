import { DA_TREE, daName } from "./dict"
import type { GlobalFilters } from "./types"

export { ALL_DA_IDS } from "./dict"
import { ALL_DA_IDS } from "./dict"

/** 「取消全选」后的占位值：不选任何 DA */
export const NO_DA = "__none__"

/** 「全部 DA」时为全部；否则返回选中 DA 的展示名 */
export function describeDaFilter(daIds: string[]) {
  if (daIds.includes(NO_DA)) return "未选择 DA"
  if (!daIds.length || daIds.length === ALL_DA_IDS.length) return "全部 DA"
  if (daIds.length <= 2) return daIds.map((id) => daName(id)).join("、")
  return `${daName(daIds[0])} 等 ${daIds.length} 个 DA`
}

export function describeFilters(filters: GlobalFilters) {
  return [
    `所属DA：${describeDaFilter(filters.daIds)}`,
    `账号类型：${filters.accountType === "all" ? "全部" : filters.accountType}`,
    `账号来源：${filters.source === "all" ? "全部" : filters.source}`,
    `用户身份：${filters.identity === "all" ? "全部" : filters.identity}`,
  ].join("；")
}

/** 单 DA 时下钻到「大区」维度，多 DA 时按「DA」维度（与 1.2 的分工一致） */
export function isSingleDa(daIds: string[]) {
  return daIds.length === 1
}

export function groupLeafIds(groupId: string) {
  return DA_TREE.find((g) => g.id === groupId)?.children?.map((c) => c.id) ?? []
}

export function sum<T>(list: T[], pick: (item: T) => number) {
  let s = 0
  for (const item of list) s += pick(item)
  return s
}

export function groupBy<T, K extends string>(list: T[], key: (item: T) => K) {
  const map = new Map<K, T[]>()
  for (const item of list) {
    const k = key(item)
    const bucket = map.get(k)
    if (bucket) bucket.push(item)
    else map.set(k, [item])
  }
  return map
}
