import alertCircleUrl from "@/assets/figma/hg-alert-circle.svg"
import chartLineDataUrl from "@/assets/figma/hg-chart-line-data-02.svg"
import fileExport16Url from "@/assets/figma/hg-file-export-16.svg"
import fileExport32Url from "@/assets/figma/hg-file-export-32.svg"
import zzzUrl from "@/assets/figma/hg-zzz.svg"

/*
 * 设计稿中的 hugeicons 图标（lucide / tabler 中没有完全一致的图形），
 * 按 Figma 中的图标框尺寸与内边距还原。
 */

export function HgChartLineData02() {
  // 24px 框，图形 20×20 偏移 (1, 2)
  return (
    <span className="relative inline-block size-6 shrink-0">
      <img src={chartLineDataUrl} alt="" width={20} height={20} className="absolute top-0.5 left-px" />
    </span>
  )
}

export function HgAlertCircle() {
  // 16px 框，图形 14.67×14.67 偏移 0.67
  return (
    <span className="relative inline-block size-4 shrink-0">
      <img
        src={alertCircleUrl}
        alt=""
        width={14.6667}
        height={14.6667}
        className="absolute top-[0.67px] left-[0.67px]"
      />
    </span>
  )
}

export function HgZzz() {
  // 32px 框，图形 24×24 偏移 4
  return (
    <span className="relative inline-block size-8 shrink-0">
      <img src={zzzUrl} alt="" width={24.0001} height={24} className="absolute top-1 left-1" />
    </span>
  )
}

export function HgFileExport({ size = 16 }: { size?: 16 | 32 }) {
  return (
    <img
      src={size === 16 ? fileExport16Url : fileExport32Url}
      alt=""
      width={size}
      height={size}
      className="shrink-0"
    />
  )
}
