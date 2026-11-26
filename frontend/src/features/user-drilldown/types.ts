import type { UsageStatus } from "@/data/types"

/** /api/vm/users/list 的一行（字段由后端 insight/users.py 按 PRD 3.2 计算，前端只展示，不再自行判定使用状态） */
export interface UserRow {
  id: number
  name: string
  phone: string
  /** DA 编码；无法映射为「待映射」 */
  da: string
  region: string
  identity: "客户" | "员工"
  account_type: string
  source_tag: string
  /** 统计截止日可用状态 */
  enabled: boolean
  status: string
  remark: string
  /** 活跃 / 休眠 / 沉默；停用账号不判定，为「—」 */
  state: UsageStatus | "—"
  /** 本期(统计周期内)是否登录过；休眠/沉默账号中为 true 即「登录未使用」，优先唤醒 */
  logged_in: boolean
  active_days: number
  period_days: number
  idle_days: number | null
  last_use: string | null
  ops_total: number
  pubmed: number
  outline: number
  share: number
  ppt_ops: number
  tweet_ops: number
  poster_ops: number
  gen_ppt: number
  gen_tweet: number
  gen_poster: number
  gen_total: number
  last_gen: string | null
  exp_ppt: number
  exp_tweet: number
  exp_poster: number
  exp_total: number
}

export interface UserListResponse {
  rows: UserRow[]
  counts: Record<"all" | UsageStatus, number>
  /** 休眠 / 沉默账号中「登录未使用」的数量 */
  loginUnusedCounts: { 休眠: number; 沉默: number }
  period: { start: string; end: string; days: number }
}

export interface WeekPoint {
  start: string
  end: string
  gen_ppt: number
  gen_tweet: number
  gen_poster: number
  exp_ppt: number
  exp_tweet: number
  exp_poster: number
}
