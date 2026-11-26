import * as React from "react"
import { IconBrandDaysCounter, IconRosetteDiscountCheck } from "@tabler/icons-react"
import { ArrowDownLeftIcon, ArrowUpRightIcon, GoalIcon, ImportIcon, RocketIcon, UserCheckIcon } from "lucide-react"

import { HgFileExport } from "@/components/dashboard/hugeicons"
import {
  CardTitleText,
  DashCard,
  IconBubble,
  SplitBar,
  StatPill,
  TileDelta,
  Trend,
  trendColorClass,
} from "@/components/dashboard/primitives"
import { Badge } from "@/components/ui/badge"
import { Separator } from "@/components/ui/separator"
import { fmtDecimal, fmtInt, fmtPct, fmtSignedPp, momChange, safeRatio } from "@/lib/format"
import { cn } from "@/lib/utils"

import { type CumulativeSnapshot, ppDiff, useCumulativeSnapshots } from "./metrics"
import { Segmented } from "./segmented"

type Scope = "all" | "core"

export function StockSection() {
  const [scope, setScope] = React.useState<Scope>("all")
  const { current: cur, previous: prev } = useCumulativeSnapshots(scope)
  // 额度 / 内容卡片不受「全平台 / 核心业务」切换影响
  const allSnapshots = useCumulativeSnapshots("all")

  return (
    <div className="flex flex-col gap-3 px-6">
      <ScaleTiles cur={cur} prev={prev} scope={scope} onScopeChange={setScope} />
      <div className="grid grid-cols-2 gap-4">
        <QuotaCard cur={allSnapshots.current} prev={allSnapshots.previous} />
        <ContentCard cur={allSnapshots.current} prev={allSnapshots.previous} />
      </div>
    </div>
  )
}

/* ------------------------------------------------------------------ */
/* 账号及产品使用规模                                                    */
/* ------------------------------------------------------------------ */

function ScaleTiles({
  cur,
  prev,
  scope,
  onScopeChange,
}: {
  cur: CumulativeSnapshot
  prev: CumulativeSnapshot
  scope: Scope
  onScopeChange: (scope: Scope) => void
}) {
  const perAccount = safeRatio(cur.featureTotal, cur.activated.total)
  const tiles = [
    {
      label: "累计有效账号数",
      value: fmtInt(cur.valid.total),
      delta: momChange(cur.valid.total, prev.valid.total),
      icon: <IconRosetteDiscountCheck stroke={1.5} />,
      footer: (
        <>
          <StatPill label="Plus" value={fmtInt(cur.valid.plus)} />
          <StatPill label="Super" value={fmtInt(cur.valid.super)} />
        </>
      ),
    },
    {
      label: "累计激活账号数",
      value: fmtInt(cur.activated.total),
      delta: momChange(cur.activated.total, prev.activated.total),
      icon: <UserCheckIcon strokeWidth={1.5} />,
      footer: (
        <>
          <StatPill label="Plus" value={fmtInt(cur.activated.plus)} />
          <StatPill label="Super" value={fmtInt(cur.activated.super)} />
        </>
      ),
    },
    {
      label: "累计导入率",
      value: fmtPct(cur.importRate),
      // 率类指标环比为百分点差（pp）
      delta: ppDiff(cur.importRate, prev.importRate),
      unit: "pp" as const,
      icon: <ImportIcon strokeWidth={1.5} />,
      footer: (
        <>
          <StatPill label="已开通" value={fmtInt(cur.opened.total)} />
          <StatPill label="配置额度" value={fmtInt(cur.quota.total)} />
        </>
      ),
    },
    {
      label: "累计激活率",
      value: fmtPct(cur.activationRate),
      delta: ppDiff(cur.activationRate, prev.activationRate),
      unit: "pp" as const,
      icon: <GoalIcon strokeWidth={1.5} />,
      footer: (
        <>
          <StatPill label="已激活" value={fmtInt(cur.activated.total)} />
          <StatPill label="待激活" value={fmtInt(cur.pendingActivation)} />
        </>
      ),
    },
    {
      label: "累计功能使用次数",
      value: fmtInt(cur.featureTotal),
      primary: true,
      delta: momChange(cur.featureTotal, prev.featureTotal),
      icon: <IconBrandDaysCounter stroke={1.5} />,
      footer: <Badge className="h-[22px]">{`激活账号人均使用 ${fmtDecimal(perAccount)} 次`}</Badge>,
    },
  ]

  return (
    <div className="relative flex flex-wrap items-start gap-6 rounded-xl border bg-card p-6">
      <CardTitleText className="w-full">账号及产品使用规模</CardTitleText>
      <Segmented
        aria-label="统计范围"
        className="absolute top-[17px] right-6"
        value={scope}
        onValueChange={onScopeChange}
        options={[
          { value: "all", label: "全平台" },
          { value: "core", label: "核心业务" },
        ]}
      />
      {tiles.map((tile, i) => (
        <React.Fragment key={tile.label}>
          {i > 0 && <Separator orientation="vertical" className="h-[102px] self-center" />}
          <div className="flex min-w-0 flex-1 flex-col gap-6">
            <div className="flex items-start justify-between">
              <div className="flex flex-col gap-1.5">
                <span className="text-sm leading-5 whitespace-nowrap text-muted-foreground">{tile.label}</span>
                <div className="flex items-center gap-1.5">
                  <span
                    className={cn(
                      "text-xl leading-7 font-semibold whitespace-nowrap",
                      tile.primary ? "text-primary" : "text-[#020617]"
                    )}
                  >
                    {tile.value}
                  </span>
                  {tile.unit === "pp" ? <PpTileDelta value={tile.delta} /> : <TileDelta value={tile.delta} />}
                </div>
              </div>
              <span className="text-muted-foreground [&_svg]:size-6">{tile.icon}</span>
            </div>
            <div className="flex flex-wrap items-center gap-2">{tile.footer}</div>
          </div>
        </React.Fragment>
      ))}
    </div>
  )
}

/** 率类指标的环比（百分点）：样式同 TileDelta，只是单位为 pp */
function PpTileDelta({ value }: { value: number | null | undefined }) {
  if (value == null || !Number.isFinite(value)) {
    return <span className="text-xs text-muted-foreground">—</span>
  }
  const Icon = value >= 0 ? ArrowUpRightIcon : ArrowDownLeftIcon
  return (
    <span className={cn("inline-flex items-center gap-1", trendColorClass(value))}>
      <Icon className="size-5" strokeWidth={2.25} />
      <span className="text-xs leading-4 tracking-[-0.072px]">{fmtSignedPp(value).replace(/^[+-]/, "")}</span>
    </span>
  )
}

/* ------------------------------------------------------------------ */
/* 额度配置与导入                                                        */
/* ------------------------------------------------------------------ */

function ProgressRing({ ratio }: { ratio: number | null }) {
  const r = 58
  const c = 2 * Math.PI * r
  const pct = Math.max(0, Math.min(1, ratio ?? 0))
  const id = React.useId().replace(/:/g, "")
  return (
    <svg width={128} height={128} viewBox="0 0 128 128" className="absolute inset-0 -rotate-90">
      <defs>
        <linearGradient id={`ring-${id}`} x1="1" y1="0" x2="0" y2="1">
          <stop stopColor="#0D42E8" />
          <stop offset="1" stopColor="#2F6DF2" />
        </linearGradient>
      </defs>
      <circle cx={64} cy={64} r={r} fill="none" stroke="#F1F5F9" strokeWidth={8} />
      <circle
        cx={64}
        cy={64}
        r={r}
        fill="none"
        stroke={`url(#ring-${id})`}
        strokeWidth={8}
        strokeLinecap="round"
        strokeDasharray={`${c * pct} ${c}`}
      />
    </svg>
  )
}

function QuotaRow({
  label,
  value,
  delta,
  plus,
  sup,
}: {
  label: string
  value: number
  delta: number | null
  plus: number
  sup: number
}) {
  return (
    <div className="flex flex-col gap-1.5">
      <div className="flex items-center gap-4">
        <span className="text-xs leading-4 whitespace-nowrap text-muted-foreground">{label}</span>
        <span className="text-sm leading-5 font-medium text-[#0f172a]">{fmtInt(value)}</span>
        <Trend value={delta} className="-ml-3" />
      </div>
      <SplitBar
        items={[
          { label: "PLUS", value: plus },
          { label: "Super", value: sup },
        ]}
      />
    </div>
  )
}

function QuotaCard({ cur, prev }: { cur: CumulativeSnapshot; prev: CumulativeSnapshot }) {
  return (
    <DashCard className="px-6">
      <CardTitleText>额度配置与导入</CardTitleText>
      <div className="flex items-center gap-6">
        <div className="relative size-32 shrink-0">
          <ProgressRing ratio={cur.importRate} />
          <div className="absolute inset-0 flex flex-col items-center justify-center gap-1">
            <span className="text-xs leading-4 text-muted-foreground">累计导入率</span>
            <span className="text-xl leading-7 font-semibold">{fmtPct(cur.importRate)}</span>
            <Trend value={ppDiff(cur.importRate, prev.importRate)} unit="pp" tone="strong" className="px-0" />
          </div>
        </div>
        <div className="flex min-w-0 flex-1 flex-col gap-4">
          <QuotaRow
            label="已配置额度"
            value={cur.quota.total}
            // 额度为配置值，无环比
            delta={null}
            plus={cur.quota.plus}
            sup={cur.quota.super}
          />
          <QuotaRow
            label="累计开通账号数"
            value={cur.opened.total}
            delta={momChange(cur.opened.total, prev.opened.total)}
            plus={cur.opened.plus}
            sup={cur.opened.super}
          />
          <QuotaRow
            // PRD：开通即导入，「累计导入账号数」与「累计开通账号数」同值，这里改展示累计有效账号数（开通且可用状态=正常）
            label="累计有效账号数"
            value={cur.valid.total}
            delta={momChange(cur.valid.total, prev.valid.total)}
            plus={cur.valid.plus}
            sup={cur.valid.super}
          />
        </div>
      </div>
    </DashCard>
  )
}

/* ------------------------------------------------------------------ */
/* 内容生成情况                                                          */
/* ------------------------------------------------------------------ */

function ContentCard({ cur, prev }: { cur: CumulativeSnapshot; prev: CumulativeSnapshot }) {
  const rows = [
    {
      label: "累计总生成数",
      icon: <RocketIcon />,
      value: cur.generation.total,
      delta: momChange(cur.generation.total, prev.generation.total),
      ppt: cur.generation.ppt,
      tweet: cur.generation.tweet,
    },
    {
      label: "累计总导出数",
      icon: <HgFileExport size={32} />,
      value: cur.exports.total,
      delta: momChange(cur.exports.total, prev.exports.total),
      ppt: cur.exports.ppt,
      tweet: cur.exports.tweet,
    },
  ]
  return (
    <DashCard>
      <CardTitleText className="px-6">内容生成情况</CardTitleText>
      {rows.map((row) => (
        <div key={row.label} className="flex items-center gap-4 px-6">
          <IconBubble>{row.icon}</IconBubble>
          <div className="flex min-w-0 flex-1 flex-col gap-1.5">
            <div className="flex flex-col gap-1.5">
              <span className="text-sm leading-5 text-muted-foreground">{row.label}</span>
              <div className="flex items-baseline gap-1">
                <span className="text-xl leading-7 font-semibold text-[#020617]">{fmtInt(row.value)}</span>
                <Trend value={row.delta} tone="strong" />
              </div>
            </div>
            <SplitBar
              items={[
                { label: "PPT", value: row.ppt },
                { label: "推文", value: row.tweet },
              ]}
            />
          </div>
        </div>
      ))}
    </DashCard>
  )
}
