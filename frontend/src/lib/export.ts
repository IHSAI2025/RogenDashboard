import * as XLSX from "xlsx"

export type ExportFormat = "xlsx" | "csv"

export interface ExportSheet {
  name: string
  /** 表头前的说明行，例如统计周期、筛选条件、数据截至时间、口径版本 */
  meta?: [string, string][]
  columns: { key: string; header: string }[]
  rows: Record<string, unknown>[]
}

function sheetToAoa(sheet: ExportSheet) {
  const aoa: unknown[][] = []
  if (sheet.meta?.length) {
    for (const [k, v] of sheet.meta) aoa.push([k, v])
    aoa.push([])
  }
  aoa.push(sheet.columns.map((c) => c.header))
  for (const row of sheet.rows) {
    aoa.push(sheet.columns.map((c) => row[c.key] ?? ""))
  }
  return aoa
}

function downloadBlob(blob: Blob, filename: string) {
  const url = URL.createObjectURL(blob)
  const a = document.createElement("a")
  a.href = url
  a.download = filename
  document.body.appendChild(a)
  a.click()
  a.remove()
  setTimeout(() => URL.revokeObjectURL(url), 1000)
}

/**
 * 导出数据。XLSX：每个 sheet 一个工作表；CSV：每个 sheet 一个文件。
 * 前端 demo 直接生成文件；接入后端后应改为请求后端导出接口（由后端校验数据权限）。
 */
export function exportSheets(
  sheets: ExportSheet[],
  baseName: string,
  formatType: ExportFormat
) {
  if (formatType === "xlsx") {
    const wb = XLSX.utils.book_new()
    for (const sheet of sheets) {
      const ws = XLSX.utils.aoa_to_sheet(sheetToAoa(sheet))
      XLSX.utils.book_append_sheet(wb, ws, sheet.name.slice(0, 31))
    }
    XLSX.writeFile(wb, `${baseName}.xlsx`)
    return
  }
  sheets.forEach((sheet, i) => {
    const ws = XLSX.utils.aoa_to_sheet(sheetToAoa(sheet))
    const csv = XLSX.utils.sheet_to_csv(ws)
    // BOM 保证 Excel 打开中文不乱码
    const blob = new Blob(["﻿" + csv], { type: "text/csv;charset=utf-8" })
    const suffix = sheets.length > 1 ? `-${sheet.name}` : ""
    setTimeout(() => downloadBlob(blob, `${baseName}${suffix}.csv`), i * 300)
  })
}
