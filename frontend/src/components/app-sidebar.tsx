import {
  IconChartBarPopular,
  IconDashboard,
  IconListDetails,
} from "@tabler/icons-react"
import { ChevronsUpDownIcon, CircleHelpIcon, SearchIcon, SettingsIcon } from "lucide-react"

import avatarUrl from "@/assets/figma/avatar.png"
import {
  Sidebar,
  SidebarContent,
  SidebarFooter,
  SidebarGroup,
  SidebarGroupLabel,
  SidebarHeader,
  SidebarMenu,
  SidebarMenuButton,
  SidebarMenuItem,
  SidebarRail,
} from "@/components/ui/sidebar"
import { CURRENT_USER, switchRole } from "@/lib/auth"
import type { Role } from "@/data/types"

const commonNav = [
  { title: "Settings", icon: SettingsIcon },
  { title: "Get Help", icon: CircleHelpIcon },
  { title: "Search", icon: SearchIcon },
]

// 占位菜单，仅用于示意「小罗智多星」分组结构，当前无实际页面
const xiaoluoNav = [
  { title: "占位菜单一", icon: IconListDetails },
  { title: "占位菜单二", icon: IconChartBarPopular },
]

const shenbiNav = [{ title: "数据看板", icon: IconDashboard, active: true }]

export function AppSidebar() {
  return (
    <Sidebar variant="inset" collapsible="offcanvas">
      <SidebarHeader>
        <div className="flex items-center gap-2 rounded-md p-1.5">
          <div className="size-[30px] shrink-0 rounded-[4px] bg-primary" />
          <span className="flex-1 truncate text-base font-medium">小罗家族</span>
        </div>
      </SidebarHeader>
      <SidebarContent>
        <SidebarGroup>
          <SidebarGroupLabel>公用菜单</SidebarGroupLabel>
          <SidebarMenu>
            {commonNav.map((item) => (
              <SidebarMenuItem key={item.title}>
                <SidebarMenuButton tooltip={item.title}>
                  <item.icon />
                  <span>{item.title}</span>
                </SidebarMenuButton>
              </SidebarMenuItem>
            ))}
          </SidebarMenu>
        </SidebarGroup>
        <SidebarGroup>
          <SidebarGroupLabel>小罗智多星</SidebarGroupLabel>
          <SidebarMenu>
            {xiaoluoNav.map((item) => (
              <SidebarMenuItem key={item.title}>
                <SidebarMenuButton tooltip={item.title}>
                  <item.icon />
                  <span>{item.title}</span>
                </SidebarMenuButton>
              </SidebarMenuItem>
            ))}
          </SidebarMenu>
        </SidebarGroup>
        <SidebarGroup>
          <SidebarGroupLabel>神笔小罗</SidebarGroupLabel>
          <SidebarMenu>
            {shenbiNav.map((item) => (
              <SidebarMenuItem key={item.title}>
                <SidebarMenuButton
                  isActive={item.active}
                  tooltip={item.title}
                  className="data-[active=true]:font-normal"
                >
                  <item.icon />
                  <span>{item.title}</span>
                </SidebarMenuButton>
              </SidebarMenuItem>
            ))}
          </SidebarMenu>
        </SidebarGroup>
      </SidebarContent>
      <SidebarFooter>
        <SidebarMenu>
          <SidebarMenuItem>
            {/* 本地联调身份切换：生产环境由网关注入 X-Role / X-Managed-DAs，此处不展示 */}
            <label className="flex items-center gap-1 px-2 text-xs text-muted-foreground group-data-[collapsible=icon]:hidden">
              身份(联调)
              <select
                className="min-w-0 flex-1 rounded border bg-background px-1 py-0.5"
                value={CURRENT_USER.role}
                onChange={(e) => switchRole(e.target.value as Role, CURRENT_USER.authorizedDaIds[0] || "BC")}
              >
                <option value="super_admin">超级管理员</option>
                <option value="da_admin">DA 管理员</option>
                <option value="other">其他角色</option>
              </select>
            </label>
          </SidebarMenuItem>
          <SidebarMenuItem>
            <SidebarMenuButton size="lg">
              <img
                src={avatarUrl}
                alt=""
                className="size-8 shrink-0 rounded-lg object-cover"
              />
              <div className="grid flex-1 text-left leading-tight">
                <span className="truncate text-sm font-medium">{CURRENT_USER.name}</span>
                <span className="truncate text-xs">{CURRENT_USER.email}</span>
              </div>
              <ChevronsUpDownIcon className="ml-auto size-4" />
            </SidebarMenuButton>
          </SidebarMenuItem>
        </SidebarMenu>
      </SidebarFooter>
      {/* 收起后（offcanvas）侧边栏完全移出屏幕；这条边缘拖拽条始终存在，
          保证收起后还能点击重新展开。展开/收起按钮统一由顶部 header 的
          SidebarTrigger 承担，这里不再重复放置，避免展开态出现两个按钮 */}
      <SidebarRail />
    </Sidebar>
  )
}
