"""PRD 三·0–5 全部指标口径的唯一实现。overview / da / users / cost 各接口都只调这里，保证数字可互相追溯。

约定：
- 比率统一用百分数(52.6 表示 52.6%)，并总是带分子分母；环比：计数/金额=增长率(%)，比率=百分点差(pp)
- 统计截止日 = min(周期结束日, 数据截至日)；当月未结束时「已过天数」即此口径
- 「使用」= PubMed/大纲/内容库分享 或 成功生成(见 vendor/dataset.is_use)；只登录、失败生成、纯导出都不算使用
- 沉默 = 周期内无使用 且 截至截止日连续 60 天无使用 且 开通满 60 天；休眠 = 周期内无使用且非沉默；有效账号才判定
- 「登录未使用」= 休眠/沉默账号中周期内登录过的账号(标签，不是第四种状态)
"""
from __future__ import annotations

import calendar
import datetime as dt
from collections import defaultdict
from dataclasses import dataclass, field

from .. import config
from ..vendor import dataset as D
from ..vendor.dataset import AccountRec, Dataset

LAUNCH = dt.date.fromisoformat(config.PLATFORM_LAUNCH_DATE)
FN_LABEL = {D.PUBMED: "PubMed检索", D.OUTLINE: "大纲生成", D.PPT_GEN: "PPT", D.TWEET_GEN: "推文",
            D.POSTER_GEN: "海报", D.SHARE: "内容库分享"}


# ───────────── 日期工具 ─────────────
def add_months(d: dt.date, n: int) -> dt.date:
    m = d.month - 1 + n
    y, m = d.year + m // 12, m % 12 + 1
    return dt.date(y, m, min(d.day, calendar.monthrange(y, m)[1]))


def month_end(d: dt.date) -> dt.date:
    return dt.date(d.year, d.month, calendar.monthrange(d.year, d.month)[1])


def month_start(d: dt.date) -> dt.date:
    return d.replace(day=1)


def prev_range(start: dt.date, end: dt.date, mode: str = "mom") -> tuple[dt.date, dt.date] | None:
    """环比对比周期。end 已是统计截止日。数据不完整(对比周期早于上线日)返回 None。"""
    if mode == "mom" and start.day == 1 and start.month == end.month and start.year == end.year:
        ps = add_months(start, -1)
        pe = month_end(ps) if end == month_end(end) else min(ps + (end - start), month_end(ps))
    else:
        n = (end - start).days + 1
        ps, pe = start - dt.timedelta(days=n), start - dt.timedelta(days=1)
    if ps < LAUNCH:
        return None
    return ps, pe


# ───────────── 筛选 ─────────────
@dataclass
class Filters:
    das: list[str] | None = None
    account_types: list[str] | None = None
    source_tag: str | None = None
    identity: str | None = None
    scope: str = "platform"            # platform=全平台(剔测试) / core=核心业务(再剔非DA)
    allowed_das: list[str] | None = None  # 角色裁剪；None=不限(超管)
    region: str | None = None
    circle_lead: str | None = None

    def key(self) -> str:
        return repr((self.das, self.account_types, self.source_tag, self.identity, self.scope, self.allowed_das, self.region, self.circle_lead))


def select_accounts(ds: Dataset, f: Filters) -> list[AccountRec]:
    out = []
    for a in ds.accounts:
        if a.is_test:
            continue
        if f.scope == "core" and not a.is_da:
            continue
        if f.allowed_das is not None and a.da not in f.allowed_das:
            continue
        if f.das is not None and a.da not in f.das:
            continue
        if f.account_types and a.account_type not in f.account_types:
            continue
        if f.source_tag and a.source_tag != f.source_tag:
            continue
        if f.identity and a.identity != f.identity:
            continue
        if f.region and (a.region or "待映射") != f.region:
            continue
        if f.circle_lead and (a.circle_lead or "待映射") != f.circle_lead:
            continue
        out.append(a)
    return out


# ───────────── 事件索引 ─────────────
class Index:
    def __init__(self, ds: Dataset):
        self.by_acc: dict[int, list[D.Event]] = defaultdict(list)
        for e in ds.events:
            self.by_acc[e.account_id].append(e)
        self.cost_by_acc: dict[int, list[D.CostRec]] = defaultdict(list)
        for c in ds.costs:
            self.cost_by_acc[c.account_id].append(c)
        self.as_of_day = ds.as_of.date()


@dataclass
class S:
    """单账号在某周期内的统计。"""
    days: set = field(default_factory=set)
    ops: int = 0
    by_fn: dict = field(default_factory=lambda: defaultdict(int))     # 有效功能操作按 kind
    by_sub: dict = field(default_factory=lambda: defaultdict(int))    # 生成类按子功能
    gen: dict = field(default_factory=lambda: defaultdict(int))       # 成功生成按 kind
    exp: dict = field(default_factory=lambda: defaultdict(int))
    last_gen: dt.date | None = None
    last_use: dt.date | None = None   # 截至 end 的全时段最近使用日(有使用记录)
    window_used: bool = False         # 沉默判定窗口内是否使用过
    logged_in: bool = False           # 周期内是否登录过(本期登录)

    @property
    def gen_total(self):
        return sum(self.gen.values())

    @property
    def exp_total(self):
        return sum(self.exp.values())


def silent_window_start(start: dt.date, end: dt.date) -> dt.date:
    """沉默判定窗口起点：截至截止日连续 60 天(含截止日)，且需覆盖整个统计周期。"""
    return min(start, end - dt.timedelta(days=config.SILENT_DAYS - 1))


def stats(idx: Index, accts: list[AccountRec], start: dt.date, end: dt.date) -> dict[int, S]:
    ws = silent_window_start(start, end)
    res: dict[int, S] = {}
    for a in accts:
        s = S()
        for e in idx.by_acc.get(a.id, ()):
            if e.day > end:
                continue
            if e.kind == D.LOGIN:
                if e.day >= start:
                    s.logged_in = True
                continue
            if D.is_use(e):
                if s.last_use is None or e.day > s.last_use:
                    s.last_use = e.day
                if e.day >= ws:
                    s.window_used = True
                if e.day >= start:
                    s.days.add(e.day)
            if e.day < start:
                continue
            if e.kind in D.EFFECTIVE_KINDS:
                s.ops += e.n
                s.by_fn[e.kind] += e.n
                if e.kind in D.GEN_KINDS:
                    s.by_sub[(e.kind, e.sub)] += e.n
                    if e.ok:
                        s.gen[e.kind] += e.n
                        if s.last_gen is None or e.day > s.last_gen:
                            s.last_gen = e.day
            elif e.kind in D.EXPORT_KINDS:
                s.exp[e.kind] += e.n
        res[a.id] = s
    return res


# ───────────── 账号状态 ─────────────
def opened(a: AccountRec, end: dt.date) -> bool:
    return a.opened_at is not None and a.opened_at <= end


def disabled(a: AccountRec, end: dt.date) -> bool:
    return a.status == "停用" and (a.disabled_at is None or a.disabled_at <= end)


def is_valid(a: AccountRec, end: dt.date) -> bool:
    return opened(a, end) and not disabled(a, end)


def activated(a: AccountRec, end: dt.date) -> bool:
    return opened(a, end) and a.first_login_at is not None and a.first_login_at <= end


def usage_state(a: AccountRec, s: S, end: dt.date) -> str | None:
    """有效账号的使用状态：活跃 / 休眠 / 沉默；非有效账号返回 None。"""
    if not is_valid(a, end):
        return None
    if s.days:
        return "活跃"
    if not s.window_used and (end - a.opened_at).days >= config.SILENT_MIN_OPEN_DAYS:
        return "沉默"
    return "休眠"


# ───────────── 指标包 ─────────────
def rate(num, den):
    return {"value": (num / den * 100.0) if den else None, "num": num, "den": den}


def type_at(a: AccountRec, day: dt.date) -> str | None:
    """账号在某日的类型：有变更记录时取「生效日<=day」的最新一条(月中改档按月末/截止日类型)，否则取当前类型。"""
    if a.type_history:
        cur = None
        for eff, typ in sorted(a.type_history):
            if eff <= day:
                cur = typ
        if cur:
            return cur
    return a.account_type


def quota_for(ds: Dataset, das: list[str] | None, types: list[str] | None, at: dt.date | None = None) -> dict:
    """配置额度(个)：N1(PLUS) / M1(SUPER)。给出 at 且有额度历史时，取「生效日<=at」的最新额度(额度会动态变化)。"""
    out = {"PLUS": None, "SUPER": None}
    if at is not None and ds.quota_history:
        items = []
        for key, hist in ds.quota_history.items():
            vals = [n for eff, n in sorted(hist) if eff <= at]
            if vals:
                items.append((key, vals[-1]))
    else:
        items = list(ds.quotas.items())
    for (da, t), n in items:
        if das is not None and da not in das:
            continue
        if types and t not in types:
            continue
        out[t] = (out[t] or 0) + n
    return out


def period_bundle(ds: Dataset, idx: Index, accts: list[AccountRec], start: dt.date, end: dt.date) -> dict:
    """某周期内的全部「当期」指标原始数。"""
    st = stats(idx, accts, start, end)
    days = max((end - start).days + 1, 1)
    valid = [a for a in accts if is_valid(a, end)]
    state = {a.id: usage_state(a, st[a.id], end) for a in valid}
    active = [a for a in valid if state[a.id] == "活跃"]
    dormant = [a for a in valid if state[a.id] == "休眠"]
    silent = [a for a in valid if state[a.id] == "沉默"]
    valid_ids = {a.id for a in valid}
    # 登录未使用：休眠 / 沉默账号中周期内登录过的
    login_unused_dormant = [a for a in dormant if st[a.id].logged_in]
    login_unused_silent = [a for a in silent if st[a.id].logged_in]

    daily_sum = sum(len(st[a.id].days) for a in valid)  # 每日活跃账号数之和 = 各账号活跃天数之和
    ops_total = sum(st[a.id].ops for a in accts)
    by_fn = defaultdict(int)
    by_sub = defaultdict(int)
    gen = defaultdict(int)
    exp = defaultdict(int)
    gen_accts = defaultdict(set)
    for a in accts:
        s = st[a.id]
        for k, v in s.by_fn.items():
            by_fn[k] += v
        for k, v in s.by_sub.items():
            by_sub[k] += v
        for k, v in s.gen.items():
            gen[k] += v
            gen_accts[k].add(a.id)
        for k, v in s.exp.items():
            exp[k] += v
    gen_acct_all = {i for v in gen_accts.values() for i in v}
    return {
        "days": days, "start": start, "end": end, "stats": st, "state": state,
        "valid": valid, "active": active, "dormant": dormant, "silent": silent,
        "n_valid": len(valid), "n_active": len(active), "n_dormant": len(dormant), "n_silent": len(silent),
        "daily_active_sum": daily_sum,
        "ops_total": ops_total, "by_fn": dict(by_fn), "by_sub": dict(by_sub),
        "gen": dict(gen), "gen_total": sum(gen.values()), "gen_accts": {k: len(v) for k, v in gen_accts.items()},
        "n_gen_accts": len(gen_acct_all),
        "exp": dict(exp), "exp_total": sum(exp.values()),
        "valid_ids": valid_ids,
        "n_login_unused_dormant": len(login_unused_dormant), "n_login_unused_silent": len(login_unused_silent),
        "login_unused_dormant": login_unused_dormant, "login_unused_silent": login_unused_silent,
        "n_exp_accts": len({a.id for a in accts if st[a.id].exp_total > 0}),  # 内容导出账号(三·2)
    }


def stock_bundle(ds: Dataset, idx: Index, accts: list[AccountRec], f: Filters, end: dt.date) -> dict:
    """累计存量：统计范围固定 2026/07/01 ~ end。"""
    op = [a for a in accts if opened(a, end)]
    n2 = sum(1 for a in op if type_at(a, end) == "PLUS")
    m2 = sum(1 for a in op if type_at(a, end) == "SUPER")
    q = quota_for(ds, _quota_das(f), f.account_types, at=end)
    st = stats(idx, accts, LAUNCH, end)
    gen = defaultdict(int)
    exp = defaultdict(int)
    fn = defaultdict(int)
    sub = defaultdict(int)
    for a in accts:
        for k, v in st[a.id].gen.items():
            gen[k] += v
        for k, v in st[a.id].exp.items():
            exp[k] += v
        for k, v in st[a.id].by_fn.items():
            fn[k] += v
        for k, v in st[a.id].by_sub.items():
            sub[k] += v
    return {
        "quota": q, "opened": len(op), "opened_plus": n2, "opened_super": m2,
        "valid": sum(1 for a in op if is_valid(a, end)),
        "activated": sum(1 for a in op if activated(a, end)),
        "fn_total": sum(fn.values()), "by_fn": dict(fn), "by_sub": dict(sub),
        "gen": dict(gen), "gen_total": sum(gen.values()), "exp": dict(exp), "exp_total": sum(exp.values()),
        "accts_opened": op,
    }


def _quota_das(f: Filters) -> list[str] | None:
    das = f.das
    if f.allowed_das is not None:
        das = f.allowed_das if das is None else [d for d in das if d in f.allowed_das]
    return das


# ───────────── 展示用小工具 ─────────────
def mom_count(cur, prev):
    if prev is None or cur is None or prev == 0:
        return None
    return (cur - prev) / prev * 100.0


def mom_rate(cur, prev):
    if prev is None or cur is None:
        return None
    return cur - prev


def card(cur, prev, kind="count", num=None, den=None, has_prev=True):
    """cur/prev 为数值(比率为百分数)。"""
    p = prev if has_prev else None
    mom = mom_rate(cur, p) if kind == "rate" else mom_count(cur, p)
    d = {"value": cur, "prev": p, "mom": mom, "kind": kind}
    if num is not None or den is not None:
        d["num"], d["den"] = num, den
    return d


def pct(num, den):
    return (num / den * 100.0) if den else None


def div(num, den):
    return (num / den) if den else None


def get_ctx(ds: Dataset):
    return Index(ds)
