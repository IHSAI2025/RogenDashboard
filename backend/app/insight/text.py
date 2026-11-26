"""AI 洞察(1.2 / 2.2)：只做规则化的事实陈述，不生成无法溯源的原因判断。LLM 润色留作可插拔(见 insights/generate.py 的配置)。"""
from __future__ import annotations

from .. import config
from ..insight import da as DA


def _pp(v):
    return None if v is None else f"{abs(v):.1f}pp"


def _pct(v):
    return None if v is None else f"{abs(v):.1f}%"


def low_usage(rows: list[dict], overall_per_active: float | None, min_valid: int = 5) -> dict:
    """PRD 2.2「功能使用规模或使用深度偏低」：只做事实判定，阈值见 config.WARN_*_RATIO(暂定)。
    rows 为 insight/da.rows 的行；深度=单活跃账号功能使用次数，规模=有效功能操作总次数。"""
    cand = [r for r in rows if r["key"] != "待映射" and (r["valid"]["value"] or 0) >= min_valid]
    depth = []
    if overall_per_active:
        for r in cand:
            v = r["ops_per_active"]["value"]
            if v is not None and v < overall_per_active * config.WARN_DEPTH_RATIO:
                depth.append((r["key"], v))
    scale = []
    if len(cand) >= 2:
        mean = sum(r["ops"]["value"] for r in cand) / len(cand)
        for r in cand:
            if mean and r["ops"]["value"] < mean * config.WARN_SCALE_RATIO:
                scale.append((r["key"], r["ops"]["value"]))
    depth.sort(key=lambda x: x[1]); scale.sort(key=lambda x: x[1])
    return {"depth": depth, "scale": scale}


def usage_risk_sentences(low: dict, overall_per_active: float | None, name=lambda k: k, limit: int = 5) -> list[str]:
    out = []
    if low["depth"]:
        out.append(f"使用深度偏低（单活跃账号功能使用次数低于整体 {overall_per_active:.1f} 次的 {config.WARN_DEPTH_RATIO:.0%}）："
                   + "、".join(f"{name(k)} {v:.1f}" for k, v in low["depth"][:limit]))
    if low["scale"]:
        out.append(f"使用规模偏低（功能使用总次数低于各组均值的 {config.WARN_SCALE_RATIO:.0%}）："
                   + "、".join(f"{name(k)} {v}" for k, v in low["scale"][:limit]))
    return out


def facts(ov: dict, da_rows: dict, level_label: str) -> dict:
    cur = ov["current"]
    core, bright, risk = [], [], []
    ar = cur["active"]["rate"]
    if ar["value"] is not None:
        txt = f"活跃率 {ar['value']:.1f}%（{ar['num']}/{ar['den']}）"
        if ar["mom"] is not None:
            txt += f"，较对比周期{'上升' if ar['mom'] >= 0 else '下降'} {_pp(ar['mom'])}"
        core.append(txt)
    g = cur["generation"]["gen"]
    if g["mom"] is not None:
        core.append(f"当期成功生成 {g['value']} 次，较对比周期{'增长' if g['mom'] >= 0 else '下降'} {_pct(g['mom'])}")
    else:
        core.append(f"当期成功生成 {g['value']} 次（无可比周期）")
    rows = da_rows["rows"]
    mapped = [r for r in rows if r["key"] != "待映射" and r["active_rate"]["value"] is not None]
    if mapped:
        top = max(mapped, key=lambda r: r["active_rate"]["value"])
        bright.append(f"{level_label}维度活跃率最高：{top['key']} {top['active_rate']['value']:.1f}%（{top['active_rate']['num']}/{top['active_rate']['den']}）")
        best_gen = max(rows, key=lambda r: r["gen_total"]["value"])
        if best_gen["gen_total"]["value"]:
            bright.append(f"成功生成次数最多：{best_gen['key']} {best_gen['gen_total']['value']} 次")
    dist = ov["distribution"]["function_sub"]
    if dist and dist[0]["value"]:
        bright.append(f"使用最多的子功能：{dist[0]['name']}（{dist[0]['value']} 次，组内占比 {dist[0]['ratio']:.1f}%）")
    low = [r for r in mapped if r["active_rate"]["warn"]]
    if low:
        risk.append(f"活跃率低于 {config.WARN_ACTIVE_RATE:.0f}% 预警线：" + "、".join(f"{r['key']} {r['active_rate']['value']:.1f}%" for r in low[:6]))
    imp = [r for r in rows if r.get("import_rate") and r["import_rate"]["warn"]]
    if imp:
        risk.append(f"导入率低于 {config.WARN_IMPORT_RATE:.0f}%（额度尚未充分导入）：" + "、".join(f"{r['key']} {r['import_rate']['value']:.1f}%" for r in imp[:6]))
    sil = [r for r in rows if r["silent_rate"]["warn"]]
    if sil:
        risk.append(f"沉默率高于 {config.WARN_SILENT_RATE:.0f}% 预警线：" + "、".join(f"{r['key']} {r['silent_rate']['value']:.1f}%" for r in sil[:6]))
    ov_pa = ov["current"]["efficiency"]["ops_per_active"]["value"]
    risk += usage_risk_sentences(low_usage(rows, ov_pa), ov_pa)
    idle = [r for r in rows if r["dormant"]["value"]]
    if idle:
        idle.sort(key=lambda r: -r["dormant"]["value"])
        risk.append("休眠账号较多：" + "、".join(f"{r['key']} {r['dormant']['value']}个" for r in idle[:3]))
    return {"core": core, "bright": bright, "risk": risk}
