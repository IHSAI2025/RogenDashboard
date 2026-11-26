import type * as React from "react"
import { AppSidebar } from "@/components/app-sidebar"
import { DashboardHeader } from "@/components/dashboard-header"
import { SidebarInset, SidebarProvider } from "@/components/ui/sidebar"
import { Tabs, TabsContent } from "@/components/ui/tabs"
import { type DashboardTab, useDashboard } from "@/context/dashboard"
import { CostTab } from "@/features/cost"
import { DaDrilldownTab } from "@/features/da-drilldown"
import { OverviewTab } from "@/features/overview"
import { UserDrilldownTab } from "@/features/user-drilldown"
import { CURRENT_USER, canSeeCostTab } from "@/lib/auth"

export default function App() {
  const { tab, setTab } = useDashboard()

  return (
    <SidebarProvider style={{ "--sidebar-width": "15rem" } as React.CSSProperties}>
      <AppSidebar />
      <SidebarInset className="min-w-0">
        <Tabs
          value={tab}
          onValueChange={(v) => setTab(v as DashboardTab)}
          className="gap-0"
        >
          <DashboardHeader />
          <TabsContent value="overview" className="pt-6 pb-10">
            <OverviewTab />
          </TabsContent>
          <TabsContent value="da" className="pt-6 pb-10">
            <DaDrilldownTab />
          </TabsContent>
          <TabsContent value="users" className="pt-6 pb-10">
            <UserDrilldownTab />
          </TabsContent>
          {canSeeCostTab(CURRENT_USER) && (
            <TabsContent value="cost" className="pt-6 pb-10">
              <CostTab />
            </TabsContent>
          )}
        </Tabs>
      </SidebarInset>
    </SidebarProvider>
  )
}
