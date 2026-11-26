"""用户数据下钻 view-model：在 insight/users.py(PRD 3.2 全部字段)之上补设计稿需要的筛选(大区/搜索/可用状态)、
周期内生效过滤，以及按「近 12 个滚动 7 日」的账号详情趋势。指标口径全部来自 metrics/engine.py。"""
from __future__ import annotations

import dataclasses
import datetime as dt

from ..metrics import engine as E
from ..vendor import dataset as D
from . import users as U

WEEKS = 12


def effective_in_period(a, start: dt.date, end: dt.date) -> bool:
    """周期内生效过：开通日 <= 周期末，且未在周期开始前停用。"""
    if a.opened_at is None or a.opened_at > end:
        return False
    if a.status == "停用" and (a.disabled_at is None or a.disabled_at < start):
        return False
    return True


def build(ctx, state: str = "all", enabled: str | None = None, region: str | None = None, q: str | None = None,
          login_unused: bool = False) -> dict:
    """返回 rows(已按 state Tab 过滤) 与 counts(搜索/大区/可用状态作用后、不含 state Tab 过滤)。"""
    f = dataclasses.replace(ctx.f, region=region) if region else ctx.f
    res = U.rows(ctx.ds, ctx.idx, f, ctx.start, ctx.end, "all", None, ctx.scope.is_super)
    acc = {a.id: a for a in ctx.ds.accounts}
    kw = (q or "").strip().lower()
    days = (ctx.end - ctx.start).days + 1
    out = []
    for r in res["rows"]:
        a = acc[r["id"]]
        if not effective_in_period(a, ctx.start, ctx.end):
            continue
        r["enabled"] = not E.disabled(a, ctx.end)
        if enabled == "正常" and not r["enabled"]:
            continue
        if enabled == "停用" and r["enabled"]:
            continue
        if kw and kw not in r["name"].lower() and kw not in str(r["id"]):
            continue
        r["period_days"] = max(days, 0)
        r["disabled_at"] = a.disabled_at.isoformat() if a.disabled_at else None
        r["opened_at"] = a.opened_at.isoformat() if a.opened_at else None
        r["first_login_at"] = a.first_login_at.isoformat() if a.first_login_at else None
        out.append(r)
    counts = {"all": len(out), "活跃": 0, "休眠": 0, "沉默": 0}
    for r in out:
        if r["state"] in counts:
            counts[r["state"]] += 1
    # 登录未使用：休眠 / 沉默账号中本期登录过的(标签，不是第四种状态)；各 Tab 的数量一并给出供前端展示
    lu = {"休眠": 0, "沉默": 0}
    for r in out:
        if r["state"] in lu and r["logged_in"]:
            lu[r["state"]] += 1
    rows = out if state in (None, "all") else [r for r in out if r["state"] == state]
    if login_unused:
        rows = [r for r in rows if r["state"] in ("休眠", "沉默") and r["logged_in"]]
    return {"rows": rows, "counts": counts, "loginUnusedCounts": lu, "period": {"start": ctx.start.isoformat(), "end": ctx.end.isoformat(), "days": max(days, 0)}}


def weekly(ds, idx, account_id: int, end: dt.date) -> dict:
    """近 12 个滚动 7 日（以统计截止日为末日向前），成功生成与导出次数。"""
    end = min(end, idx.as_of_day)
    evs = idx.by_acc.get(account_id, ())
    pts = []
    for i in range(WEEKS - 1, -1, -1):
        w_end = end - dt.timedelta(days=7 * i)
        w_start = w_end - dt.timedelta(days=6)
        p = {"start": w_start.isoformat(), "end": w_end.isoformat(), "gen_ppt": 0, "gen_tweet": 0, "gen_poster": 0,
             "exp_ppt": 0, "exp_tweet": 0, "exp_poster": 0}
        if w_end >= E.LAUNCH:
            for e in evs:
                if w_start <= e.day <= w_end:
                    if e.kind in D.GEN_KINDS and e.ok:
                        p["gen_" + e.kind.split("_")[0]] += e.n
                    elif e.kind in D.EXPORT_KINDS:
                        p["exp_" + e.kind.split("_")[0]] += e.n
        pts.append(p)
    return {"points": pts, "end": end.isoformat()}
