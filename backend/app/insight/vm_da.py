"""DA 下钻 view-model：输出与前端 features/da-drilldown/data.ts 的 GroupMetrics / GroupRow / TrendPoint 同形(camelCase，比率为 0~1)。
口径全部来自 metrics/engine.py(period_bundle / usage_state / quota_for)，这里只做分组与字段整形。"""
from __future__ import annotations

import dataclasses
import datetime as dt

from ..etl.da_dict import ALL_DAS
from ..metrics import engine as E
from ..vendor import dataset as D

UNMAPPED_KEY = "__unmapped__"
UNMAPPED = "待映射"
DIMS = ("da", "region", "leader")


def group_key(a, dim: str) -> str:
    if dim == "da":
        return a.da or UNMAPPED_KEY
    if dim == "region":
        return a.region or UNMAPPED
    return a.circle_lead or UNMAPPED


def apply_focus(accts, focus_dim: str | None, focus_key: str | None):
    if not focus_dim or focus_key is None:
        return accts
    return [a for a in accts if group_key(a, focus_dim) == focus_key]


def _r(num, den):
    return (num / den) if den else None


def _typed(num, den):
    return {"numerator": num, "denominator": den, "rate": _r(num, den)}


def metrics(ds, idx, subset, start, end, key, dim, f) -> dict:
    b = E.period_bundle(ds, idx, subset, start, end)
    types = ("PLUS", "SUPER")
    cnt = lambda lst, t: sum(1 for a in lst if a.account_type == t)  # noqa: E731
    opened_l = [a for a in subset if E.opened(a, end)]
    quota = qt = None
    if dim == "da" and key != UNMAPPED_KEY:
        q = E.quota_for(ds, [key], f.account_types, at=end)
        qt = {t: (q[t] or 0) for t in types}
        quota = (qt["PLUS"] + qt["SUPER"]) or None
        if quota is None:
            qt = None
    gen, exp = b["gen"], b["exp"]
    return {
        "key": key,
        "quota": quota,
        "quotaByType": qt,
        "opened": len(opened_l),
        "importRate": _r(len(opened_l), quota) if quota else None,
        "importRateByType": {t: (_r(cnt(opened_l, t), qt[t]) if qt and qt[t] else None) for t in types},
        "effective": b["n_valid"], "active": b["n_active"], "dormant": b["n_dormant"], "silent": b["n_silent"],
        "activeRate": _typed(b["n_active"], b["n_valid"]),
        "silentRate": _typed(b["n_silent"], b["n_valid"]),
        "activeRateByType": {t: _r(cnt(b["active"], t), cnt(b["valid"], t)) for t in types},
        "silentRateByType": {t: _r(cnt(b["silent"], t), cnt(b["valid"], t)) for t in types},
        "featureTotal": b["ops_total"],
        "perActiveUsage": _r(b["ops_total"], b["n_active"]),
        "genAccounts": b["n_gen_accts"],
        "genConversion": _r(b["n_gen_accts"], b["n_active"]),
        "perCapitaGen": _r(b["gen_total"], b["n_gen_accts"]),
        "gen": {"ppt": gen.get(D.PPT_GEN, 0), "tweet": gen.get(D.TWEET_GEN, 0), "poster": gen.get(D.POSTER_GEN, 0), "total": b["gen_total"]},
        "exp": {"ppt": exp.get(D.PPT_EXP, 0), "tweet": exp.get(D.TWEET_EXP, 0), "poster": exp.get(D.POSTER_EXP, 0), "total": b["exp_total"]},
        "exportRate": _r(b["exp_total"], b["gen_total"]),
    }


def _order(keys, dim):
    if dim == "da":
        rank = {d: i for i, d in enumerate(ALL_DAS)}
        return sorted(keys, key=lambda k: (k == UNMAPPED_KEY, rank.get(k, 999)))
    return sorted(keys, key=lambda k: (k == UNMAPPED, k))


def groups(ctx, dim: str, focus_dim=None, focus_key=None, include_unmapped=False) -> dict:
    ds, idx, f = ctx.ds, ctx.idx, ctx.f
    accts = apply_focus(E.select_accounts(ds, f), focus_dim, focus_key)
    bucket: dict[str, list] = {}
    for a in accts:
        bucket.setdefault(group_key(a, dim), []).append(a)
    if not include_unmapped:
        bucket.pop(UNMAPPED_KEY, None)
    rows = []
    for key in _order(list(bucket), dim):
        sub = bucket[key]
        cur = metrics(ds, idx, sub, ctx.start, ctx.end, key, dim, f)
        if cur["effective"] == 0 and cur["opened"] == 0:
            continue
        cur["prev"] = metrics(ds, idx, sub, *ctx.prev, key, dim, f) if ctx.prev else None
        rows.append(cur)
    # 全平台参考线：不受页面筛选影响，但仍受角色范围约束
    pf = dataclasses.replace(f, das=None, account_types=None, source_tag=None, identity=None, region=None, circle_lead=None)
    pb = E.period_bundle(ds, idx, E.select_accounts(ds, pf), ctx.start, ctx.end)
    return {
        "dim": dim, "rows": rows,
        "platform": {"activeRate": _typed(pb["n_active"], pb["n_valid"]), "perActiveUsage": _r(pb["ops_total"], pb["n_active"])},
        "period": {"start": ctx.start.isoformat(), "end": ctx.end.isoformat(), "prev": [d.isoformat() for d in ctx.prev] if ctx.prev else None},
        "asOf": ds.as_of.strftime("%Y-%m-%d %H:%M"),
    }


def _buckets(gran: str, as_of: dt.date):
    out = []
    if gran == "month":
        d = E.month_start(E.LAUNCH)
        while d <= as_of:
            out.append((d.strftime("%y年%-m月"), d, E.month_end(d)))
            d = E.add_months(d, 1)
    elif gran == "week":
        first = as_of - dt.timedelta(weeks=25)
        first -= dt.timedelta(days=first.weekday())
        d = max(first, E.LAUNCH - dt.timedelta(days=E.LAUNCH.weekday()))
        while d <= as_of:
            out.append((f"{d.month}/{d.day}", d, d + dt.timedelta(days=6)))
            d += dt.timedelta(days=7)
    else:
        y = E.LAUNCH.year
        while dt.date(y, 1, 1) <= as_of:
            out.append((f"{y}年", max(dt.date(y, 1, 1), E.LAUNCH), dt.date(y, 12, 31)))
            y += 1
    return out


def trend(ctx, granularity: str, focus_dim=None, focus_key=None) -> dict:
    ds, idx = ctx.ds, ctx.idx
    accts = apply_focus(E.select_accounts(ds, ctx.f), focus_dim, focus_key)
    pts = []
    for label, s, e in _buckets(granularity, idx.as_of_day):
        s2, e2 = max(s, E.LAUNCH), min(e, idx.as_of_day)
        b = E.period_bundle(ds, idx, accts, s2, e2)
        pts.append({"label": label, "rangeLabel": f"{s2:%Y/%m/%d} - {e2:%Y/%m/%d}",
                    "activeRate": _r(b["n_active"], b["n_valid"]), "silentRate": _r(b["n_silent"], b["n_valid"]), "genTotal": b["gen_total"]})
    return {"granularity": granularity, "points": pts}
