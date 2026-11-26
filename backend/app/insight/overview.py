"""全景看板 1.3 – 1.6。"""
from __future__ import annotations

import datetime as dt
from collections import defaultdict

from .. import config
from ..metrics import engine as E
from ..metrics.engine import Filters, card, div, pct, rate
from ..vendor import dataset as D

SUB_ORDER = {
    D.PPT_GEN: ["文献解读", "学术创作Pro"],
    D.TWEET_GEN: ["医学科普", "专业学术", "指南/政策解读"],
}


def _gen_cards(cur, prev, has_prev, key="gen"):
    names = [("ppt_gen", "PPT"), ("tweet_gen", "推文")] + ([("poster_gen", "海报")] if config.POSTER_LIVE else [])
    out = [{"label": n, **card(cur[key].get(k, 0), prev[key].get(k, 0) if has_prev else None, has_prev=has_prev)} for k, n in names]
    return out


def build(ds, idx, f: Filters, start, end, mode="mom") -> dict:
    end_eff = min(end, idx.as_of_day)
    accts = E.select_accounts(ds, f)
    pr = E.prev_range(start, end_eff, mode)
    cur = E.period_bundle(ds, idx, accts, start, end_eff)
    prv = E.period_bundle(ds, idx, accts, *pr) if pr else None
    hp = prv is not None
    P = lambda k, default=None: (prv[k] if hp else default)  # noqa: E731

    # ── 1.3 累计存量 ──
    sc = E.stock_bundle(ds, idx, accts, f, end_eff)
    sp = E.stock_bundle(ds, idx, accts, f, pr[1]) if pr else None

    def import_rate(b, t=None):
        if t == "PLUS":
            return E.pct(b["opened_plus"], b["quota"]["PLUS"]) if b["quota"]["PLUS"] else None, b["opened_plus"], b["quota"]["PLUS"]
        if t == "SUPER":
            return E.pct(b["opened_super"], b["quota"]["SUPER"]) if b["quota"]["SUPER"] else None, b["opened_super"], b["quota"]["SUPER"]
        q = (b["quota"]["PLUS"] or 0) + (b["quota"]["SUPER"] or 0)
        return (E.pct(b["opened"], q) if q else None), b["opened"], (q or None)

    def imp_card(t=None):
        v, n, d = import_rate(sc, t)
        pv = import_rate(sp, t)[0] if sp else None
        return {"label": {"PLUS": "PLUS账号", "SUPER": "SUPER账号", None: "累计导入率"}[t], **card(v, pv, "rate", n, d, bool(sp)),
                "warn": v is not None and v < config.WARN_IMPORT_RATE}

    q_tot = (sc["quota"]["PLUS"] or 0) + (sc["quota"]["SUPER"] or 0)
    qp_tot = ((sp["quota"]["PLUS"] or 0) + (sp["quota"]["SUPER"] or 0)) if sp else None
    stock = {
        "import_rate": {**imp_card(None), "parts": [imp_card("PLUS"), imp_card("SUPER")]},
        "valid": card(sc["valid"], sp["valid"] if sp else None, has_prev=bool(sp)),
        "activated": card(sc["activated"], sp["activated"] if sp else None, has_prev=bool(sp)),
        "activation_rate": card(pct(sc["activated"], sc["opened"]), pct(sp["activated"], sp["opened"]) if sp else None, "rate",
                                sc["activated"], sc["opened"], bool(sp)),
        "fn_total": {**card(sc["fn_total"], sp["fn_total"] if sp else None, has_prev=bool(sp)),
                     "parts": [{"label": E.FN_LABEL[k], **card(sc["by_fn"].get(k, 0), sp["by_fn"].get(k, 0) if sp else None, has_prev=bool(sp))}
                               for k in (D.PUBMED, D.OUTLINE, D.PPT_GEN, D.TWEET_GEN, D.SHARE) if k != D.POSTER_GEN]},
        "quota": {**card(q_tot or None, qp_tot or None, has_prev=bool(sp)),
                  "parts": [{"label": "PLUS账号", "value": sc["quota"]["PLUS"]}, {"label": "SUPER账号", "value": sc["quota"]["SUPER"]}]},
        "opened": {**card(sc["opened"], sp["opened"] if sp else None, has_prev=bool(sp)),
                   "parts": [{"label": "PLUS账号", "value": sc["opened_plus"]}, {"label": "SUPER账号", "value": sc["opened_super"]}]},
        "gen": {**card(sc["gen_total"], sp["gen_total"] if sp else None, has_prev=bool(sp)), "parts": _gen_cards(sc, sp, bool(sp))},
        "export": {**card(sc["exp_total"], sp["exp_total"] if sp else None, has_prev=bool(sp)),
                   "parts": [{"label": n, **card(sc["exp"].get(k, 0), sp["exp"].get(k, 0) if sp else None, has_prev=bool(sp))}
                             for k, n in (("ppt_export", "PPT"), ("tweet_export", "推文"), ("poster_export", "海报")) if k != "poster_export" or config.POSTER_LIVE]},
    }

    # ── 1.4 当期指标 ──
    def rates(b):
        return {
            "active": pct(b["n_active"], b["n_valid"]), "dormant": pct(b["n_dormant"], b["n_valid"]),
            "silent": pct(b["n_silent"], b["n_valid"]),
            "daily_active": div(b["daily_active_sum"], b["days"]),
            "daily_ops": div(b["ops_total"], b["days"]),
            "ops_per_active": div(b["ops_total"], b["n_active"]),
            "daily_gen": div(b["gen_total"], b["days"]),
            "gen_per_capita": div(b["gen_total"], b["n_gen_accts"]),
        }

    rc, rp = rates(cur), (rates(prv) if hp else {})
    g = lambda k: rp.get(k)  # noqa: E731
    period = {
        "active": {
            "count": card(cur["n_active"], P("n_active"), has_prev=hp),
            "rate": {**card(rc["active"], g("active"), "rate", cur["n_active"], cur["n_valid"], hp), "warn": rc["active"] is not None and rc["active"] < config.WARN_ACTIVE_RATE},
            "daily": card(rc["daily_active"], g("daily_active"), has_prev=hp),
        },
        "idle": {
            "dormant_count": card(cur["n_dormant"], P("n_dormant"), has_prev=hp),
            "dormant_rate": card(rc["dormant"], g("dormant"), "rate", cur["n_dormant"], cur["n_valid"], hp),
            "silent_count": card(cur["n_silent"], P("n_silent"), has_prev=hp),
            "login_unused_dormant": card(cur["n_login_unused_dormant"], P("n_login_unused_dormant"), has_prev=hp),
            "login_unused_silent": card(cur["n_login_unused_silent"], P("n_login_unused_silent"), has_prev=hp),
            "silent_rate": {**card(rc["silent"], g("silent"), "rate", cur["n_silent"], cur["n_valid"], hp), "warn": rc["silent"] is not None and rc["silent"] > config.WARN_SILENT_RATE},
        },
        "efficiency": {
            "ops": card(cur["ops_total"], P("ops_total"), has_prev=hp),
            "daily_ops": card(rc["daily_ops"], g("daily_ops"), has_prev=hp),
            "ops_per_active": card(rc["ops_per_active"], g("ops_per_active"), num=cur["ops_total"], den=cur["n_active"], has_prev=hp),
        },
        "generation": {
            "gen": {**card(cur["gen_total"], P("gen_total"), has_prev=hp), "parts": _gen_cards(cur, prv, hp)},
            "export": {**card(cur["exp_total"], P("exp_total"), has_prev=hp),
                       "parts": [{"label": n, **card(cur["exp"].get(k, 0), prv["exp"].get(k, 0) if hp else None, has_prev=hp)}
                                 for k, n in (("ppt_export", "PPT"), ("tweet_export", "推文"), ("poster_export", "海报")) if k != "poster_export" or config.POSTER_LIVE]},
            "daily_gen": card(rc["daily_gen"], g("daily_gen"), has_prev=hp),
            "gen_per_capita": card(rc["gen_per_capita"], g("gen_per_capita"), num=cur["gen_total"], den=cur["n_gen_accts"], has_prev=hp),
            "gen_conversion": card(pct(cur["n_gen_accts"], cur["n_active"]), pct(prv["n_gen_accts"], prv["n_active"]) if hp else None, "rate",
                                   cur["n_gen_accts"], cur["n_active"], hp),
        },
    }

    # ── 1.5 分布 ──
    op = sc["accts_opened"]
    def donut(keyfn, order):
        c = defaultdict(int)
        for a in op:
            c[keyfn(a)] += 1
        tot = sum(c.values())
        return [{"name": k, "value": c.get(k, 0), "ratio": pct(c.get(k, 0), tot)} for k in order]
    dist = {
        "account_type": donut(lambda a: a.account_type or "待映射", ["PLUS", "SUPER"]),
        "identity": donut(lambda a: a.identity, ["员工", "客户"]),
    }
    mains = [(D.PPT_GEN, "PPT"), (D.TWEET_GEN, "推文")] + ([(D.POSTER_GEN, "海报")] if config.POSTER_LIVE else [])
    main_tot = sum(cur["by_fn"].get(k, 0) for k, _ in mains)
    main_rows = sorted(({"name": n, "value": cur["by_fn"].get(k, 0), "ratio": pct(cur["by_fn"].get(k, 0), main_tot)} for k, n in mains),
                       key=lambda r: -r["value"])
    sub_rows = []
    for k, n in mains:
        group_tot = cur["by_fn"].get(k, 0)
        for s in SUB_ORDER.get(k, []):
            v = cur["by_sub"].get((k, s), 0)
            sub_rows.append({"group": n, "name": s, "value": v, "ratio": pct(v, group_tot)})
    sub_rows.sort(key=lambda r: -r["value"])
    all_tot = sum(r["value"] for r in sub_rows)
    acc, top_n = 0, 0
    for r in sub_rows:
        acc += r["value"]
        top_n += 1
        if all_tot and acc / all_tot >= 0.5:
            break
    dist["function_main"] = main_rows
    dist["function_sub"] = sub_rows
    dist["top50"] = {"n": top_n if all_tot else None, "names": [r["name"] for r in sub_rows[:top_n]] if all_tot else []}

    return {
        "period": {"start": start.isoformat(), "end": end_eff.isoformat(), "days": cur["days"],
                   "prev": [pr[0].isoformat(), pr[1].isoformat()] if pr else None},
        "stock": stock, "current": period, "distribution": dist,
        "n_accounts": len(accts),
    }


def trend(ds, idx, f: Filters, start, end, granularity="month") -> dict:
    """1.6：核心功能生成总次数 / 人均生成次数，两张趋势。month 时若所选周期不足一个月，向前补到最多 6 个月。"""
    end_eff = min(end, idx.as_of_day)
    accts = E.select_accounts(ds, f)
    buckets: list[tuple[str, dt.date, dt.date]] = []
    if granularity == "week":
        d = start - dt.timedelta(days=start.weekday())
        while d <= end_eff:
            buckets.append((d.strftime("%m/%d"), max(d, start), min(d + dt.timedelta(days=6), end_eff)))
            d += dt.timedelta(days=7)
    else:
        first = E.month_start(start)
        if (end_eff - start).days < 31:
            first = max(E.add_months(E.month_start(end_eff), -5), E.month_start(E.LAUNCH))
        d = first
        while d <= end_eff:
            buckets.append((d.strftime("%Y-%m"), max(d, E.LAUNCH), min(E.month_end(d), end_eff)))
            d = E.add_months(d, 1)
    kinds = [("ppt_gen", "PPT"), ("tweet_gen", "推文")] + ([("poster_gen", "海报")] if config.POSTER_LIVE else [])
    pts = []
    for label, s, e in buckets:
        b = E.period_bundle(ds, idx, accts, s, e)
        p = {"label": label, "start": s.isoformat(), "end": e.isoformat()}
        for k, n in kinds:
            p[f"{k}_total"] = b["gen"].get(k, 0)
            p[f"{k}_per"] = div(b["gen"].get(k, 0), b["gen_accts"].get(k, 0))
        pts.append(p)
    return {"granularity": granularity, "series": [{"key": k, "name": n} for k, n in kinds], "points": pts,
            "can_week": (end_eff - start).days + 1 <= 90}
