import * as React from "react"

/*
 * 气泡标签避让：按气泡从大到小依次放置标签，依次尝试 上 / 下 / 右 / 左，
 * 与已放置标签或其他气泡重叠则换位置；四个位置都冲突时隐藏标签（悬停气泡时再显示）。
 */

export interface PlotGeometry {
  width: number
  height: number
  margin: { top: number; right: number; bottom: number; left: number }
  yAxisWidth: number
  xAxisHeight: number
  xDomain: [number, number]
  yDomain: [number, number]
  /** ZAxis：数据范围 → 气泡面积范围 */
  zDomain: [number, number]
  zRange: [number, number]
}

export interface LabelPlacement {
  /** 文本锚点相对气泡中心的偏移 */
  dx: number
  dy: number
  anchor: "start" | "middle" | "end"
}

interface Box {
  x1: number
  y1: number
  x2: number
  y2: number
}

const FONT_SIZE = 12
const GAP = 4

function textWidth(text: string) {
  let w = 0
  for (const ch of text) w += /[\u0000-ÿ]/.test(ch) ? FONT_SIZE * 0.58 : FONT_SIZE
  return w
}

function overlaps(a: Box, b: Box) {
  return a.x1 < b.x2 && a.x2 > b.x1 && a.y1 < b.y2 && a.y2 > b.y1
}

export function bubbleRadius(z: number, geo: PlotGeometry) {
  const [z0, z1] = geo.zDomain
  const [a0, a1] = geo.zRange
  const t = z1 === z0 ? 1 : (z - z0) / (z1 - z0)
  // recharts 中 ZAxis range 表示符号面积
  return Math.sqrt((a0 + t * (a1 - a0)) / Math.PI)
}

export function layoutBubbleLabels(
  points: { key: string; label: string; x: number; y: number; z: number }[],
  geo: PlotGeometry
): Map<string, LabelPlacement | null> {
  const result = new Map<string, LabelPlacement | null>()
  if (geo.width <= 0) return result

  const left = geo.margin.left + geo.yAxisWidth
  const right = geo.width - geo.margin.right
  const top = geo.margin.top
  const bottom = geo.height - geo.margin.bottom - geo.xAxisHeight
  const sx = (v: number) =>
    left + ((v - geo.xDomain[0]) / (geo.xDomain[1] - geo.xDomain[0] || 1)) * (right - left)
  const sy = (v: number) =>
    bottom - ((v - geo.yDomain[0]) / (geo.yDomain[1] - geo.yDomain[0] || 1)) * (bottom - top)

  const circles = points.map((p) => ({ ...p, cx: sx(p.x), cy: sy(p.y), r: bubbleRadius(p.z, geo) }))
  // 气泡本身也是障碍物（用外接矩形近似）
  const obstacles: Box[] = circles.map((c) => ({
    x1: c.cx - c.r,
    y1: c.cy - c.r,
    x2: c.cx + c.r,
    y2: c.cy + c.r,
  }))
  const placed: Box[] = []

  const order = [...circles].sort((a, b) => b.z - a.z)
  for (const c of order) {
    const w = textWidth(c.label)
    const h = FONT_SIZE + 2
    const candidates: (LabelPlacement & { box: Box })[] = [
      // 上
      { dx: 0, dy: -c.r - GAP, anchor: "middle", box: { x1: c.cx - w / 2, y1: c.cy - c.r - GAP - h, x2: c.cx + w / 2, y2: c.cy - c.r - GAP } },
      // 下
      { dx: 0, dy: c.r + GAP + h - 2, anchor: "middle", box: { x1: c.cx - w / 2, y1: c.cy + c.r + GAP, x2: c.cx + w / 2, y2: c.cy + c.r + GAP + h } },
      // 右
      { dx: c.r + GAP, dy: h / 2 - 3, anchor: "start", box: { x1: c.cx + c.r + GAP, y1: c.cy - h / 2, x2: c.cx + c.r + GAP + w, y2: c.cy + h / 2 } },
      // 左
      { dx: -c.r - GAP, dy: h / 2 - 3, anchor: "end", box: { x1: c.cx - c.r - GAP - w, y1: c.cy - h / 2, x2: c.cx - c.r - GAP, y2: c.cy + h / 2 } },
    ]
    const selfIndex = circles.indexOf(c)
    const ok = candidates.find(
      (cand) =>
        cand.box.x1 >= left - 4 &&
        cand.box.x2 <= right + 4 &&
        cand.box.y1 >= top - 4 &&
        cand.box.y2 <= bottom + 4 &&
        !placed.some((b) => overlaps(b, cand.box)) &&
        !obstacles.some((b, i) => i !== selfIndex && overlaps(b, cand.box))
    )
    if (ok) {
      placed.push(ok.box)
      result.set(c.key, { dx: ok.dx, dy: ok.dy, anchor: ok.anchor })
    } else {
      result.set(c.key, null)
    }
  }
  return result
}

/** 监听容器宽度 */
export function useElementWidth<T extends HTMLElement>() {
  const ref = React.useRef<T>(null)
  const [width, setWidth] = React.useState(0)
  React.useLayoutEffect(() => {
    const el = ref.current
    if (!el) return
    setWidth(el.getBoundingClientRect().width)
    const ro = new ResizeObserver(([entry]) => setWidth(entry.contentRect.width))
    ro.observe(el)
    return () => ro.disconnect()
  }, [])
  return [ref, width] as const
}

/** recharts LabelList content：按避让结果绘制标签 */
export function makeBubbleLabel({
  placements,
  pointsByIndex,
  hoveredKey,
  showAll,
}: {
  placements: Map<string, LabelPlacement | null>
  pointsByIndex: { key: string; label: string }[]
  hoveredKey: string | null
  showAll: boolean
}) {
  return function BubbleLabel(props: {
    x?: number | string
    y?: number | string
    width?: number | string
    height?: number | string
    index?: number
  }) {
    const point = props.index != null ? pointsByIndex[props.index] : undefined
    if (!point) return null
    const w = Number(props.width ?? 0)
    const cx = Number(props.x ?? 0) + w / 2
    const cy = Number(props.y ?? 0) + Number(props.height ?? 0) / 2
    const r = w / 2
    const hovered = hoveredKey === point.key
    const placement = placements.get(point.key)
    // 悬停 / 显示全部时，放不下的标签默认放在气泡上方
    const fallback: LabelPlacement = { dx: 0, dy: -r - GAP, anchor: "middle" }
    const pos = placement ?? (hovered || showAll ? fallback : null)
    if (!pos) return null
    const dimmed = hoveredKey != null && !hovered
    return (
      <text
        x={cx + pos.dx}
        y={cy + pos.dy}
        textAnchor={pos.anchor}
        className="fill-foreground text-xs"
        style={{
          pointerEvents: "none",
          fontWeight: hovered ? 600 : 400,
          opacity: dimmed ? 0.35 : 1,
          paintOrder: "stroke",
          stroke: "var(--background)",
          strokeWidth: 3,
        }}
      >
        {point.label}
      </text>
    )
  }
}
