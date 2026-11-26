import { SectionHeader } from "@/components/dashboard/primitives"
import { useDashboard } from "@/context/dashboard"
import { effectiveEnd } from "@/data/dict"
import { fmtDate, fmtPeriod } from "@/lib/format"

import { AiInsightCard } from "./ai-insight-card"
import { AccountDistributionCard, FeatureDistributionCard } from "./distribution-cards"
import { LAUNCH_LABEL } from "./metrics"
import { PeriodSection } from "./period-section"
import { StockSection } from "./stock-section"
import { GenerationTrendCard } from "./trend-widgets"

function SubHeader({ title, extra }: { title: string; extra: string }) {
  return (
    <div className="flex items-center justify-between gap-4 px-6">
      <h3 className="text-sm leading-6 font-medium text-foreground">{title}</h3>
      <span className="text-sm leading-5 whitespace-nowrap text-muted-foreground">{extra}</span>
    </div>
  )
}

export function OverviewTab() {
  const { period } = useDashboard()

  return (
    <div className="flex flex-col gap-6">
      <div className="px-6">
        <AiInsightCard />
      </div>

      {/* 数据大盘 */}
      <section className="flex flex-col gap-4">
        <SectionHeader title="数据大盘" />
        <div className="flex flex-col gap-3">
          <SubHeader
            title="累计存量指标"
            extra={`数据周期：${LAUNCH_LABEL}- ${fmtDate(effectiveEnd(period))}`}
          />
          <StockSection />
        </div>
        <div className="flex flex-col gap-3">
          <SubHeader title="当期数据指标" extra={`数据周期：${fmtPeriod(period)}`} />
          <PeriodSection />
        </div>
      </section>

      {/* 数据看板 */}
      <section className="flex flex-col gap-3">
        <SectionHeader title="数据看板" />
        <div className="px-6">
          <AccountDistributionCard />
        </div>
        <div className="px-6">
          <FeatureDistributionCard />
        </div>
        <div className="grid grid-cols-2 gap-2.5 px-6">
          <GenerationTrendCard metric="total" />
          <GenerationTrendCard metric="perCapita" />
        </div>
      </section>
    </div>
  )
}
