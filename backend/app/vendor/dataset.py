"""数据契约：指标引擎(metrics/engine.py)只依赖这里的 Dataset，不关心数据从哪来。

- 本地：vendor/local_adapter.py 由三份上传文件 + mock 补齐生成
- 商汤接口就绪后：写一个 vendor_adapter 返回同样的 Dataset 即可(字段说明见 docs/vendor-api-contract.md)
"""
from __future__ import annotations

import datetime as dt
from dataclasses import dataclass, field

# 事件类型
LOGIN = "login"
PUBMED = "pubmed"
OUTLINE = "outline"
SHARE = "share"
PPT_GEN, TWEET_GEN, POSTER_GEN = "ppt_gen", "tweet_gen", "poster_gen"
PPT_EXP, TWEET_EXP, POSTER_EXP = "ppt_export", "tweet_export", "poster_export"

GEN_KINDS = (PPT_GEN, TWEET_GEN, POSTER_GEN)
EXPORT_KINDS = (PPT_EXP, TWEET_EXP, POSTER_EXP)
# 三·0「有效功能操作」：无论成功失败取消都计入
EFFECTIVE_KINDS = (PUBMED, OUTLINE, PPT_GEN, TWEET_GEN, POSTER_GEN, SHARE)
# 「使用」(PRD v0.1 最新版三·0)：有使用记录 = PubMed 检索 / 大纲生成 / 内容库分享，或「成功」生成 PPT/推文/海报。
# 只登录不算使用；失败/取消的生成、纯导出也不算使用(但失败/取消的生成仍计入「有效功能操作」次数)。
USE_PLAIN_KINDS = (PUBMED, OUTLINE, SHARE)


def is_use(e: "Event") -> bool:
    return e.kind in USE_PLAIN_KINDS or (e.kind in GEN_KINDS and e.ok)


@dataclass
class AccountRec:
    id: int
    name: str
    phone: str
    da: str | None                  # DA 代码；None = 待映射
    region: str | None              # 大区
    circle_lead: str | None         # 圈长/负责同事
    identity: str                   # 客户 / 员工
    account_type: str | None        # PLUS / SUPER / None(待映射)
    source_tag: str | None          # 采购 / 免费
    status: str                     # 正常 / 停用
    opened_at: dt.date | None
    disabled_at: dt.date | None
    first_login_at: dt.date | None
    is_test: bool = False
    is_da: bool = True              # 非 DA 账号=False
    remark: str | None = None
    # 账号类型变更记录 [(生效日, PLUS|SUPER)]；月中改档的月度预算取「月末」类型(PRD 三·5)。为空则一直是 account_type
    type_history: list = field(default_factory=list)


@dataclass
class Event:
    account_id: int
    day: dt.date
    kind: str
    n: int = 1                      # 次数
    ok: bool = True                 # 仅生成类：成功=True，失败/取消=False
    sub: str | None = None          # 子功能(文献解读/学术创作Pro/医学科普/专业学术/指南政策解读)


@dataclass
class CostRec:
    account_id: int
    day: dt.date
    amount: float                   # 元
    fn: str = "other"               # ppt / tweet / poster / other


@dataclass
class Dataset:
    accounts: list[AccountRec]
    events: list[Event]
    costs: list[CostRec]
    quotas: dict[tuple[str, str], int]  # (da, PLUS|SUPER) -> 个数(最新)
    as_of: dt.datetime                  # 数据截至时间
    fx_version: str = "report-cny-v0"   # token↔人民币换算版本
    mock_fields: list[str] = field(default_factory=list)  # 由 mock 补齐的字段，前端提示「含模拟数据」
    # 额度历史 {(da, type): [(生效日, 个数)]}，按生效日升序；额度会动态变化(活动激励)，统计时取「生效日<=统计截止日」的最新一条
    quota_history: dict = field(default_factory=dict)
