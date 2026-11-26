from __future__ import annotations

import csv
import dataclasses
import datetime as dt
import io
import zipfile
from urllib.parse import quote

from fastapi import APIRouter, Depends, HTTPException, Query
from fastapi.responses import Response
from sqlalchemy import func
from sqlalchemy.orm import Session

from .. import config, models
from ..database import get_db
from ..etl.da_dict import ALL_DAS, DA_GROUPS
from ..insight import cost as COST, da as DA, overview as OV, text as TXT, users as USERS
from ..metrics import engine as E
from ..metrics.engine import Filters
from ..services_scope import Scope, get_scope
from ..vendor.local_adapter import build_dataset

router = APIRouter(prefix="/api/insight", tags=["insight"])

_cache: dict = {}


def load(db: Session):
    """Dataset+Index 缓存。local：按库内数据签名失效；vendor：按 TTL(VENDOR_CACHE_TTL) 重新拉取。"""
    if config.DATA_SOURCE == "vendor":
        import time
        if _cache.get("vendor_at") is None or time.time() - _cache["vendor_at"] > config.VENDOR_CACHE_TTL:
            from ..vendor.vendor_adapter import build_dataset_from_vendor
            ds = build_dataset_from_vendor()
            _cache.update(vendor_at=time.time(), ds=ds, idx=E.Index(ds))
        return _cache["ds"], _cache["idx"]
    sig = (
        db.query(func.count(models.ProjectItem.id), func.max(models.ProjectItem.id)).one(),
        db.query(func.count(models.Account.id)).scalar(),
        db.query(func.max(models.RosterSnapshot.id)).scalar(),
        db.query(func.count(models.QuotaConfig.id), func.max(models.QuotaConfig.id)).one(),
        db.query(func.count(models.ExclusionRule.id)).scalar(),
        db.query(func.max(models.WeeklyUpload.id)).scalar(), config.MOCK_FILL,
    )
    if _cache.get("sig") != sig:
        ds = build_dataset(db)
        _cache.update(sig=sig, ds=ds, idx=E.Index(ds))
    return _cache["ds"], _cache["idx"]


def _list(v: str | None):
    return [x for x in (v or "").split(",") if x] or None


def _d(v: str, name: str) -> dt.date:
    try:
        return dt.date.fromisoformat(v)
    except ValueError:
        raise HTTPException(400, f"{name} 日期格式应为 YYYY-MM-DD")


def make_filters(scope: Scope, das=None, account_types=None, source_tag=None, identity=None, scope_view="platform", **kw) -> Filters:
    return Filters(das=_list(das), account_types=_list(account_types), source_tag=source_tag or None, identity=identity or None,
                   scope=scope_view, allowed_das=scope.managed, **kw)


def meta_of(ds) -> dict:
    return {"as_of": ds.as_of.strftime("%Y-%m-%d %H:%M"), "mock_fields": ds.mock_fields, "poster_live": config.POSTER_LIVE,
            "metric_version": config.METRIC_VERSION, "fx_version": ds.fx_version}


@router.get("/meta")
def meta(db: Session = Depends(get_db), scope: Scope = Depends(get_scope)):
    ds, idx = load(db)
    das = ALL_DAS if scope.managed is None else scope.managed
    return {**meta_of(ds), "role": scope.role, "can_cost": scope.can_cost, "is_super": scope.is_super,
            "managed_das": scope.managed, "cost_level": scope.level,
            "da_groups": {g: [d for d in v if d in das] for g, v in DA_GROUPS.items() if any(d in das for d in v)},
            "launch_date": config.PLATFORM_LAUNCH_DATE, "default_month": ds.as_of.strftime("%Y-%m"),
            "warn": {"import": config.WARN_IMPORT_RATE, "active": config.WARN_ACTIVE_RATE, "silent": config.WARN_SILENT_RATE},
            "regions": sorted({a.region for a in ds.accounts if a.region and (scope.managed is None or a.da in scope.managed)})}


COMMON = dict(das=Query(None), account_types=Query(None), source_tag=Query(None), identity=Query(None))


@router.get("/overview")
def overview(start: str, end: str, mode: str = "mom", view: str = "platform", das: str | None = None, account_types: str | None = None,
             source_tag: str | None = None, identity: str | None = None, db: Session = Depends(get_db), scope: Scope = Depends(get_scope)):
    ds, idx = load(db)
    f = make_filters(scope, das, account_types, source_tag, identity, view)
    s, e = _d(start, "start"), _d(end, "end")
    res = OV.build(ds, idx, f, s, e, mode)
    return {**res, "meta": meta_of(ds)}


@router.get("/overview/trend")
def overview_trend(start: str, end: str, granularity: str = "month", view: str = "platform", das: str | None = None,
                   account_types: str | None = None, source_tag: str | None = None, identity: str | None = None,
                   db: Session = Depends(get_db), scope: Scope = Depends(get_scope)):
    ds, idx = load(db)
    f = make_filters(scope, das, account_types, source_tag, identity, view)
    return OV.trend(ds, idx, f, _d(start, "start"), _d(end, "end"), granularity)


@router.get("/da")
def da_rows(start: str, end: str, mode: str = "mom", dim: str = "da", types: str | None = None, das: str | None = None,
            account_types: str | None = None, source_tag: str | None = None, identity: str | None = None, view: str = "platform",
            db: Session = Depends(get_db), scope: Scope = Depends(get_scope)):
    ds, idx = load(db)
    if dim not in DA.DIMS:
        raise HTTPException(400, "dim 应为 da/region/circle")
    f = make_filters(scope, das, account_types, source_tag, identity, view)
    res = DA.rows(ds, idx, f, _d(start, "start"), _d(end, "end"), mode, dim, _list(types))
    return {**res, "meta": meta_of(ds)}


@router.get("/da/trend")
def da_trend(start: str, end: str, granularity: str = "month", da: str | None = None, region: str | None = None, das: str | None = None,
             account_types: str | None = None, source_tag: str | None = None, identity: str | None = None, view: str = "platform",
             db: Session = Depends(get_db), scope: Scope = Depends(get_scope)):
    ds, idx = load(db)
    f = make_filters(scope, das, account_types, source_tag, identity, view)
    return DA.trend(ds, idx, f, _d(start, "start"), _d(end, "end"), granularity, da, region)


@router.get("/users")
def users(start: str, end: str, state: str = "活跃", status: str | None = None, das: str | None = None, account_types: str | None = None,
          source_tag: str | None = None, identity: str | None = None, view: str = "platform",
          db: Session = Depends(get_db), scope: Scope = Depends(get_scope)):
    ds, idx = load(db)
    f = make_filters(scope, das, account_types, source_tag, identity, view)
    res = USERS.rows(ds, idx, f, _d(start, "start"), _d(end, "end"), state, status, scope.is_super)
    return {**res, "meta": meta_of(ds)}


@router.get("/users/{account_id}/weekly")
def user_weekly(account_id: int, end: str, db: Session = Depends(get_db), scope: Scope = Depends(get_scope)):
    ds, idx = load(db)
    acc = next((a for a in ds.accounts if a.id == account_id), None)
    if acc is None or (scope.managed is not None and acc.da not in scope.managed):
        raise HTTPException(404, "账号不存在或无权查看")
    return USERS.weekly(ds, idx, account_id, _d(end, "end"))


def _need_cost(scope: Scope):
    if not scope.can_cost:
        raise HTTPException(403, "无权查看费用看板")


@router.get("/cost")
def cost(month: str, das: str | None = None, account_types: str | None = None, source_tag: str | None = None, identity: str | None = None,
         db: Session = Depends(get_db), scope: Scope = Depends(get_scope)):
    _need_cost(scope)
    ds, idx = load(db)
    f = make_filters(scope, das, account_types, source_tag, identity)
    res = COST.build(ds, idx, f, month, scope.level, scope.is_super)
    return {**res, "meta": meta_of(ds)}


@router.get("/cost/daily")
def cost_daily(month: str, das: str | None = None, account_types: str | None = None, source_tag: str | None = None,
               identity: str | None = None, db: Session = Depends(get_db), scope: Scope = Depends(get_scope)):
    _need_cost(scope)
    ds, idx = load(db)
    return COST.daily(ds, idx, make_filters(scope, das, account_types, source_tag, identity), month)


@router.get("/cost/account/{account_id}")
def cost_account(account_id: int, month: str, db: Session = Depends(get_db), scope: Scope = Depends(get_scope)):
    _need_cost(scope)
    ds, idx = load(db)
    acc = next((a for a in ds.accounts if a.id == account_id), None)
    if acc is None or (scope.managed is not None and acc.da not in scope.managed):
        raise HTTPException(404, "账号不存在或无权查看")
    return COST.account_detail(ds, idx, account_id, month)


# ───────────── AI 洞察 ─────────────
@router.get("/insight-text")
def insight_text(start: str, end: str, mode: str = "mom", das: str | None = None, account_types: str | None = None,
                 source_tag: str | None = None, identity: str | None = None, view: str = "platform",
                 db: Session = Depends(get_db), scope: Scope = Depends(get_scope)):
    ds, idx = load(db)
    f = make_filters(scope, das, account_types, source_tag, identity, view)
    s, e = _d(start, "start"), _d(end, "end")
    dim = "da" if scope.is_super else "region"
    ov = OV.build(ds, idx, f, s, e, mode)
    rows = DA.rows(ds, idx, f, s, e, mode, dim)
    fx = TXT.facts(ov, rows, "DA" if dim == "da" else "大区")
    key = f"{scope.role}|{','.join(scope.managed or [])}|{start}|{end}|{das}|{account_types}|{source_tag}|{identity}|{view}"
    note = db.query(models.InsightNote).filter_by(key=key).one_or_none()
    return {"facts": fx, "edited": note.content if note else None, "key": key, "editable": scope.is_super, "level": dim}


@router.put("/insight-text")
def save_insight_text(payload: dict, db: Session = Depends(get_db), scope: Scope = Depends(get_scope)):
    if not scope.is_super:
        raise HTTPException(403, "仅超级管理员可编辑洞察")
    key, content = payload.get("key"), (payload.get("content") or "").strip()
    note = db.query(models.InsightNote).filter_by(key=key).one_or_none()
    if not content:
        if note:
            db.delete(note)
    elif note:
        note.content, note.updated_at = content, dt.datetime.utcnow()
    else:
        db.add(models.InsightNote(key=key, content=content))
    db.commit()
    return {"ok": True}


# ───────────── 导出 ─────────────
def _fmt(v):
    if isinstance(v, float):
        return round(v, 4)
    return v


def _rate_cols(m):
    return [(_fmt(m["value"]) if m else None), (m or {}).get("num"), (m or {}).get("den"), _fmt((m or {}).get("mom"))] if m else [None] * 4


def _csv_bytes(headers, rows, meta_lines):
    buf = io.StringIO()
    for l in meta_lines:
        buf.write("# " + l + "\n")
    w = csv.writer(buf)
    w.writerow(headers)
    w.writerows(rows)
    return ("﻿" + buf.getvalue()).encode("utf-8")


def _xlsx_bytes(tables, meta_rows):
    import openpyxl
    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "说明"
    for r in meta_rows:
        ws.append(list(r))
    for name, (headers, rows) in tables.items():
        sh = wb.create_sheet(name)
        sh.append(headers)
        for r in rows:
            sh.append(list(r))
    out = io.BytesIO()
    wb.save(out)
    return out.getvalue()


def _respond(fmt: str, tables: dict, meta_rows: list, filename: str):
    meta_lines = [f"{k}：{v}" for k, v in meta_rows]
    if fmt == "xlsx":
        data, media, ext = _xlsx_bytes(tables, meta_rows), "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", "xlsx"
    elif len(tables) == 1:
        (h, r), = tables.values()
        data, media, ext = _csv_bytes(h, r, meta_lines), "text/csv; charset=utf-8", "csv"
    else:
        buf = io.BytesIO()
        with zipfile.ZipFile(buf, "w", zipfile.ZIP_DEFLATED) as z:
            for name, (h, r) in tables.items():
                z.writestr(f"{filename}_{name}.csv", _csv_bytes(h, r, meta_lines))
        data, media, ext = buf.getvalue(), "application/zip", "zip"
    return Response(data, media_type=media,
                    headers={"Content-Disposition": f"attachment; filename*=UTF-8''{quote(filename)}.{ext}"})


def _meta_rows(ds, title, period, filters):
    return [("报表", title), ("统计周期", period), ("筛选条件", filters), ("数据截至", ds.as_of.strftime("%Y-%m-%d %H:%M")),
            ("口径版本", config.METRIC_VERSION), ("含模拟数据字段", "、".join(ds.mock_fields) or "无")]


@router.get("/export/da")
def export_da(start: str, end: str, mode: str = "mom", dim: str = "da", das: str | None = None, account_types: str | None = None,
              source_tag: str | None = None, identity: str | None = None, view: str = "platform", fmt: str = "xlsx",
              db: Session = Depends(get_db), scope: Scope = Depends(get_scope)):
    ds, idx = load(db)
    f = make_filters(scope, das, account_types, source_tag, identity, view)
    res = DA.rows(ds, idx, f, _d(start, "start"), _d(end, "end"), mode, dim)
    headers = ["维度", "已配置额度", "累计开通账号数", "额度导入率%", "导入率分子", "导入率分母", "有效账号数", "活跃账号数", "活跃率%", "活跃率分子", "活跃率分母", "活跃率环比pp",
               "功能使用总次数", "单活跃账号功能使用次数", "PPT生成", "推文生成", "海报生成", "总生成", "PPT导出", "推文导出", "海报导出", "总导出",
               "导出率%", "导出率分子", "导出率分母", "休眠账号数", "沉默账号数", "沉默率%", "沉默率分子", "沉默率分母", "沉默率环比pp"]
    rows = []
    for r in res["rows"]:
        v = lambda k: r[k]["value"] if r.get(k) else None  # noqa: E731
        rows.append([r["key"], r["quota"], v("opened"), *_rate_cols(r["import_rate"])[:3], v("valid"), v("active"), *_rate_cols(r["active_rate"]),
                     v("ops"), _fmt(v("ops_per_active")), v("gen_ppt"), v("gen_tweet"), v("gen_poster"), v("gen_total"),
                     v("exp_ppt"), v("exp_tweet"), v("exp_poster"), v("exp_total"), *_rate_cols(r["export_rate"])[:3],
                     v("dormant"), v("silent"), *_rate_cols(r["silent_rate"])])
    mr = _meta_rows(ds, "DA 多指标明细", f"{start} ~ {res['period']['end']}", f"维度={dim} DA={das or '全部'} 类型={account_types or '全部'} 来源={source_tag or '全部'} 身份={identity or '全部'}")
    return _respond(fmt, {"DA明细": (headers, rows)}, mr, f"DA明细_{start}_{end}")


@router.get("/export/users")
def export_users(start: str, end: str, state: str = "活跃", status: str | None = None, das: str | None = None, account_types: str | None = None,
                 source_tag: str | None = None, identity: str | None = None, view: str = "platform", fmt: str = "xlsx",
                 db: Session = Depends(get_db), scope: Scope = Depends(get_scope)):
    ds, idx = load(db)
    f = make_filters(scope, das, account_types, source_tag, identity, view)
    res = USERS.rows(ds, idx, f, _d(start, "start"), _d(end, "end"), state, status, scope.is_super)
    cols = [("账号ID", "id"), ("姓名", "name"), ("联系电话", "phone"), ("所属DA", "da"), ("大区", "region"), ("用户身份", "identity"), ("账号类型", "account_type"),
            ("账号来源标签", "source_tag"), ("可用状态", "status"), ("备注", "remark"), ("使用状态", "state"), ("活跃天数", "active_days"),
            ("连续未使用天数", "idle_days"), ("最近使用日期", "last_use"), ("功能使用总次数", "ops_total"), ("PubMed检索次数", "pubmed"),
            ("大纲生成次数", "outline"), ("内容库分享次数", "share"), ("PPT功能使用次数", "ppt_ops"), ("推文功能使用次数", "tweet_ops"),
            ("海报功能使用次数", "poster_ops"), ("PPT生成次数", "gen_ppt"), ("推文生成次数", "gen_tweet"), ("海报生成次数", "gen_poster"),
            ("总生成次数", "gen_total"), ("最近成功生成日期", "last_gen"), ("PPT导出次数", "exp_ppt"), ("推文导出次数", "exp_tweet"),
            ("海报导出次数", "exp_poster"), ("总导出次数", "exp_total")]
    rows = [[r[k] for _, k in cols] for r in res["rows"]]
    mr = _meta_rows(ds, f"用户明细-{state}", f"{start} ~ {res['period']['end']}", f"DA={das or '全部'} 类型={account_types or '全部'} 来源={source_tag or '全部'} 身份={identity or '全部'} 可用状态={status or '全部'}")
    return _respond(fmt, {f"{state}用户": ([c for c, _ in cols], rows)}, mr, f"用户明细_{state}_{start}_{end}")


@router.get("/export/cost")
def export_cost(month: str, das: str | None = None, account_types: str | None = None, source_tag: str | None = None,
                identity: str | None = None, fmt: str = "xlsx", db: Session = Depends(get_db), scope: Scope = Depends(get_scope)):
    _need_cost(scope)
    ds, idx = load(db)
    res = COST.build(ds, idx, make_filters(scope, das, account_types, source_tag, identity), month, scope.level, scope.is_super)
    lvl = "DA" if scope.level == "da" else "大区"
    rank_h = [lvl, "账号数", "本月预算(元)", "本月花费(元)", "采购账号费用(元)", "免费账号成本(元)", "预算使用率%", "使用率分子", "使用率分母", "人均花费(元)", "有花费账号数", "本月花费环比%"]
    rank_r = [[r["key"], r["n_accounts"], r["budget"], r["cost"], r["purchase"], r["free"], _fmt(r["usage"]), r["usage_num"], r["usage_den"],
               _fmt(r["per_capita"]), r["paying"], _fmt(r["mom"])] for r in res["rank"]]
    rank_r.append(["合计", sum(r["n_accounts"] for r in res["rank"]), sum(r["budget"] for r in res["rank"]), res["totals"]["rank_sum"],
                   round(sum(r["purchase"] for r in res["rank"]), 2), round(sum(r["free"] for r in res["rank"]), 2), None, None, None, None, None, None])
    det_h = ["姓名", "账号ID", "联系电话", "所属DA", "大区", "用户身份", "账号类型", "账号来源标签", "可用状态", "月度预算(元)", "本月花费(元)", "预算使用率%", "本年累计花费(元)", "最近使用日期"]
    det_r = [[d["name"], d["id"], d["phone"], d["da"], d["region"], d["identity"], d["account_type"], d["source_tag"], d["status"], d["budget"],
              d["cost"], _fmt(d["usage"]), d["ytd"], d["last_use"]] for d in res["detail"]]
    mr = _meta_rows(ds, "费用看板", month, f"DA={das or '全部'} 类型={account_types or '全部'} 来源={source_tag or '全部'} 身份={identity or '全部'}") + [("换算比例版本", res["overview"]["fx_version"])]
    return _respond(fmt, {f"{lvl}汇总": (rank_h, rank_r), "个人明细": (det_h, det_r)}, mr, f"费用看板_{month}")
