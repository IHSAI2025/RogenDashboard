"""PRD 4.x 导出报告(HTML)。

- 4.1 单文件 HTML(内联 CSS/SVG，无外部依赖)，可直接另存/发送
- 4.2 封面：「神笔小罗 分析报告」「分析周期：YYYY-MM-DD ～ YYYY-MM-DD」「报告日期：YYYY-MM-DD HH:MM:SS」
- 4.3 正文：每页 16:9(1280×720)，页眉=标题+周期+范围+数据截至，页脚=口径脚注+页码(验收 4)；
  图表带悬停提示、键盘 ←/→ 翻页、打印时每页一张 16:9(可存 PDF)
数据全部复用各 Tab 的后端构造函数，权限已由 ctx(Scope) 裁剪，口径不在此另写。
"""
from __future__ import annotations

import datetime as dt
import html
import math

from .. import config
from ..etl.da_dict import ALL_DAS
from . import cost as COST, da as DA, vm_da, vm_overview as VO

PRIMARY, GREEN, RED, AMBER, GRAY, PURPLE = "#2563eb", "#10b981", "#e11d48", "#f59e0b", "#94a3b8", "#8b5cf6"
C_PPT, C_TWEET = "#1e40af", "#14b8a6"
esc = html.escape

DA_NAMES = {"BC": "乳腺癌 BC", "LC": "肺癌 LC", "GI": "肝癌 GI", "HEMA": "血液肿瘤 HEMA", "OPH": "眼科 OPH", "NS&RD": "神经科学 NS&RD",
            "INF": "流感 INF", "IMMU": "肾病免疫 IMMU", "NMA": "全国准入 NMA", "HSA": "大客户 HSA", "MCE": "多渠道 MCE"}


def pct(v, d=1):
    return "—" if v is None else f"{v * 100:.{d}f}%"


def num(v, d=0):
    return "—" if v is None else f"{v:,.{d}f}"


def mom_html(cur, prev, kind="count", good="up"):
    if cur is None or prev is None or (kind == "count" and not prev):
        return '<span class="mom na">环比 —</span>'
    diff = (cur - prev) * 100 if kind == "rate" else (cur - prev) / prev * 100
    txt = f"{diff:+.1f}{'pp' if kind == 'rate' else '%'}"
    ok = (diff > 0) == (good == "up") if diff else None
    cls = "na" if ok is None else ("up" if ok else "down")
    return f'<span class="mom {cls}">环比 {"▲" if diff > 0 else "▼" if diff < 0 else ""}{txt}</span>'


def tile(label, value, sub="", mom="", warn=False):
    return (f'<div class="tile{" warn" if warn else ""}"><div class="tl">{esc(label)}</div><div class="tv">{value}</div>'
            f'<div class="ts">{sub}</div><div>{mom}</div></div>')


# ───────────── SVG ─────────────
def svg_bars(rows, width=420, warn=None, color=PRIMARY, warn_bad="above", label_w=96, row_h=26):
    """rows: [(label, ratio|None, text)]；warn 为 0~1 预警线。"""
    h = row_h * len(rows) + 22
    bw = width - label_w - 130
    out = [f'<svg viewBox="0 0 {width} {h}" width="100%" role="img">']
    for i, (label, v, text) in enumerate(rows):
        y = 12 + i * row_h
        out.append(f'<text x="{label_w - 8}" y="{y + 13}" text-anchor="end" class="svl">{esc(label)}</text>')
        out.append(f'<rect x="{label_w}" y="{y + 3}" width="{bw}" height="14" rx="3" fill="#f1f5f9"/>')
        if v is not None:
            bad = warn is not None and ((v > warn) if warn_bad == "above" else (v < warn))
            out.append(f'<rect x="{label_w}" y="{y + 3}" width="{max(min(v, 1), 0) * bw:.1f}" height="14" rx="3" fill="{RED if bad else color}">'
                       f'<title>{esc(label)}：{esc(text)}</title></rect>')
        out.append(f'<text x="{label_w + bw + 6}" y="{y + 14}" class="svt">{esc(text)}</text>')
    if warn is not None:
        x = label_w + warn * bw
        out.append(f'<line x1="{x:.1f}" y1="4" x2="{x:.1f}" y2="{h - 14}" stroke="#475569" stroke-dasharray="4 3"/>'
                   f'<text x="{x:.1f}" y="{h - 3}" text-anchor="middle" class="svl">预警线 {warn:.0%}</text>')
    out.append("</svg>")
    return "".join(out)


def svg_hbars(rows, width=520, color=PRIMARY):
    """rows: [(label, value, text)]，按 value 相对最大值画。"""
    mx = max([r[1] for r in rows] + [1])
    h = 30 * len(rows) + 6
    out = [f'<svg viewBox="0 0 {width} {h}" width="100%">']
    for i, (label, v, text) in enumerate(rows):
        y = 4 + i * 30
        w = (width - 250) * v / mx
        out.append(f'<text x="128" y="{y + 15}" text-anchor="end" class="svl">{esc(label)}</text>'
                   f'<rect x="136" y="{y + 3}" width="{w:.1f}" height="16" rx="3" fill="{color}"><title>{esc(label)}：{esc(text)}</title></rect>'
                   f'<text x="{142 + w:.1f}" y="{y + 16}" class="svt">{esc(text)}</text>')
    out.append("</svg>")
    return "".join(out)


def svg_donut(parts, colors, center, size=170):
    tot = sum(v for _, v in parts) or 1
    r, cx, cy, sw = size / 2 - 14, size / 2, size / 2, 24
    out = [f'<svg viewBox="0 0 {size} {size}" width="{size}" height="{size}">']
    ang = -math.pi / 2
    for (name, v), c in zip(parts, colors):
        if not v:
            continue
        a2 = ang + 2 * math.pi * v / tot
        x1, y1, x2, y2 = cx + r * math.cos(ang), cy + r * math.sin(ang), cx + r * math.cos(a2), cy + r * math.sin(a2)
        large = 1 if a2 - ang > math.pi else 0
        if v == tot:
            out.append(f'<circle cx="{cx}" cy="{cy}" r="{r}" fill="none" stroke="{c}" stroke-width="{sw}"><title>{esc(name)}：{num(v)}</title></circle>')
        else:
            out.append(f'<path d="M{x1:.1f},{y1:.1f} A{r},{r} 0 {large} 1 {x2:.1f},{y2:.1f}" fill="none" stroke="{c}" stroke-width="{sw}">'
                       f'<title>{esc(name)}：{num(v)}（{v / tot:.1%}）</title></path>')
        ang = a2
    out.append(f'<text x="{cx}" y="{cy + 5}" text-anchor="middle" class="svl">{esc(center)}</text></svg>')
    legend = "".join(f'<div><i style="background:{c}"></i>{esc(n)}　<b>{num(v)}</b> <span class="mut">({v / tot:.1%})</span></div>'
                     for (n, v), c in zip(parts, colors))
    return f'<div class="donut">{"".join(out)}<div class="lg">{legend}</div></div>'


def svg_lines(labels, series, width=560, height=230, fmt=lambda v: f"{v:g}"):
    """series: [(name, color, values[])]"""
    vals = [v for _, _, vs in series for v in vs if v is not None] or [1]
    mx = max(vals) * 1.15 or 1
    L, T, W, H = 44, 14, width - 60, height - 52
    n = max(len(labels) - 1, 1)
    out = [f'<svg viewBox="0 0 {width} {height}" width="100%">']
    for k in range(5):
        y = T + H - H * k / 4
        out.append(f'<line x1="{L}" y1="{y:.1f}" x2="{L + W}" y2="{y:.1f}" stroke="#e2e8f0"/><text x="{L - 6}" y="{y + 4:.1f}" text-anchor="end" class="svl">{fmt(mx * k / 4)}</text>')
    for i, lb in enumerate(labels):
        out.append(f'<text x="{L + W * i / n:.1f}" y="{height - 20}" text-anchor="middle" class="svl">{esc(lb)}</text>')
    for li, (name, c, vs) in enumerate(series):
        pts = [(L + W * i / n, T + H - H * v / mx) for i, v in enumerate(vs) if v is not None]
        if len(pts) > 1:
            out.append(f'<polyline fill="none" stroke="{c}" stroke-width="2.2" points="{" ".join(f"{x:.1f},{y:.1f}" for x, y in pts)}"/>')
        for i, v in enumerate(vs):
            if v is not None:
                out.append(f'<circle cx="{L + W * i / n:.1f}" cy="{T + H - H * v / mx:.1f}" r="3.5" fill="{c}"><title>{esc(name)} {esc(labels[i])}：{fmt(v)}</title></circle>')
        out.append(f'<text x="{L + 8 + li * 110}" y="{height - 4}" class="svl"><tspan fill="{c}">●</tspan> {esc(name)}</text>')
    out.append("</svg>")
    return "".join(out)


def svg_bubble(points, xref, yref, xlabel, ylabel, xref_label, yref_label, xmax=1.0, ymax=None, width=560, height=290, yfmt=lambda v: f"{v:.0%}"):
    """points: [(name, x(0-1), y, z, tip)]"""
    ymax = ymax or (max([p[2] for p in points] + [yref or 0, 0.01]) * 1.25)
    zmax = max([p[3] for p in points] + [1])
    L, T, W, H = 52, 12, width - 70, height - 52
    out = [f'<svg viewBox="0 0 {width} {height}" width="100%">']
    for k in range(5):
        y = T + H - H * k / 4
        out.append(f'<line x1="{L}" y1="{y:.1f}" x2="{L + W}" y2="{y:.1f}" stroke="#e2e8f0"/><text x="{L - 6}" y="{y + 4:.1f}" text-anchor="end" class="svl">{yfmt(ymax * k / 4)}</text>')
        x = L + W * k / 4
        out.append(f'<text x="{x:.1f}" y="{T + H + 14}" text-anchor="middle" class="svl">{xmax * k / 4:.0%}</text>')
    out.append(f'<text x="{L + W / 2}" y="{height - 4}" text-anchor="middle" class="svl">{esc(xlabel)}</text>'
               f'<text x="10" y="{T + H / 2}" transform="rotate(-90 10 {T + H / 2})" text-anchor="middle" class="svl">{esc(ylabel)}</text>')
    if xref is not None:
        x = L + W * xref / xmax
        out.append(f'<line x1="{x:.1f}" y1="{T}" x2="{x:.1f}" y2="{T + H}" stroke="{GRAY}" stroke-dasharray="4 3"/><text x="{x + 3:.1f}" y="{T + 10}" class="svl">{esc(xref_label)}</text>')
    if yref is not None:
        y = T + H - H * yref / ymax
        out.append(f'<line x1="{L}" y1="{y:.1f}" x2="{L + W}" y2="{y:.1f}" stroke="{RED}" stroke-dasharray="4 3"/><text x="{L + W - 4}" y="{y - 3:.1f}" text-anchor="end" class="svl" fill="{RED}">{esc(yref_label)}</text>')
    for name, x, y, z, tip in points:
        cx, cy, rr = L + W * min(x, xmax) / xmax, T + H - H * min(y, ymax) / ymax, 6 + 16 * math.sqrt(z / zmax)
        out.append(f'<circle cx="{cx:.1f}" cy="{cy:.1f}" r="{rr:.1f}" fill="{PRIMARY}" fill-opacity=".45" stroke="{PRIMARY}"><title>{esc(tip)}</title></circle>'
                   f'<text x="{cx:.1f}" y="{cy - rr - 3:.1f}" text-anchor="middle" class="svl">{esc(name)}</text>')
    out.append("</svg>")
    return "".join(out)


# ───────────── 页面内容 ─────────────
def describe_filters(ctx) -> str:
    f = ctx.f
    das = "全部 DA" if not f.das else "、".join(f.das)
    if f.allowed_das is not None:
        das = f"授权 DA（{'、'.join(f.allowed_das) or '无'}）" + ("" if not f.das else f"，已选 {'、'.join(f.das)}")
    return " ｜ ".join([f"所属DA：{das}", f"账号类型：{'、'.join(f.account_types) if f.account_types else '全部'}",
                       f"来源：{f.source_tag or '全部'}", f"用户身份：{f.identity or '全部'}",
                       f"口径范围：{'核心业务' if f.scope == 'core' else '全平台（剔除测试账号）'}"])


FOOT_USE = ("使用 = PubMed 检索 / 大纲生成 / 内容库分享 / 成功生成 PPT·推文（只登录、失败生成、纯导出不算使用）；"
            "活跃 = 有效账号中周期内有使用；休眠 = 未使用且非沉默；沉默 = 周期内且连续 60 天无使用、开通满 60 天。")
FOOT_STOCK = "累计口径固定为平台上线日 2026/07/01 至统计截止日；累计导入率 = 累计开通账号 ÷ 配置额度（个数）；环比 = 本期末累计 vs 上期末累计。"


def build(ctx, can_cost: bool, full_phone: bool, now: dt.datetime | None = None) -> str:
    now = now or dt.datetime.now()
    snap = VO.snapshots(ctx)
    cur, prv = snap["period"]["current"], snap["period"]["previous"] or {}
    cumv = snap["cumulative"]["core" if ctx.f.scope == "core" else "all"]
    cc, cp = cumv["current"], cumv["previous"] or {}
    dim = "da" if ctx.scope.is_super and not (ctx.f.das and len(ctx.f.das) == 1) else "region"
    dim_label = "DA" if dim == "da" else "大区"
    groups = vm_da.groups(ctx, dim)
    rows = groups["rows"]
    name = (lambda k: DA_NAMES.get(k, k)) if dim == "da" else (lambda k: k)
    period_txt = f"{ctx.start.isoformat()} ～ {ctx.end.isoformat()}"
    meta_line = f"分析周期：{period_txt} ｜ {describe_filters(ctx)} ｜ 数据截至：{ctx.ds.as_of.strftime('%Y-%m-%d %H:%M')}"
    slides: list[tuple[str, str, str]] = []

    # 洞察
    secs = VO.insight_sections(ctx, "overview")
    ins = "".join(f'<div class="ins {s["kind"]}"><h4>{esc(s["title"])}</h4><p>{"".join(esc(t["text"]) for t in s["body"])}</p></div>' for s in secs)
    slides.append(("AI 诊断及洞察", f'<div class="insgrid">{ins}</div>',
                   "洞察仅陈述由已计算指标得出的事实，不自动推断无法溯源的原因；预警线：导入率 <40%、活跃率 <40%、沉默率 >30%（暂定）。"))

    # 累计存量
    q, op = cc["quota"], cc["opened"]
    ir = lambda a, b: pct(a / b if b else None)  # noqa: E731
    tiles = "".join([
        tile("累计导入率", pct(cc["importRate"]), f'{num(op["total"])} / {num(q["total"])}　PLUS {ir(op["plus"], q["plus"])} · SUPER {ir(op["super"], q["super"])}',
             mom_html(cc["importRate"], cp.get("importRate"), "rate"), warn=cc["importRate"] is not None and cc["importRate"] < config.WARN_IMPORT_RATE / 100),
        tile("累计有效账号数", num(cc["valid"]["total"]), f'PLUS {cc["valid"]["plus"]} · SUPER {cc["valid"]["super"]}', mom_html(cc["valid"]["total"], (cp.get("valid") or {}).get("total"))),
        tile("累计激活账号数", num(cc["activated"]["total"]), f'PLUS {cc["activated"]["plus"]} · SUPER {cc["activated"]["super"]}', mom_html(cc["activated"]["total"], (cp.get("activated") or {}).get("total"))),
        tile("累计激活率", pct(cc["activationRate"]), f'{num(cc["activated"]["total"])} / {num(op["total"])}', mom_html(cc["activationRate"], cp.get("activationRate"), "rate")),
        tile("累计功能使用次数", num(cc["featureTotal"]), "", mom_html(cc["featureTotal"], cp.get("featureTotal"))),
    ])
    tiles2 = "".join([
        tile("已配置额度（个）", num(q["total"]), f'PLUS {q["plus"]} · SUPER {q["super"]}', mom_html(q["total"], (cp.get("quota") or {}).get("total"))),
        tile("累计开通账号数", num(op["total"]), f'PLUS {op["plus"]} · SUPER {op["super"]}（含后来停用）', mom_html(op["total"], (cp.get("opened") or {}).get("total"))),
        tile("累计总生成数", num(cc["generation"]["total"]), f'PPT {num(cc["generation"]["ppt"])} · 推文 {num(cc["generation"]["tweet"])}', mom_html(cc["generation"]["total"], (cp.get("generation") or {}).get("total"))),
        tile("累计总导出数", num(cc["exports"]["total"]), f'PPT {num(cc["exports"]["ppt"])} · 推文 {num(cc["exports"]["tweet"])}', mom_html(cc["exports"]["total"], (cp.get("exports") or {}).get("total"))),
    ])
    slides.append((f"累计存量指标（{'核心业务' if ctx.f.scope == 'core' else '全平台'}）", f'<div class="tiles t5">{tiles}</div><div class="tiles t4">{tiles2}</div>', FOOT_STOCK))

    # 当期
    pa = prv.get
    t = "".join([
        tile("活跃账号数", num(cur["active"]), "", mom_html(cur["active"], pa("active"))),
        tile("活跃率", pct(cur["activeRate"]), f'{num(cur["active"])} / {num(cur["valid"])}', mom_html(cur["activeRate"], pa("activeRate"), "rate"),
             warn=cur["activeRate"] is not None and cur["activeRate"] < config.WARN_ACTIVE_RATE / 100),
        tile("日均活跃账号数", num(cur["dailyActive"], 1), "", mom_html(cur["dailyActive"], pa("dailyActive"))),
        tile("休眠账号数 / 休眠率", f'{num(cur["dormant"])} / {pct(cur["dormantRate"])}', f'登录未使用 {num(cur["loginUnusedDormant"])}', mom_html(cur["dormantRate"], pa("dormantRate"), "rate", "down")),
        tile("沉默账号数 / 沉默率", f'{num(cur["silent"])} / {pct(cur["silentRate"])}', f'登录未使用 {num(cur["loginUnusedSilent"])}', mom_html(cur["silentRate"], pa("silentRate"), "rate", "down"),
             warn=cur["silentRate"] is not None and cur["silentRate"] > config.WARN_SILENT_RATE / 100),
        tile("功能使用次数", num(cur["featureTotal"]), f'日均 {num(cur["dailyFeature"], 1)}', mom_html(cur["featureTotal"], pa("featureTotal"))),
        tile("单活跃账号功能使用次数", num(cur["perActiveFeature"], 1), f'{num(cur["featureTotal"])} / {num(cur["active"])}', mom_html(cur["perActiveFeature"], pa("perActiveFeature"))),
        tile("当期生成数", num(cur["generation"]["total"]), f'PPT {cur["generation"]["ppt"]} · 推文 {cur["generation"]["tweet"]}', mom_html(cur["generation"]["total"], (prv.get("generation") or {}).get("total"))),
        tile("当期导出数", num(cur["exports"]["total"]), f'PPT {cur["exports"]["ppt"]} · 推文 {cur["exports"]["tweet"]}', mom_html(cur["exports"]["total"], (prv.get("exports") or {}).get("total"))),
        tile("人均生成次数", num(cur["perCapitaGeneration"], 1), f'日均生成 {num(cur["dailyGeneration"], 1)}', mom_html(cur["perCapitaGeneration"], pa("perCapitaGeneration"))),
    ])
    slides.append(("当期数据指标", f'<div class="tiles t5">{t}</div>', FOOT_USE + " 日均类指标：周期内每日之和 ÷ 统计天数（当月未结束按已过天数）。"))

    # 分布
    d, fn = snap["distribution"], snap["functions"]
    core_rows = [(x["label"], x["value"], "%s（%s）" % (num(x["value"]), pct(x["ratio"]))) for x in fn["core"]]
    sub_rows = [(x["group"] + "·" + x["label"], x["value"], "%s（%s）" % (num(x["value"]), pct(x["ratio"]))) for x in fn["subs"]]
    top_txt = "｜前 %d 个子模块贡献达 %s" % (fn["topN"], pct(fn["topShare"], 0)) if fn["topN"] else ""
    types_svg = svg_donut([("PLUS账号", d["types"]["plus"]), ("SUPER账号", d["types"]["super"])], [PRIMARY, PURPLE], "账号类型")
    ident_svg = svg_donut([("员工", d["identities"]["staff"]), ("客户", d["identities"]["customer"])], [GREEN, "#99e0cb"], "用户身份")
    body = ('<div class="two"><div><h5>账号类型（累计开通）</h5>' + types_svg + '<h5>用户身份（累计开通）</h5>' + ident_svg + '</div>'
            '<div><h5>主模块使用次数</h5>' + svg_hbars(core_rows, color=C_PPT) +
            '<h5>子模块使用次数（组内占比）' + top_txt + '</h5>' + svg_hbars(sub_rows, color=C_TWEET) + '</div></div>')
    slides.append(("账号及功能使用分布", body, "账号分布按统计截止日累计开通账号计；功能使用次数按有效功能操作计（成败均计）；Top N = 子模块按次数降序累计占比首次 ≥ 50% 的最小 N。"))

    # 趋势
    tr = VO.trend(ctx, "month")
    labs = [r["start"][:7] for r in tr["rows"]]
    kinds = [("ppt", "PPT", C_PPT), ("tweet", "推文", C_TWEET)] + ([("poster", "海报", AMBER)] if config.POSTER_LIVE else [])
    body = (f'<div class="two"><div><h5>核心功能生成总次数</h5>{svg_lines(labs, [(n, c, [r["total"][k] for r in tr["rows"]]) for k, n, c in kinds])}</div>'
            f'<div><h5>核心功能人均生成次数（次/账号）</h5>{svg_lines(labs, [(n + "人均", c, [r["perCapita"][k] for r in tr["rows"]]) for k, n, c in kinds], fmt=lambda v: f"{v:.1f}")}</div></div>')
    slides.append(("核心功能生成次数趋势", body, "成功生成次数按月汇总（当月未结束为截至数据日）；人均 = 该功能成功生成次数 ÷ 该功能的内容生成账号数。"))

    # 三率
    def rate_rows(key):
        out = []
        for r in sorted(rows, key=lambda x: -(((x["importRate"] if key == "importRate" else x[key]["rate"])) or 0)):
            if key == "importRate":
                if r["importRate"] is None:
                    continue
                out.append((name(r["key"]), r["importRate"], f'{pct(r["importRate"])}（{r["opened"]}/{r["quota"]}）'))
            else:
                x = r[key]
                out.append((name(r["key"]), x["rate"], f'{pct(x["rate"])}（{x["numerator"]}/{x["denominator"]}）'))
        return out
    wi, wa, ws = config.WARN_IMPORT_RATE / 100, config.WARN_ACTIVE_RATE / 100, config.WARN_SILENT_RATE / 100
    imp = rate_rows("importRate")
    body = (f'<div class="three"><div><h5>账号导入率</h5>{svg_bars(imp, 420, wi, warn_bad="below") if imp else "<p class=mut>导入率仅按 DA 维度统计；无额度数据时显示「待接入」</p>"}</div>'
            f'<div><h5>账号活跃率</h5>{svg_bars(rate_rows("activeRate"), 420, wa, warn_bad="below")}</div>'
            f'<div><h5>账号沉默率</h5>{svg_bars(rate_rows("silentRate"), 420, ws)}</div></div>')
    slides.append((f"{dim_label} 三率看板", body, "每个率均标注 分子/分母；红色柱 = 触及预警线（导入率<40%、活跃率<40%、沉默率>30%，暂定）；虚线 = 预警线。"))

    # 气泡
    plat = groups["platform"]
    p1 = [(name(r["key"]), r["activeRate"]["rate"], r["silentRate"]["rate"] or 0, r["effective"],
           f'{name(r["key"])}\n有效账号 {r["effective"]}\n活跃率 {pct(r["activeRate"]["rate"])}（{r["activeRate"]["numerator"]}/{r["activeRate"]["denominator"]}）\n沉默率 {pct(r["silentRate"]["rate"])}（{r["silentRate"]["numerator"]}/{r["silentRate"]["denominator"]}）')
          for r in rows if r["activeRate"]["rate"] is not None]
    p2 = [(name(r["key"]), r["activeRate"]["rate"], r["perActiveUsage"] or 0, max(r["featureTotal"], 1),
           f'{name(r["key"])}\n活跃率 {pct(r["activeRate"]["rate"])}\n有效功能操作 {r["featureTotal"]}\n单活跃账号功能使用次数 {num(r["perActiveUsage"], 1)}\n内容生成账号 {r["genAccounts"]}')
          for r in rows if r["activeRate"]["rate"] is not None and r["perActiveUsage"] is not None]
    body = (f'<div class="two"><div><h5>{dim_label}运营健康分布（气泡=有效账号数）</h5>'
            f'{svg_bubble(p1, plat["activeRate"]["rate"], ws, "活跃率", "沉默率", "全平台活跃率", "沉默率预警线 30%", ymax=max(0.4, max([p[2] for p in p1] + [0]) * 1.2))}</div>'
            f'<div><h5>{dim_label}功能使用效能（气泡=有效功能操作总次数）</h5>'
            f'{svg_bubble(p2, plat["activeRate"]["rate"], plat["perActiveUsage"], "活跃率", "单活跃账号功能使用次数", "全平台活跃率", "全平台单活跃账号使用次数", yfmt=lambda v: f"{v:.0f}")}</div></div>')
    slides.append((f"{dim_label} 使用深度", body, "单活跃账号功能使用次数 = 周期内有效功能操作总次数 ÷ 周期内活跃账号数；参考线为全平台水平（受角色数据范围约束）。"))

    # 明细表
    cols = [(dim_label, lambda r: name(r["key"])), ("额度", lambda r: "待接入" if r["quota"] is None else num(r["quota"])), ("累计开通", lambda r: num(r["opened"])),
            ("导入率", lambda r: "—" if r["importRate"] is None else f'{pct(r["importRate"])} ({r["opened"]}/{r["quota"]})'),
            ("有效", lambda r: num(r["effective"])), ("活跃", lambda r: num(r["active"])),
            ("活跃率", lambda r: f'{pct(r["activeRate"]["rate"])} ({r["activeRate"]["numerator"]}/{r["activeRate"]["denominator"]})'),
            ("功能使用", lambda r: num(r["featureTotal"])), ("单活跃使用", lambda r: num(r["perActiveUsage"], 1)),
            ("生成", lambda r: num(r["gen"]["total"])), ("导出", lambda r: num(r["exp"]["total"])), ("导出率", lambda r: pct(r["exportRate"])),
            ("休眠", lambda r: num(r["dormant"])), ("沉默", lambda r: num(r["silent"])),
            ("沉默率", lambda r: f'{pct(r["silentRate"]["rate"])} ({r["silentRate"]["numerator"]}/{r["silentRate"]["denominator"]})')]
    per = 11
    chunks = [rows[i:i + per] for i in range(0, max(len(rows), 1), per)]
    for ci, ch in enumerate(chunks):
        th = "".join(f"<th>{c}</th>" for c, _ in cols)
        tr_ = "".join("<tr>" + "".join(f"<td>{esc(str(f(r)))}</td>" for _, f in cols) + "</tr>" for r in ch)
        slides.append((f"{dim_label} 多指标明细一览表" + (f"（{ci + 1}/{len(chunks)}）" if len(chunks) > 1 else ""),
                       f'<table class="tb"><tr>{th}</tr>{tr_}</table>',
                       "导出率 = 导出次数 ÷ 成功生成次数（同一内容重复导出重复计算，可能超过 100%）；单活跃账号功能使用次数分母为 0 显示「—」。" + FOOT_USE))

    # 费用
    if can_cost:
        month = ctx.end.strftime("%Y-%m")
        level = "da" if ctx.scope.is_super else "region"
        res = COST.build(ctx.ds, ctx.idx, ctx.f, month, level, full_phone)
        o = res["overview"]
        u = o["usage"]
        rr = lambda v: None if v is None else v / 100  # noqa: E731
        ct = "".join([
            tile("本月花费（元）", num(o["cost"]["value"], 2), f'采购账号费用 {num(o["cost"]["purchase"], 2)} ｜ 免费账号成本 {num(o["cost"]["free"], 2)}', mom_html(o["cost"]["value"], o["cost"]["prev"], "count", "down")),
            tile("本月预算（元）", num(o["budget"]["value"]), f'PLUS {o["budget"]["n_plus"]}个 × 600 ｜ SUPER {o["budget"]["n_super"]}个 × 1200', mom_html(o["budget"]["value"], o["budget"]["prev"])),
            tile("预算使用率", "—" if u["value"] is None else f'{u["value"]:.1f}%', f'{num(u["num"], 2)} / {num(u["den"])}', mom_html(rr(u["value"]), rr(u["prev"]), "rate", "down")),
            tile("本年累计花费（元）", num(o["ytd"]["value"], 2), f'采购账号费用 {num(o["ytd"]["purchase"], 2)} ｜ 免费账号成本 {num(o["ytd"]["free"], 2)}', ""),
        ])
        lvl = "DA" if level == "da" else "大区"

        def use_txt(r):
            return "—" if r["usage"] is None else f'{r["usage"]:.1f}% ({num(r["usage_num"], 2)}/{num(r["usage_den"])})'
        rk = "".join(f'<tr><td>{esc(DA_NAMES.get(r["key"], r["key"]) if level == "da" else r["key"])}</td><td>{r["n_accounts"]}</td><td>{num(r["budget"])}</td>'
                     f'<td>{num(r["cost"], 2)}</td><td>{num(r["purchase"], 2)}</td><td>{num(r["free"], 2)}</td><td>{use_txt(r)}</td>'
                     f'<td>{"—" if r["per_capita"] is None else num(r["per_capita"], 2)}</td></tr>' for r in res["rank"][:10])
        body = (f'<div class="tiles t4">{ct}</div><table class="tb"><tr><th>{lvl}</th><th>账号数</th><th>本月预算</th><th>本月花费</th>'
                f'<th>采购账号费用</th><th>免费账号成本</th><th>预算使用率</th><th>人均花费</th></tr>{rk}</table>')
        slides.append((f"费用看板（统计月份 {month}）", body,
                       "花费 = token 消耗按换算比例折算的元（换算比例 [TBD] 待商汤确认）；本月预算 = 生效账号月度预算之和（PLUS 600 / SUPER 1200，整月计入）；采购账号费用 + 免费账号成本 = 本月花费。"))

    return render(ctx, slides, meta_line, period_txt, now)


CSS = """
*{box-sizing:border-box}body{margin:0;background:#e2e8f0;font-family:-apple-system,'PingFang SC','Noto Sans SC','Microsoft YaHei',sans-serif;color:#1e293b}
.bar{position:sticky;top:0;z-index:5;background:#0f172a;color:#fff;padding:8px 16px;font-size:13px;display:flex;gap:12px;align-items:center}
.bar button{background:#2563eb;color:#fff;border:0;border-radius:6px;padding:5px 12px;cursor:pointer}
.slide{width:1280px;height:720px;margin:20px auto;background:#fff;position:relative;display:flex;flex-direction:column;box-shadow:0 2px 12px rgba(15,23,42,.15);overflow:hidden}
.slide>header{padding:22px 40px 10px;border-bottom:1px solid #e2e8f0}.slide>header h2{margin:0;font-size:24px}.meta{margin-top:5px;font-size:11.5px;color:#64748b;line-height:1.5}
.body{flex:1;padding:16px 40px;overflow:hidden}.slide>footer{padding:8px 40px;font-size:10.5px;color:#64748b;border-top:1px solid #e2e8f0;display:flex;justify-content:space-between;gap:24px}
.cover{background:linear-gradient(135deg,#1e3a8a,#2563eb);color:#fff;justify-content:center;padding:0 90px}.cover h1{font-size:54px;margin:0 0 28px}.cover p{font-size:20px;margin:8px 0}.cover small{display:block;margin-top:40px;font-size:13px;opacity:.85;line-height:1.7}
.tiles{display:grid;gap:12px;margin-bottom:14px}.t5{grid-template-columns:repeat(5,1fr)}.t4{grid-template-columns:repeat(4,1fr)}
.tile{border:1px solid #e2e8f0;border-radius:10px;padding:12px 14px;background:#f8fafc}.tile.warn{border-color:#fda4af;background:#fff1f2}
.tl{font-size:12px;color:#64748b}.tv{font-size:24px;font-weight:600;margin:4px 0;font-variant-numeric:tabular-nums}.ts{font-size:11px;color:#64748b;min-height:15px}
.mom{font-size:11.5px}.mom.up{color:#059669}.mom.down{color:#e11d48}.mom.na{color:#94a3b8}
.two{display:grid;grid-template-columns:1fr 1fr;gap:24px}.three{display:grid;grid-template-columns:1fr 1fr 1fr;gap:18px}h5{margin:6px 0;font-size:13px}
.insgrid{display:grid;grid-template-columns:1fr 1fr;gap:14px}.ins{border:1px solid #e2e8f0;border-radius:10px;padding:12px 16px;background:#f8fafc}.ins h4{margin:0 0 6px;font-size:14px}.ins p{margin:0;font-size:13px;line-height:1.7}
.ins.risk h4{color:#e11d48}.ins.highlight h4{color:#059669}.ins.conclusion h4{color:#2563eb}
.svl{font-size:10.5px;fill:#475569}.svt{font-size:10.5px;fill:#0f172a}.mut{color:#94a3b8}
.donut{display:flex;align-items:center;gap:18px}.lg div{font-size:12.5px;margin:4px 0}.lg i{display:inline-block;width:10px;height:10px;border-radius:2px;margin-right:6px}
.tb{width:100%;border-collapse:collapse;font-size:11.5px}.tb th,.tb td{border-bottom:1px solid #e2e8f0;padding:6px 6px;text-align:right;white-space:nowrap}.tb th{background:#f1f5f9;color:#475569}.tb td:first-child,.tb th:first-child{text-align:left}
@media print{@page{size:1280px 720px;margin:0}body{background:#fff}.bar{display:none}.slide{margin:0;box-shadow:none;page-break-after:always}}
"""

JS = """
const S=[...document.querySelectorAll('.slide')];let i=0;
function go(n){i=Math.max(0,Math.min(S.length-1,n));S[i].scrollIntoView({behavior:'smooth',block:'center'})}
addEventListener('keydown',e=>{if(['ArrowRight','ArrowDown','PageDown'].includes(e.key))go(i+1);if(['ArrowLeft','ArrowUp','PageUp'].includes(e.key))go(i-1)});
"""


def render(ctx, slides, meta_line, period_txt, now) -> str:
    total = len(slides) + 1
    mock = "、".join(ctx.ds.mock_fields)
    cover = (f'<section class="slide cover"><h1>神笔小罗 分析报告</h1><p>分析周期：{esc(ctx.start.isoformat())} ～ {esc(ctx.end.isoformat())}</p>'
             f'<p>报告日期：{now.strftime("%Y-%m-%d %H:%M:%S")}</p>'
             f'<small>{esc(describe_filters(ctx))}<br>数据截至：{esc(ctx.ds.as_of.strftime("%Y-%m-%d %H:%M"))} ｜ 口径版本：{esc(config.METRIC_VERSION)}'
             f'{"<br>⚠ 含模拟数据字段（乙方接口未接入）：" + esc(mock) if mock else ""}</small></section>')
    pages = []
    for n, (title, body, foot) in enumerate(slides, start=2):
        pages.append(f'<section class="slide"><header><h2>{esc(title)}</h2><div class="meta">{esc(meta_line)}</div></header>'
                     f'<div class="body">{body}</div><footer><span>口径说明：{esc(foot)}</span><span style="white-space:nowrap">{n} / {total}</span></footer></section>')
    return (f'<!doctype html><html lang="zh-CN"><head><meta charset="utf-8"><title>神笔小罗 分析报告 {esc(period_txt)}</title><style>{CSS}</style></head><body>'
            f'<div class="bar"><b>神笔小罗 分析报告</b><span>{esc(period_txt)}</span><span>← → 翻页</span><button onclick="print()">打印 / 另存 PDF（16:9）</button></div>'
            f'{cover}{"".join(pages)}<script>{JS}</script></body></html>')
