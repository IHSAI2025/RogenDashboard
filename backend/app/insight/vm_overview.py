"""设计稿「全景看板」的 view-model 构造。口径全部来自 metrics/engine.py，这里只做形状转换。
比率输出 0~1 小数；分母为 0 / 无可比周期输出 None。字段名为前端 camelCase（与 features/overview/metrics.ts 的类型同形）。
"""
from __future__ import annotations

import dataclasses
import datetime as dt

from .. import config
from ..etl.da_dict import ALL_DAS, UNMAPPED
from ..metrics import engine as E
from ..vendor import dataset as D
from . import da as DA
from . import overview as OV

DA_NAMES = {
    "BC": "乳腺癌 BC", "LC": "肺癌 LC", "GI": "肝癌 GI", "HEMA": "血液肿瘤 HEMA", "OPH": "眼科 OPH", "NS&RD": "神经科学 NS&RD",
    "INF": "流感 INF", "IMMU": "肾病免疫 IMMU", "NMA": "全国准入 NMA", "HSA": "大客户 HSA", "MCE": "多渠道 MCE",
}


def r(num, den):
    return (num / den) if den else None


def _split(accts):
    return {"total": len(accts), "plus": sum(1 for a in accts if a.account_type == "PLUS"),
            "super": sum(1 for a in accts if a.account_type == "SUPER")}


def cumulative(ds, idx, f, end, view: str) -> dict:
    """累计存量(2026/07/01 ~ end)。view=core 时在全平台基础上再剔除非 DA 账号，额度也只算 DA 额度。"""
    ff = dataclasses.replace(f, scope="core" if view == "core" else "platform")
    if view == "core":
        ff = dataclasses.replace(ff, das=(f.das if f.das is not None else list(ALL_DAS)))
    accts = E.select_accounts(ds, ff)
    b = E.stock_bundle(ds, idx, accts, ff, end)
    op = b["accts_opened"]
    valid = [a for a in op if E.is_valid(a, end)]
    act = [a for a in op if E.activated(a, end)]
    q = b["quota"]
    qp, qs = q["PLUS"] or 0, q["SUPER"] or 0
    return {
        "valid": _split(valid), "activated": _split(act), "opened": _split(op),
        "quota": {"total": qp + qs, "plus": qp, "super": qs},
        # 累计导入率 = 累计开通账号(含后来停用) ÷ 配置额度（PRD 三·4）
        "importRate": r(len(op), qp + qs),
        "activationRate": r(len(act), len(op)),
        "pendingActivation": len(op) - len(act),
        "featureTotal": b["fn_total"],
        "generation": {"total": b["gen_total"], "ppt": b["gen"].get(D.PPT_GEN, 0), "tweet": b["gen"].get(D.TWEET_GEN, 0)},
        "exports": {"total": b["exp_total"], "ppt": b["exp"].get(D.PPT_EXP, 0), "tweet": b["exp"].get(D.TWEET_EXP, 0)},
    }


def period_snapshot(b: dict) -> dict:
    fn = b["by_fn"]
    days = b["days"]
    return {
        "valid": b["n_valid"], "active": b["n_active"], "dormant": b["n_dormant"], "silent": b["n_silent"],
        "activeRate": r(b["n_active"], b["n_valid"]), "dormantRate": r(b["n_dormant"], b["n_valid"]),
        "silentRate": r(b["n_silent"], b["n_valid"]),
        # 登录未使用：休眠/沉默账号中周期内登录过的(PRD 1.4)
        "loginUnusedDormant": b["n_login_unused_dormant"], "loginUnusedSilent": b["n_login_unused_silent"],
        "dailyActive": r(b["daily_active_sum"], days),
        "featureTotal": b["ops_total"], "dailyFeature": r(b["ops_total"], days),
        "perActiveFeature": r(b["ops_total"], b["n_active"]),
        "generation": {"total": b["gen_total"], "ppt": b["gen"].get(D.PPT_GEN, 0), "tweet": b["gen"].get(D.TWEET_GEN, 0)},
        "exports": {"total": b["exp_total"], "ppt": b["exp"].get(D.PPT_EXP, 0), "tweet": b["exp"].get(D.TWEET_EXP, 0)},
        "dailyGeneration": r(b["gen_total"], days), "perCapitaGeneration": r(b["gen_total"], b["n_gen_accts"]),
        "features": {"pubmed": fn.get(D.PUBMED, 0), "outline": fn.get(D.OUTLINE, 0), "libraryShare": fn.get(D.SHARE, 0),
                     "ppt": fn.get(D.PPT_GEN, 0), "tweet": fn.get(D.TWEET_GEN, 0), "poster": fn.get(D.POSTER_GEN, 0)},
    }


def distribution(ds, idx, f, end) -> dict:
    """1.5：按统计截止日的累计开通账号分布 + 功能使用分布(周期内)。"""
    accts = E.select_accounts(ds, f)
    op = [a for a in accts if E.opened(a, end)]
    return {
        "types": {"plus": sum(1 for a in op if a.account_type == "PLUS"), "super": sum(1 for a in op if a.account_type == "SUPER"),
                  "unmapped": sum(1 for a in op if a.account_type is None)},
        "identities": {"customer": sum(1 for a in op if a.identity == "客户"), "staff": sum(1 for a in op if a.identity == "员工")},
    }


def functions(cur_bundle: dict) -> dict:
    """功能使用分布：图①主模块(PPT/推文/海报)；图②子模块按主模块分组，组内占比；TopN 在全部子模块里累计占比首次 >= 50%。"""
    fn, sub = cur_bundle["by_fn"], cur_bundle["by_sub"]
    mains = [(D.PPT_GEN, "PPT"), (D.TWEET_GEN, "推文")] + ([(D.POSTER_GEN, "海报")] if config.POSTER_LIVE else [])
    tot = sum(fn.get(k, 0) for k, _ in mains)
    core = sorted(({"label": n, "value": fn.get(k, 0), "ratio": r(fn.get(k, 0), tot)} for k, n in mains), key=lambda x: -x["value"])
    subs = []
    for k, n in mains:
        gt = fn.get(k, 0)
        for s in OV.SUB_ORDER.get(k, []):
            v = sub.get((k, s), 0)
            subs.append({"label": s, "group": n, "value": v, "ratio": r(v, gt)})
    subs.sort(key=lambda x: -x["value"])
    all_tot = sum(x["value"] for x in subs)
    acc = n = 0
    for x in subs:
        acc += x["value"]
        n += 1
        if all_tot and acc / all_tot >= 0.5:
            break
    return {"core": core, "subs": subs, "topN": n if all_tot else 0, "topShare": r(acc, all_tot) if all_tot else None}


def snapshots(ctx) -> dict:
    ds, idx, f = ctx.ds, ctx.idx, ctx.f
    accts = E.select_accounts(ds, f)
    cur = E.period_bundle(ds, idx, accts, ctx.start, ctx.end)
    prv = E.period_bundle(ds, idx, accts, *ctx.prev) if ctx.prev else None
    cum = {}
    for view in ("all", "core"):
        cum[view] = {
            "asOf": ctx.end.isoformat(),
            "current": cumulative(ds, idx, f, ctx.end, view),
            "previous": cumulative(ds, idx, f, ctx.prev[1], view) if ctx.prev else None,
        }
    return {
        "cumulative": cum,
        "period": {"current": period_snapshot(cur), "previous": period_snapshot(prv) if prv else None},
        "distribution": distribution(ds, idx, f, ctx.end),
        "functions": functions(cur),
        "range": {"start": ctx.start.isoformat(), "end": ctx.end.isoformat(),
                  "prev": [ctx.prev[0].isoformat(), ctx.prev[1].isoformat()] if ctx.prev else None},
    }


def _buckets(granularity: str, end: dt.date):
    out = []
    if granularity == "week":
        d = E.LAUNCH - dt.timedelta(days=E.LAUNCH.weekday())
        while d <= end:
            out.append((d, min(d + dt.timedelta(days=6), end)))
            d += dt.timedelta(days=7)
    elif granularity == "year":
        d = dt.date(E.LAUNCH.year, 1, 1)
        while d <= end:
            out.append((d, min(dt.date(d.year, 12, 31), end)))
            d = dt.date(d.year + 1, 1, 1)
    else:
        d = E.month_start(E.LAUNCH)
        while d <= end:
            out.append((d, min(E.month_end(d), end)))
            d = E.add_months(d, 1)
    return out


def trend(ctx, granularity: str) -> dict:
    """1.6：自平台上线起各周期成功生成次数 / 人均生成次数（受 DA/类型/来源/身份筛选，不受统计周期限制；前端 Brush 选可视窗口）。"""
    accts = E.select_accounts(ctx.ds, ctx.f)
    rows = []
    for s, e in _buckets(granularity, ctx.idx.as_of_day):
        b = E.period_bundle(ctx.ds, ctx.idx, accts, max(s, E.LAUNCH), e)
        row = {"start": s.isoformat(), "end": e.isoformat(), "total": {}, "perCapita": {}}
        for k, name in ((D.PPT_GEN, "ppt"), (D.TWEET_GEN, "tweet"), (D.POSTER_GEN, "poster")):
            row["total"][name] = b["gen"].get(k, 0)
            row["perCapita"][name] = r(b["gen"].get(k, 0), b["gen_accts"].get(k, 0))
        rows.append(row)
    return {"granularity": granularity, "rows": rows}


# ───────────── AI 洞察（设计稿四段，规则化事实陈述）─────────────
def _pct(v, d=1):
    return "—" if v is None else f"{v * 100:.{d}f}%"


def _spct(v, d=1):
    return "—" if v is None else f"{'+' if v > 0 else ''}{v * 100:.{d}f}%"


def _spp(cur, prev):
    if cur is None or prev is None:
        return "—"
    d = (cur - prev) * 100
    return f"{'+' if d > 0 else ''}{d:.1f}pp"


def _int(v):
    return "—" if v is None else f"{round(v):,}"


def _mom(cur, prev):
    return None if cur is None or prev is None or prev == 0 else (cur - prev) / prev


FEATURE_LABEL = {"pubmed": "PubMed 检索", "outline": "大纲生成", "libraryShare": "内容库分享", "ppt": "PPT", "tweet": "推文", "poster": "海报"}


def insight_sections(ctx, scope: str) -> list[dict]:
    ds, idx = ctx.ds, ctx.idx
    snap = snapshots(ctx)
    cur = snap["period"]["current"]
    prev = snap["period"]["previous"] or {}
    by_region = (ctx.f.das is not None and len(ctx.f.das) == 1) or not ctx.scope.is_super
    dim = "region" if by_region else "da"
    dim_label = "大区" if by_region else "DA"
    rows = DA.rows(ds, idx, ctx.f, ctx.start, ctx.end, ctx.mode, dim)["rows"]
    rows = [x for x in rows if x["valid"]["value"] >= 5 and not (dim == "da" and x["key"] == UNMAPPED)]
    name = (lambda k: DA_NAMES.get(k, k)) if dim == "da" else (lambda k: k)
    ar = lambda x: (x["active_rate"]["value"] or 0) / 100  # noqa: E731
    sr = lambda x: (x["silent_rate"]["value"] or 0) / 100  # noqa: E731
    label = f"{ctx.start.month}月" if ctx.mode == "mom" else "所选周期内"

    feat_mom = _mom(cur["featureTotal"], prev.get("featureTotal"))
    daily_mom = _mom(cur["dailyFeature"], prev.get("dailyFeature"))
    per_mom = _mom(cur["perActiveFeature"], prev.get("perActiveFeature"))
    act_mom = _mom(cur["active"], prev.get("active"))

    if scope == "da" and len(rows) >= 2:
        srt = sorted(rows, key=ar, reverse=True)
        top, bot = srt[0], srt[-1]
        gap = (ar(top) - ar(bot)) * 100
        conclusion = [
            {"text": f"{label}各{dim_label}活跃率分化明显：最高为「{name(top['key'])}」"}, {"text": _pct(ar(top)), "bold": True},
            {"text": f"，最低为「{name(bot['key'])}」"}, {"text": _pct(ar(bot)), "bold": True},
            {"text": f"，相差 {gap:.1f}pp；整体活跃率 {_pct(cur['activeRate'])}（环比{_spp(cur['activeRate'], prev.get('activeRate'))}），表明"},
            {"text": f"{dim_label}间运营水平差距较大，需针对低活跃{dim_label}专项提升" if gap > 20 else f"各{dim_label}整体使用水平较为均衡", "highlight": True},
            {"text": "。"},
        ]
    else:
        both_up = (daily_mom or 0) > 0 and (per_mom or 0) > 0
        both_down = (daily_mom or 0) < 0 and (per_mom or 0) < 0
        if (per_mom or 0) > 0 and (act_mom or 0) <= 0:
            phrase = "增长动力主要由存量活跃账号使用加深拉动"
        elif (per_mom or 0) > 0 and (act_mom or 0) > 0:
            phrase = "活跃规模与使用深度同步提升"
        elif (act_mom or 0) > 0:
            phrase = "增长主要来自活跃账号规模扩大，单账号使用深度仍待提升"
        else:
            phrase = "整体使用热度回落，需关注休眠与沉默账号的召回"
        trend_txt = "均录得增长" if both_up else "均有所回落" if both_down else "走势分化"
        conclusion = [
            {"text": f"{label}功能使用次数达 "}, {"text": f"{_int(cur['featureTotal'])} ", "bold": True},
            {"text": f"次（环比{_spct(feat_mom)}），日均使用（{_spct(daily_mom)}）与单活跃账号功能使用次数（{_spct(per_mom)}）{trend_txt}，表明"},
            {"text": phrase, "highlight": True}, {"text": "。"},
        ]

    worst = max(rows, key=sr, default=None)
    if worst and sr(worst) > (cur["silentRate"] or 0):
        risk = [{"text": f"「{name(worst['key'])}」沉默率 "}, {"text": _pct(sr(worst)), "bold": True},
                {"text": f"，高于整体 {_pct(cur['silentRate'])}；该{dim_label}休眠账号 {_int(worst['dormant']['value'])} 个、沉默账号 {_int(worst['silent']['value'])} 个，存在资源闲置风险，建议优先召回。"}]
    else:
        risk = [{"text": f"各{dim_label}沉默率均未高于整体水平（{_pct(cur['silentRate'])}），资源闲置风险可控。"}]
    # PRD 2.2 风险预警补充：导入率 / 活跃率预警线（事实陈述）
    low_imp = [x for x in rows if x.get("import_rate") and x["import_rate"]["warn"]]
    if low_imp:
        risk.append({"text": f" 另：额度导入率低于 {config.WARN_IMPORT_RATE:.0f}% 预警线：" + "、".join(f"{name(x['key'])} {x['import_rate']['value']:.1f}%" for x in low_imp[:5]) + "。"})
    low_act = [x for x in rows if x["active_rate"]["warn"]]
    if low_act:
        risk.append({"text": f" 活跃率低于 {config.WARN_ACTIVE_RATE:.0f}% 预警线：" + "、".join(f"{name(x['key'])} {x['active_rate']['value']:.1f}%" for x in low_act[:5]) + "。"})

    # PRD 2.2：功能使用规模 / 深度偏低(阈值为暂定预警线，见 config.WARN_DEPTH_RATIO / WARN_SCALE_RATIO)
    from .text import low_usage, usage_risk_sentences
    for sent in usage_risk_sentences(low_usage(rows, cur["perActiveFeature"]), cur["perActiveFeature"], name):
        risk.append({"text": f" {sent}。"})

    growth = [(k, _mom(cur["features"][k], prev.get("features", {}).get(k))) for k in FEATURE_LABEL if k != "poster" or config.POSTER_LIVE]
    growth = sorted([g for g in growth if g[1] is not None], key=lambda g: -g[1])
    best = max(rows, key=ar, default=None)
    highlight = []
    if growth:
        highlight += [{"text": f"「{FEATURE_LABEL[growth[0][0]]}」功能使用环比 "}, {"text": _spct(growth[0][1]), "bold": True}, {"text": "，增长最快"}]
    if best:
        highlight += [{"text": f"{'；' if highlight else ''}{dim_label}维度中「{name(best['key'])}」活跃率 "}, {"text": _pct(ar(best)), "bold": True}, {"text": " 位列第一"}]
    highlight.append({"text": "。" if highlight else "当期暂无明显亮点。"})

    pc = cur["perCapitaGeneration"]
    other = [{"text": f"当期休眠账号 {_int(cur['dormant'])} 个、沉默账号 {_int(cur['silent'])} 个；人均生成 {'—' if pc is None else f'{pc:.1f}'} 次。建议面向休眠账号推送 PPT / 推文模板与使用指引，提升二次使用率。"}]
    return [
        {"id": "conclusion", "kind": "conclusion", "title": "核心结论", "body": conclusion},
        {"id": "risk", "kind": "risk", "title": "风险预警", "body": risk},
        {"id": "highlight", "kind": "highlight", "title": "亮点突破", "body": highlight},
        {"id": "other", "kind": "other", "title": "运营建议", "body": other},
    ]
