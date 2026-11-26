export type AccountType = "PLUS" | "SUPER"
export type AccountSource = "采购" | "免费"
export type Identity = "客户" | "员工"
export type UsageStatus = "活跃" | "休眠" | "沉默"
export type Role = "super_admin" | "da_admin" | "other"

export interface DaNode {
  id: string
  name: string
  /** 叶子节点才有 code，代表一个真实可筛选的 DA */
  children?: DaNode[]
}

export interface DaInfo {
  id: string
  name: string
  groupId: string
  groupName: string
  /** 额度配置 */
  quota: { PLUS: number; SUPER: number }
}

export interface Account {
  id: string
  name: string
  phone: string
  /** null = 无法映射 DA（待映射） */
  daId: string | null
  region: string
  identity: Identity
  /** null = 缺少账号类型（月度预算显示「待映射」） */
  accountType: AccountType | null
  source: AccountSource
  enabled: boolean
  /** 停用日期（可用状态为停用时） */
  disabledAt: string | null
  remark: string
  /** 导入日期 YYYY-MM-DD */
  importedAt: string
  /** 首次激活日期，null = 待激活 */
  activatedAt: string | null
  /** 使用画像（mock 用） */
  profile: "active" | "dormant" | "silent"
  intensity: number
}

export interface Period {
  /** 'month' 来自月份 toggle；'custom' 来自自定义周期 */
  kind: "month" | "custom"
  start: Date
  end: Date
}

export interface FeatureUsage {
  pubmed: number
  outline: number
  libraryShare: number
  ppt: number
  tweet: number
  poster: number
  total: number
}

export interface GenerationStats {
  ppt: number
  tweet: number
  poster: number
  total: number
  lastSuccessDate: string | null
}

export interface ExportStats {
  ppt: number
  tweet: number
  poster: number
  total: number
}

export interface AccountPeriodStats {
  status: UsageStatus
  activeDays: number
  periodDays: number
  inactiveDays: number
  lastUsedDate: string | null
  features: FeatureUsage
  generation: GenerationStats
  exports: ExportStats
}

export interface GlobalFilters {
  /** 选中的 DA 叶子 id；空数组 = 全部 DA */
  daIds: string[]
  accountType: AccountType | "all"
  source: AccountSource | "all"
  identity: Identity | "all"
}
