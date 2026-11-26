"""费用看板 5.x。金额口径见 PRD 三·5。"""
from __future__ import annotations

import dataclasses
import datetime as dt
from collections import defaultdict

from .. import config
from ..etl.da_dict import ALL_DAS, UNMAPPED
from ..metrics import engine as E
from ..metrics.engine import Filters, card, mom_count, mom_rate, div, pct

BUDGET = config.BUDGET_PER_MONTH


def month_bounds(month: str, as_of: dt.date):
    y, m = map(int, month.split("-"))
    ms = dt.date(y, m, 1)
    me = E.month_end(ms)
    return ms, me, min(me, as_of)


def in_force(a, ms, me) -> bool:
    """统计月份内任一天处于生效状态：开通日 <= 月末，且停用日(若有) >= 月初。"""
    return a.opened_at is not None and a.opened_at <= me and not (E.disabled(a, me) and a.disabled_at is not None and a.disabled_at < ms) \
        and not (a.status == "停用" and a.disabled_at is None)


def _cost_in(idx, a, s, e):
    return sum(c.amount for c in idx.cost_by_acc.get(a.id, ()) if s <= c.day <= e)


def _calc(ds, idx, accts, ms, me, end_eff, ytd_start):
    """给定账号集合与月份，返回逐账号明细及合计。"""
    act = [a for a in accts if in_force(a, ms, me)]
    rows = []
    for a in act:
        cost = _cost_in(idx, a, ms, end_eff)
        ytd = _cost_in(idx, a, ytd_start, end_eff)
        t_end = E.type_at(a, me)
        budget = BUDGET.get(t_end) if t_end else None
        last = max((e.day for e in idx.by_acc.get(a.id, ()) if e.day <= end_eff), default=None)
        rows.append({"a": a, "cost": round(cost, 2), "ytd": round(ytd, 2), "budget": budget, "last_use": last})
    return rows


def _sum(rows, key="cost"):
    return round(sum(r[key] for r in rows), 2)


def _split(rows):
    buy = _sum([r for r in rows if r["a"].source_tag == "采购"])
    free = _sum([r for r in rows if r["a"].source_tag == "免费"])
    other = round(_sum(rows) - buy - free, 2)  # 来源标签缺失
    return buy, free, other


def build(ds, idx, f: Filters, month: str, level="da", full_phone=True) -> dict:
    ms, me, end_eff = month_bounds(month, idx.as_of_day)
    accts = E.select_accounts(ds, f)
    ytd_start = max(dt.date(ms.year, 1, 1), E.LAUNCH)
    cur = _calc(ds, idx, accts, ms, me, end_eff, ytd_start)

    # 环比：上个自然月；当月未结束 → 花费类对比上月同期，预算对比上月整月
    pms = E.add_months(ms, -1)
    pme = E.month_end(pms)
    has_prev = pms >= E.LAUNCH
    pend = pme if end_eff == me else min(pms + (end_eff - ms), pme)
    prv = _calc(ds, idx, accts, pms, pme, pend, ytd_start) if has_prev else []

    cost, cost_p = _sum(cur), (_sum(prv) if has_prev else None)
    budget = sum(r["budget"] or 0 for r in cur)
    budget_p = sum(r["budget"] or 0 for r in prv) if has_prev else None
    buy, free, other = _split(cur)
    n_plus = sum(1 for r in cur if E.type_at(r["a"], me) == "PLUS")
    n_super = sum(1 for r in cur if E.type_at(r["a"], me) == "SUPER")
    use = pct(cost, budget)
    use_p = pct(cost_p, budget_p) if has_prev else None
    overview = {
        "cost": {**card(cost, cost_p, has_prev=has_prev), "purchase": buy, "free": free, "unlabeled": other},
        "budget": {**card(budget, budget_p, has_prev=has_prev), "n_plus": n_plus, "n_super": n_super,
                   "unmapped": sum(1 for r in cur if r["budget"] is None)},
        "usage": card(use, use_p, "rate", cost, budget, has_prev),
        "ytd": {"value": _sum(cur, "ytd"), "purchase": _split_ytd(cur, "采购"), "free": _split_ytd(cur, "免费")},
        "as_of": ds.as_of.strftime("%Y-%m-%d %H:%M"), "fx_version": ds.fx_version,
    }

    # 5.3 排行：超管按 DA、DA 管理员按大区
    key = (lambda a: a.da or UNMAPPED) if level == "da" else (lambda a: a.region or UNMAPPED)
    groups, groups_p = defaultdict(list), defaultdict(list)
    for r in cur:
        groups[key(r["a"])].append(r)
    for r in prv:
        groups_p[key(r["a"])].append(r)
    rank = []
    for k, rs in groups.items():
        c = _sum(rs)
        cp = _sum(groups_p[k]) if has_prev and k in groups_p else None
        b = sum(r["budget"] or 0 for r in rs)
        paying = sum(1 for r in rs if r["cost"] > 0)
        bu, fr, ot = _split(rs)
        rank.append({"key": k, "n_accounts": len(rs), "budget": b, "cost": c, "purchase": bu, "free": fr,
                     "usage": pct(c, b), "usage_num": c, "usage_den": b, "per_capita": div(c, paying), "paying": paying,
                     "mom": mom_count(c, cp) if has_prev else None})
    rank.sort(key=lambda r: -r["cost"])

    detail = []
    for r in sorted(cur, key=lambda r: -r["cost"]):
        a = r["a"]
        detail.append({
            "id": a.id, "name": a.name, "phone": _mask(a.phone, full_phone), "da": a.da or UNMAPPED, "region": a.region or UNMAPPED,
            "identity": a.identity, "account_type": E.type_at(a, me) or UNMAPPED, "source_tag": a.source_tag or "—",
            "status": "停用" if E.disabled(a, me) else "正常", "budget": r["budget"], "cost": r["cost"],
            "usage": pct(r["cost"], r["budget"]) if r["budget"] else None, "ytd": r["ytd"],
            "last_use": r["last_use"].isoformat() if r["last_use"] else None,
        })
    return {"month": month, "partial": end_eff < me, "end": end_eff.isoformat(), "level": level,
            "overview": overview, "rank": rank, "detail": detail,
            "totals": {"rank_sum": round(sum(r["cost"] for r in rank), 2), "detail_sum": round(sum(d["cost"] for d in detail), 2)}}


def _split_ytd(rows, tag):
    return round(sum(r["ytd"] for r in rows if r["a"].source_tag == tag), 2)


def _mask(p, full):
    from .users import mask_phone
    return mask_phone(p, full)


def daily(ds, idx, f: Filters, month: str) -> dict:
    """5.6 本月每日费用趋势：柱(采购/免费堆叠) + 累计折线 + 本月预算参考线。"""
    ms, me, end_eff = month_bounds(month, idx.as_of_day)
    accts = E.select_accounts(ds, f)
    act = {a.id: a for a in accts if in_force(a, ms, me)}
    budget = sum(BUDGET.get(E.type_at(a, me), 0) for a in act.values() if E.type_at(a, me))
    per = defaultdict(lambda: [0.0, 0.0, 0.0])
    for aid, a in act.items():
        for c in idx.cost_by_acc.get(aid, ()):
            if ms <= c.day <= end_eff:
                i = 0 if a.source_tag == "采购" else 1 if a.source_tag == "免费" else 2
                per[c.day][i] += c.amount
    pts, cum, d = [], 0.0, ms
    while d <= me:
        if d <= end_eff:
            b, fr, ot = per[d]
            cum += b + fr + ot
            pts.append({"day": d.day, "purchase": round(b, 2), "free": round(fr + ot, 2), "cum": round(cum, 2),
                        "cum_ratio": pct(cum, budget)})
        else:
            pts.append({"day": d.day, "purchase": None, "free": None, "cum": None, "cum_ratio": None})
        d += dt.timedelta(days=1)
    return {"points": pts, "budget": budget}


def account_detail(ds, idx, account_id: int, month: str) -> dict:
    """5.7 近 12 个月逐月花费；平台上线前月份为 None；本月按功能拆分(token 按次回传前仅 PPT/推文可拆，其余归其他)。"""
    a = next((x for x in ds.accounts if x.id == account_id), None)
    if a is None:
        return {}
    ms, me, end_eff = month_bounds(month, idx.as_of_day)
    months = []
    for i in range(11, -1, -1):
        s = E.add_months(ms, -i)
        e = E.month_end(s)
        months.append({"month": s.strftime("%Y-%m"), "cost": None if e < E.LAUNCH else round(_cost_in(idx, a, s, min(e, end_eff)), 2)})
    fn = defaultdict(float)
    for c in idx.cost_by_acc.get(a.id, ()):
        if ms <= c.day <= end_eff:
            fn[c.fn] += c.amount
    total = sum(fn.values())
    parts = [{"name": n, "value": round(fn.get(k, 0), 2), "ratio": pct(fn.get(k, 0), total)}
             for k, n in (("ppt", "PPT"), ("tweet", "推文"), ("poster", "海报"), ("other", "其他"))]
    return {"id": a.id, "name": a.name, "account_type": E.type_at(a, me), "budget": BUDGET.get(E.type_at(a, me)) if E.type_at(a, me) else None,
            "months": months, "by_function": parts, "by_function_note": "按次回传 token 前，功能拆分为估算口径"}
