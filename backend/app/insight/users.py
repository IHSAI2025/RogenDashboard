"""用户数据下钻 3.x。"""
from __future__ import annotations

import datetime as dt
from collections import defaultdict

from ..etl.da_dict import UNMAPPED
from ..metrics import engine as E
from ..metrics.engine import Filters
from ..vendor import dataset as D


def mask_phone(p: str, full: bool) -> str:
    if full or not p or len(p) < 7:
        return p
    return p[:3] + "****" + p[-4:]


def rows(ds, idx, f: Filters, start, end, state: str | None = None, status: str | None = None, full_phone=True) -> dict:
    end_eff = min(end, idx.as_of_day)
    accts = E.select_accounts(ds, f)
    if status:
        accts = [a for a in accts if (E.disabled(a, end_eff) and status == "停用") or (not E.disabled(a, end_eff) and status == "正常")]
    st = E.stats(idx, accts, start, end_eff)
    out, counts = [], defaultdict(int)
    for a in accts:
        s = st[a.id]
        us = E.usage_state(a, s, end_eff)
        counts[us or "—"] += 1
        if state and state != "all" and us != state:
            continue
        idle = (end_eff - s.last_use).days if s.last_use else None
        out.append({
            "id": a.id, "name": a.name, "phone": mask_phone(a.phone, full_phone), "da": a.da or UNMAPPED, "region": a.region or UNMAPPED,
            "identity": a.identity, "account_type": a.account_type or UNMAPPED, "source_tag": a.source_tag or "—",
            "status": "停用" if E.disabled(a, end_eff) else ("正常" if E.opened(a, end_eff) else "未开通"), "remark": a.remark or "",
            "state": us or "—", "logged_in": s.logged_in, "active_days": len(s.days), "idle_days": idle, "last_use": s.last_use.isoformat() if s.last_use else None,
            "ops_total": s.ops, "pubmed": s.by_fn.get(D.PUBMED, 0), "outline": s.by_fn.get(D.OUTLINE, 0), "share": s.by_fn.get(D.SHARE, 0),
            "ppt_ops": s.by_fn.get(D.PPT_GEN, 0), "tweet_ops": s.by_fn.get(D.TWEET_GEN, 0), "poster_ops": s.by_fn.get(D.POSTER_GEN, 0),
            "gen_ppt": s.gen.get(D.PPT_GEN, 0), "gen_tweet": s.gen.get(D.TWEET_GEN, 0), "gen_poster": s.gen.get(D.POSTER_GEN, 0),
            "gen_total": s.gen_total, "last_gen": s.last_gen.isoformat() if s.last_gen else None,
            "exp_ppt": s.exp.get(D.PPT_EXP, 0), "exp_tweet": s.exp.get(D.TWEET_EXP, 0), "exp_poster": s.exp.get(D.POSTER_EXP, 0),
            "exp_total": s.exp_total,
        })
    return {"rows": out, "counts": dict(counts), "period": {"start": start.isoformat(), "end": end_eff.isoformat()}}


def weekly(ds, idx, account_id: int, end) -> dict:
    """账号详情抽屉：按周 PPT/推文 生成与导出趋势(整个数据区间)。"""
    end_eff = min(end, idx.as_of_day)
    wk: dict[dt.date, dict] = {}
    d = E.LAUNCH - dt.timedelta(days=E.LAUNCH.weekday())
    while d <= end_eff:
        wk[d] = {"label": d.strftime("%m/%d"), "ppt_gen": 0, "tweet_gen": 0, "ppt_export": 0, "tweet_export": 0, "poster_gen": 0, "poster_export": 0}
        d += dt.timedelta(days=7)
    for e in idx.by_acc.get(account_id, ()):
        if e.day > end_eff or e.day < E.LAUNCH:
            continue
        w = e.day - dt.timedelta(days=e.day.weekday())
        if e.kind in D.GEN_KINDS and e.ok or e.kind in D.EXPORT_KINDS:
            wk[w][e.kind] += e.n
    return {"points": list(wk.values())}
