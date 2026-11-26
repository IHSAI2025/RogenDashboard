import type { Column } from "@/components/dashboard/data-table"
import { daName } from "@/data/dict"
import { META } from "@/data/dict"
import type { UserRow } from "./types"
import { maskPhone } from "@/lib/auth"
import { EMPTY, fmtInt } from "@/lib/format"

import { EnabledBadge, SourceBadge, UsageStatusBadge } from "@/components/dashboard/account-badges"

type Row = UserRow

const STATUS_ORDER = { 活跃: 0, 休眠: 1, 沉默: 2, "—": 3 } as const

function num(
  key: string,
  header: string,
  group: string,
  get: (row: Row) => number | null
): Column<Row> {
  return {
    key,
    header,
    group,
    align: "right",
    sortValue: get,
    cell: (row) => (get(row) === null ? EMPTY : fmtInt(get(row))),
  }
}

function date(
  key: string,
  header: string,
  group: string,
  get: (row: Row) => string | null
): Column<Row> {
  return {
    key,
    header,
    group,
    sortValue: get,
    cell: (row) => get(row)?.replaceAll("-", "/") ?? EMPTY,
  }
}

export function buildColumns(onOpen: (row: Row) => void): Column<Row>[] {
  const link = (row: Row, text: string) => (
    <button
      type="button"
      data-open-sheet="user"
      onClick={(e) => {
        e.stopPropagation()
        onOpen(row)
      }}
      className="font-medium text-primary hover:underline"
    >
      {text}
    </button>
  )

  const base = "账号基本信息"
  const usage = "使用状态"
  const feature = "功能使用情况"
  const gen = "内容生成情况"
  const exp = "内容导出情况"

  const cols: Column<Row>[] = [
    {
      key: "id",
      header: "账号ID",
      group: base,
      sticky: true,
      sortValue: (r) => String(r.id),
      cell: (r) => link(r, String(r.id)),
    },
    {
      key: "name",
      header: "姓名",
      group: base,
      sortValue: (r) => r.name,
      cell: (r) => link(r, r.name),
    },
    {
      key: "phone",
      header: "联系电话",
      group: base,
      sortValue: (r) => r.phone,
      cell: (r) => maskPhone(r.phone),
    },
    {
      key: "da",
      header: "所属DA",
      group: base,
      sortValue: (r) => daName(r.da === "待映射" ? null : r.da),
      cell: (r) =>
        r.da !== "待映射" ? (
          daName(r.da)
        ) : (
          <span className="text-muted-foreground">{daName(null)}</span>
        ),
    },
    {
      key: "region",
      header: "大区",
      group: base,
      sortValue: (r) => r.region,
      cell: (r) => r.region,
    },
    {
      key: "identity",
      header: "用户身份",
      group: base,
      sortValue: (r) => r.identity,
      cell: (r) => r.identity,
    },
    {
      key: "type",
      header: "账号类型",
      group: base,
      sortValue: (r) => r.account_type,
      cell: (r) =>
        r.account_type !== "待映射" ? r.account_type : <span className="text-muted-foreground">待映射</span>,
    },
    {
      key: "source",
      header: "账号来源标签",
      group: base,
      sortValue: (r) => r.source_tag,
      cell: (r) =>
        r.source_tag === "采购" || r.source_tag === "免费" ? (
          <SourceBadge source={r.source_tag} />
        ) : (
          <span className="text-muted-foreground">{EMPTY}</span>
        ),
    },
    {
      key: "enabled",
      header: "可用状态",
      group: base,
      sortValue: (r) => (r.enabled ? 1 : 0),
      cell: (r) => <EnabledBadge enabled={r.enabled} />,
    },
    {
      key: "remark",
      header: "备注",
      group: base,
      sortValue: (r) => r.remark || null,
      className: "whitespace-normal",
      cell: (r) =>
        r.remark ? (
          <span title={r.remark} className="line-clamp-2 w-40 text-sm leading-5">
            {r.remark}
          </span>
        ) : (
          <span className="text-muted-foreground">{EMPTY}</span>
        ),
    },
    {
      key: "status",
      header: "使用状态",
      group: usage,
      sortValue: (r) => STATUS_ORDER[r.state],
      cell: (r) =>
        r.state === "—" ? <span className="text-muted-foreground">{EMPTY}</span> : <UsageStatusBadge status={r.state} />,
    },
    {
      key: "loggedIn",
      header: "本期登录",
      group: usage,
      sortValue: (r) => (r.logged_in ? 1 : 0),
      cell: (r) =>
        r.state === "休眠" || r.state === "沉默" ? (
          r.logged_in ? <span className="font-medium text-amber-600" title="登录未使用，优先唤醒">是</span> : <span>否</span>
        ) : r.logged_in ? (
          <span>是</span>
        ) : (
          <span>否</span>
        ),
    },
    num("activeDays", "活跃天数", usage, (r) => r.active_days),
    num("inactiveDays", "连续未使用天数", usage, (r) => r.idle_days),
    date("lastUsed", "最近使用日期", usage, (r) => r.last_use),
    num("usageTotal", "功能使用总次数", usage, (r) => r.ops_total),

    num("pubmed", "PubMed检索次数", feature, (r) => r.pubmed),
    num("outline", "大纲生成次数", feature, (r) => r.outline),
    num("share", "内容库分享次数", feature, (r) => r.share),
    num("fPpt", "PPT功能使用次数", feature, (r) => r.ppt_ops),
    num("fTweet", "推文功能使用次数", feature, (r) => r.tweet_ops),
    num("fPoster", "海报功能使用次数", feature, (r) => r.poster_ops),
    num("featureTotal", "功能使用总次数", feature, (r) => r.ops_total),

    num("gPpt", "PPT生成次数", gen, (r) => r.gen_ppt),
    num("gTweet", "推文生成次数", gen, (r) => r.gen_tweet),
    num("gPoster", "海报生成次数", gen, (r) => r.gen_poster),
    num("gTotal", "总生成次数", gen, (r) => r.gen_total),
    date("gLast", "最近成功生成日期", gen, (r) => r.last_gen),

    num("ePpt", "PPT导出次数", exp, (r) => r.exp_ppt),
    num("eTweet", "推文导出次数", exp, (r) => r.exp_tweet),
    num("ePoster", "海报导出次数", exp, (r) => r.exp_poster),
    num("eTotal", "总导出次数", exp, (r) => r.exp_total),
  ]
  // 海报上线前不显示海报相关数据
  const posterKeys = new Set(["fPoster", "gPoster", "ePoster"])
  return META.poster_live ? cols : cols.filter((c) => !posterKeys.has(c.key))
}
