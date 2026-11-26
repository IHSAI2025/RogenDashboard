# 神笔小罗 · 使用数据看板

React 19 + Vite + Tailwind CSS v4 + shadcn/ui（radix-nova 风格）实现的管理后台数据看板，按 Figma「管理后台」设计稿还原。

## 运行

```bash
npm install
npm run dev      # http://localhost:5173
npm run build    # 类型检查 + 生产构建
```

## 页面

| Tab | 说明 | 设计稿 |
| --- | --- | --- |
| 全景看板 | AI 诊断及洞察、数据大盘（累计存量 / 当期指标）、数据看板（账号分布、功能使用分布、趋势） | node 170:6026 |
| DA 数据下钻 | 三大率综合看板、健康雷达（运营 / 功能使用气泡图、周/月趋势）、多指标明细一览表 | node 196:10266 |
| 用户数据下钻 | 用户状态 Tab（全部 / 活跃 / 休眠 / 沉默）、用户明细表、账号详情抽屉、XLSX/CSV 导出 | node 1:1805（需求以 PRD 为准） |
| 费用看板 | 费用总览、本月每日费用趋势、DA 费用排行、个人费用明细、账号费用详情、导出 | 无设计稿，沿用现有设计语言 |

顶部全局筛选（所属 DA 树形多选 / 账号类型 / 账号来源 / 用户身份 + 月份 toggle / 自定义周期）作用于所有 Tab；
切换到「费用看板」时，月份 toggle 替换为「统计月份 YYYY-MM」选择器。

## 目录

```
src/
  components/
    ui/                 shadcn 组件
    filters/            全局筛选（DA 树形多选、单选下拉、周期 toggle、月份选择器）
    dashboard/          看板通用积木（卡片、环比、图例、分段条、数据表格、导出菜单、hugeicons）
    app-sidebar.tsx     侧边栏
    dashboard-header.tsx 标题 + 筛选 + Tab
  context/dashboard.tsx 全局筛选 / 周期 / Tab 状态与跨 Tab 跳转
  data/
    mock.ts             确定性 mock 数据（DA、账号、周期使用指标、每日花费）
    selectors.ts        筛选与聚合工具
  features/             各 Tab 的实现
  lib/
    auth.ts             当前账号与权限（demo 固定为超级管理员）、手机号脱敏
    export.ts           XLSX / CSV 导出
    format.ts           数字、金额、百分比、环比格式化
```

## 数据与权限

- 所有数据均为前端 mock（`src/data/mock.ts`），按账号 ID + 统计周期确定性生成，刷新不变；接入后端时替换该层即可。
- 当前账号固定为超级管理员（`src/lib/auth.ts`）。DA 管理员 / 其他角色的分支逻辑（费用 Tab 可见性、DA 选项范围、按大区排行、手机号脱敏）已预留，
  但数据范围最终必须由后端按角色校验。
- 「导出报告」按钮调用浏览器打印（可另存为 PDF）；各表格的「下载 / 导出」生成 XLSX 或 CSV。
