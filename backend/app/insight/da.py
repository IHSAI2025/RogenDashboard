"""DA 数据下钻 2.3 – 2.6。"""
from __future__ import annotations

import dataclasses
import datetime as dt
from collections import defaultdict

from .. import config
from ..etl.da_dict import ALL_DAS, UNMAPPED
from ..metrics import engine as E
from ..metrics.engine import Filters, card, div, pct
from ..vendor import dataset as D

DIMS = {"da": lambda a: a.da or UNMAPPED, "region": lambda a: a.region or UNMAPPED, "circle": lambda a: a.circle_lead or UNMAPPED}


def _groups(accts, dim):
    g = defaultdict(list)
    for a in accts:
        g[DIMS[dim](a)].append(a)
    return g


def _group_row(ds, idx, key, dim, subset, f, start, end, pr, cur_b=None, prev_b=None):
    cur = cur_b or E.period_bundle(ds, idx, subset, start, end)
    prv = prev_b or (E.period_bundle(ds, idx, subset, *pr) if pr else None)
    hp = prv is not None
    P = lambda k: prv[k] if hp else None  # noqa: E731
    # 额度/导入仅 DA 维度有意义
    quota_n = opened = opened_p = quota_p = None
    if dim == "da" and key != UNMAPPED:
        q = E.quota_for(ds, [key], f.account_types, at=end)
        quota_n = (q["PLUS"] or 0) + (q["SUPER"] or 0) or None
        opened = sum(1 for a in subset if E.opened(a, end))
        if pr:
            opened_p = sum(1 for a in subset if E.opened(a, pr[1]))
    imp = pct(opened, quota_n) if quota_n else None
    imp_p = pct(opened_p, quota_n) if (quota_n and opened_p is not None) else None
    ar = pct(cur["n_active"], cur["n_valid"])
    sr = pct(cur["n_silent"], cur["n_valid"])
    opa = div(cur["ops_total"], cur["n_active"])
    exp_rate = lambda b, k: pct(b["exp"].get(k, 0), b["gen"].get(D.PPT_GEN if k == D.PPT_EXP else D.TWEET_GEN, 0))  # noqa: E731
    return {
        "key": key,
        "n_accounts": len(subset),
        "quota": quota_n,
        "opened": card(opened, opened_p, has_prev=opened_p is not None) if opened is not None else None,
        "import_rate": {**card(imp, imp_p, "rate", opened, quota_n, imp_p is not None), "warn": imp is not None and imp < config.WARN_IMPORT_RATE} if quota_n else None,
        "valid": card(cur["n_valid"], P("n_valid"), has_prev=hp),
        "active": card(cur["n_active"], P("n_active"), has_prev=hp),
        "active_rate": {**card(ar, pct(prv["n_active"], prv["n_valid"]) if hp else None, "rate", cur["n_active"], cur["n_valid"], hp),
                        "warn": ar is not None and ar < config.WARN_ACTIVE_RATE},
        "dormant": card(cur["n_dormant"], P("n_dormant"), has_prev=hp),
        "silent": card(cur["n_silent"], P("n_silent"), has_prev=hp),
        "silent_rate": {**card(sr, pct(prv["n_silent"], prv["n_valid"]) if hp else None, "rate", cur["n_silent"], cur["n_valid"], hp),
                        "warn": sr is not None and sr > config.WARN_SILENT_RATE},
        "ops": card(cur["ops_total"], P("ops_total"), has_prev=hp),
        "ops_per_active": card(opa, div(prv["ops_total"], prv["n_active"]) if hp else None, num=cur["ops_total"], den=cur["n_active"], has_prev=hp),
        "gen_ppt": card(cur["gen"].get(D.PPT_GEN, 0), prv["gen"].get(D.PPT_GEN, 0) if hp else None, has_prev=hp),
        "gen_tweet": card(cur["gen"].get(D.TWEET_GEN, 0), prv["gen"].get(D.TWEET_GEN, 0) if hp else None, has_prev=hp),
        "gen_poster": card(cur["gen"].get(D.POSTER_GEN, 0), prv["gen"].get(D.POSTER_GEN, 0) if hp else None, has_prev=hp),
        "gen_total": card(cur["gen_total"], P("gen_total"), has_prev=hp),
        "exp_ppt": card(cur["exp"].get(D.PPT_EXP, 0), prv["exp"].get(D.PPT_EXP, 0) if hp else None, has_prev=hp),
        "exp_tweet": card(cur["exp"].get(D.TWEET_EXP, 0), prv["exp"].get(D.TWEET_EXP, 0) if hp else None, has_prev=hp),
        "exp_poster": card(cur["exp"].get(D.POSTER_EXP, 0), prv["exp"].get(D.POSTER_EXP, 0) if hp else None, has_prev=hp),
        "exp_total": card(cur["exp_total"], P("exp_total"), has_prev=hp),
        "export_rate": card(pct(cur["exp_total"], cur["gen_total"]), pct(prv["exp_total"], prv["gen_total"]) if hp else None, "rate",
                            cur["exp_total"], cur["gen_total"], hp),
        "export_rate_ppt": exp_rate(cur, D.PPT_EXP), "export_rate_tweet": exp_rate(cur, D.TWEET_EXP),
        "gen_accounts": cur["n_gen_accts"],
        "gen_conversion": card(pct(cur["n_gen_accts"], cur["n_active"]), pct(prv["n_gen_accts"], prv["n_active"]) if hp else None, "rate",
                               cur["n_gen_accts"], cur["n_active"], hp),
        "gen_per_capita": card(div(cur["gen_total"], cur["n_gen_accts"]), div(prv["gen_total"], prv["n_gen_accts"]) if hp else None,
                               num=cur["gen_total"], den=cur["n_gen_accts"], has_prev=hp),
    }


def _order(keys, dim):
    if dim == "da":
        return [k for k in ALL_DAS if k in keys] + [k for k in keys if k not in ALL_DAS]
    return sorted(keys, key=lambda k: (k == UNMAPPED, k))


def rows(ds, idx, f: Filters, start, end, mode="mom", dim="da", types=None) -> dict:
    """types：None/[] = 全部；['PLUS'] / ['SUPER']。"""
    end_eff = min(end, idx.as_of_day)
    ff = dataclasses.replace(f, account_types=types or f.account_types)
    accts = E.select_accounts(ds, ff)
    pr = E.prev_range(start, end_eff, mode)
    out = []
    for key, subset in _groups(accts, dim).items():
        out.append(_group_row(ds, idx, key, dim, subset, ff, start, end_eff, pr))
    keys = _order([r["key"] for r in out], dim)
    out.sort(key=lambda r: keys.index(r["key"]))
    # 平台参考线
    allb = E.period_bundle(ds, idx, accts, start, end_eff)
    ref = {"active_rate": pct(allb["n_active"], allb["n_valid"]), "ops_per_active": div(allb["ops_total"], allb["n_active"]),
           "silent_warn": config.WARN_SILENT_RATE}
    return {"dim": dim, "rows": out, "reference": ref,
            "period": {"start": start.isoformat(), "end": end_eff.isoformat(), "prev": [pr[0].isoformat(), pr[1].isoformat()] if pr else None},
            "warn": {"import": config.WARN_IMPORT_RATE, "active": config.WARN_ACTIVE_RATE, "silent": config.WARN_SILENT_RATE}}


def trend(ds, idx, f: Filters, start, end, granularity="month", da=None, region=None) -> dict:
    """2.5：单个 DA 或大区的 活跃率 / 沉默率 / 总生成次数 趋势。"""
    end_eff = min(end, idx.as_of_day)
    ff = dataclasses.replace(f, das=[da] if da else f.das, region=region)
    accts = E.select_accounts(ds, ff)
    buckets = []
    if granularity == "week":
        d = start - dt.timedelta(days=start.weekday())
        while d <= end_eff:
            buckets.append((d.strftime("%m/%d"), max(d, start), min(d + dt.timedelta(days=6), end_eff)))
            d += dt.timedelta(days=7)
    else:
        d = E.month_start(start) if (end_eff - start).days >= 31 else max(E.add_months(E.month_start(end_eff), -5), E.month_start(E.LAUNCH))
        while d <= end_eff:
            buckets.append((d.strftime("%Y-%m"), max(d, E.LAUNCH), min(E.month_end(d), end_eff)))
            d = E.add_months(d, 1)
    pts = []
    for label, s, e in buckets:
        b = E.period_bundle(ds, idx, accts, s, e)
        full = (e == E.month_end(s)) if granularity == "month" else ((e - s).days == 6)
        pts.append({"label": label, "active_rate": pct(b["n_active"], b["n_valid"]), "silent_rate": pct(b["n_silent"], b["n_valid"]),
                    "gen_total": b["gen_total"], "complete": full})
    return {"granularity": granularity, "points": pts, "can_week": (end_eff - start).days + 1 <= 90,
            "scope": da or region or "全部所选DA", "n_accounts": len(accts)}
