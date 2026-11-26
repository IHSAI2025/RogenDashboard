import * as React from "react"

/**
 * 账号详情抽屉共用的指标小格：标签在上、数值在下。
 * 跨 Tab 共用（用户数据下钻 / 费用看板的账号详情抽屉），保证两处视觉一致。
 * 数值字号与全站其余「大数字」卡片一致（text-xl/leading-7/font-semibold）。
 */
export function SheetStat({
  label,
  value,
  /** 数值下方的补充说明（如预算使用率的分子/分母），避免把两类信息硬塞进同一行导致溢出 */
  caption,
  /** 值本身较长（如备注）时缩小字号并允许两行截断 */
  small,
}: {
  label: string
  value: React.ReactNode
  caption?: React.ReactNode
  small?: boolean
}) {
  return (
    <div className="flex min-w-0 flex-col gap-1">
      <span className="text-xs text-muted-foreground">{label}</span>
      <span
        className={small ? "line-clamp-2 text-xs leading-4" : "text-xl leading-7 font-semibold tabular-nums"}
        title={typeof value === "string" ? value : undefined}
      >
        {value}
      </span>
      {caption != null && (
        <span
          className="truncate text-xs text-muted-foreground"
          title={typeof caption === "string" ? caption : undefined}
        >
          {caption}
        </span>
      )}
    </div>
  )
}

/**
 * 账号基础信息行（账号ID / 联系电话 / 所属DA 等）：固定两列网格对齐，
 * 避免 flex-wrap 的 label：value 文本在窄屏下换行错位、参差不齐。
 */
export function SheetMetaGrid({
  items,
}: {
  items: { label: string; value: React.ReactNode }[]
}) {
  return (
    <div className="grid grid-cols-2 gap-x-6 gap-y-1.5 text-sm">
      {items.map((item) => (
        <div key={item.label} className="flex min-w-0 gap-1.5">
          <span className="shrink-0 text-muted-foreground">{item.label}：</span>
          <span
            className="min-w-0 truncate font-medium text-foreground"
            title={typeof item.value === "string" ? item.value : undefined}
          >
            {item.value}
          </span>
        </div>
      ))}
    </div>
  )
}

/** 指标小格的网格容器 */
export function SheetStatGrid({
  children,
  cols = 4,
}: {
  children: React.ReactNode
  cols?: 3 | 4
}) {
  return (
    <div className={cols === 3 ? "grid grid-cols-3 gap-4" : "grid grid-cols-4 gap-4"}>
      {children}
    </div>
  )
}
