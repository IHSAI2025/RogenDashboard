from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException

from .. import config
from ..insight import vm_da as V
from ..metrics import engine as E
from .insight import _meta_rows, _respond
from .vm_common import Ctx, common

router = APIRouter(prefix="/api/vm/da", tags=["vm-da"])


def _dim(dim: str) -> str:
    if dim not in V.DIMS:
        raise HTTPException(400, "dim 应为 da/region/leader")
    return dim


@router.get("/groups")
def groups(dim: str = "da", focus_dim: str | None = None, focus_key: str | None = None, include_unmapped: bool = False,
           ctx: Ctx = Depends(common)):
    """按维度分组的 GroupRow(含 prev 环比周期) + 全平台参考值。focus_* 为气泡/名称点击带入的聚焦。"""
    return V.groups(ctx, _dim(dim), focus_dim, focus_key, include_unmapped)


@router.get("/trend")
def trend(granularity: str = "month", focus_dim: str | None = None, focus_key: str | None = None, ctx: Ctx = Depends(common)):
    if granularity not in ("week", "month", "year"):
        raise HTTPException(400, "granularity 应为 week/month/year")
    return V.trend(ctx, granularity, focus_dim, focus_key)


@router.get("/export")
def export(dim: str = "da", focus_dim: str | None = None, focus_key: str | None = None, include_unmapped: bool = False,
           fmt: str = "xlsx", filters_text: str = "", ctx: Ctx = Depends(common)):
    """多指标明细一览表导出：每个率含分子/分母，另含统计周期、筛选条件、数据截至、口径版本。"""
    dim = _dim(dim)
    res = V.groups(ctx, dim, focus_dim, focus_key, include_unmapped)
    poster = config.POSTER_LIVE
    label = {"da": "DA", "region": "大区", "leader": "圈长"}[dim]
    pp = lambda c, p: (None if c is None or p is None else round((c - p) * 100, 2))  # noqa: E731
    pc = lambda c, p: (None if c is None or not p else round((c - p) / p * 100, 2))  # noqa: E731
    h = [label, "已配置额度", "累计开通账号数", "额度导入率", "有效账号数", "活跃账号数", "活跃率", "活跃率分子", "活跃率分母",
         "功能使用总次数", "单活跃账号功能使用次数", "PPT生成次数", "推文生成次数"] + (["海报生成次数"] if poster else []) + \
        ["总生成次数", "PPT导出次数", "推文导出次数"] + (["海报导出次数"] if poster else []) + \
        ["总导出次数", "导出率", "导出率分子", "导出率分母", "休眠账号数", "沉默账号数", "沉默率", "沉默率分子", "沉默率分母",
         "活跃率环比(pp)", "沉默率环比(pp)", "导入率环比(pp)", "功能使用总次数环比(%)", "总生成次数环比(%)", "总导出次数环比(%)"]
    rows = []
    for r in res["rows"]:
        p = r["prev"] or {}
        g = lambda d, k: (d or {}).get(k)  # noqa: E731
        rows.append([
            "待映射" if r["key"] == V.UNMAPPED_KEY else r["key"], r["quota"], r["opened"], r["importRate"], r["effective"], r["active"],
            r["activeRate"]["rate"], r["activeRate"]["numerator"], r["activeRate"]["denominator"], r["featureTotal"], r["perActiveUsage"],
            r["gen"]["ppt"], r["gen"]["tweet"], *([r["gen"]["poster"]] if poster else []), r["gen"]["total"],
            r["exp"]["ppt"], r["exp"]["tweet"], *([r["exp"]["poster"]] if poster else []), r["exp"]["total"],
            r["exportRate"], r["exp"]["total"], r["gen"]["total"], r["dormant"], r["silent"],
            r["silentRate"]["rate"], r["silentRate"]["numerator"], r["silentRate"]["denominator"],
            pp(r["activeRate"]["rate"], g(p.get("activeRate"), "rate")), pp(r["silentRate"]["rate"], g(p.get("silentRate"), "rate")),
            pp(r["importRate"], p.get("importRate")), pc(r["featureTotal"], p.get("featureTotal")),
            pc(r["gen"]["total"], g(p.get("gen"), "total")), pc(r["exp"]["total"], g(p.get("exp"), "total")),
        ])
    title = f"DA 多指标明细一览表（{label}维度" + (f"，带入 {focus_key}" if focus_key else "") + "）"
    mr = _meta_rows(ctx.ds, title, f"{ctx.start} ~ {ctx.end}", filters_text or "见页面筛选")
    return _respond(fmt, {"多指标明细一览表": (h, rows)}, mr, f"DA明细_{dim}_{ctx.start}_{ctx.end}")
