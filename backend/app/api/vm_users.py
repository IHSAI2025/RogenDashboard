"""用户数据下钻接口(设计稿 features/user-drilldown)。"""
from __future__ import annotations

import datetime as dt

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from .. import config
from ..database import get_db
from ..insight import vm_users as VM
from ..services_scope import Scope, get_scope
from .insight import _meta_rows, _respond, load, meta_of
from .vm_common import Ctx, common

router = APIRouter(prefix="/api/vm/users", tags=["vm-users"])


@router.get("/list")
def list_users(state: str = "all", enabled: str | None = None, region: str | None = None, q: str | None = None,
               login_unused: bool = False, ctx: Ctx = Depends(common)):
    """每行一个账号；counts 为搜索/大区/可用状态作用后各使用状态的账号数(「全部」Tab 含停用账号，其使用状态为「—」)。"""
    res = VM.build(ctx, state, enabled, region, q, login_unused)
    return {**res, "meta": meta_of(ctx.ds)}


@router.get("/{account_id}/weekly")
def account_weekly(account_id: int, end: str, db: Session = Depends(get_db), scope: Scope = Depends(get_scope)):
    ds, idx = load(db)
    acc = next((a for a in ds.accounts if a.id == account_id), None)
    if acc is None or acc.is_test or (scope.managed is not None and acc.da not in scope.managed):
        raise HTTPException(404, "账号不存在或无权查看")
    try:
        e = dt.date.fromisoformat(end)
    except ValueError:
        raise HTTPException(400, "end 日期格式应为 YYYY-MM-DD")
    return VM.weekly(ds, idx, account_id, e)


COLS = [("账号ID", "id"), ("姓名", "name"), ("联系电话", "phone"), ("所属DA", "da"), ("大区", "region"), ("用户身份", "identity"),
        ("账号类型", "account_type"), ("账号来源标签", "source_tag"), ("可用状态", "status"), ("备注", "remark"),
        ("开通日期", "opened_at"), ("首次登录日期", "first_login_at"), ("停用日期", "disabled_at"),
        ("使用状态", "state"), ("本期登录", "logged_in_text"), ("活跃天数(分子)", "active_days"), ("统计周期天数(分母)", "period_days"), ("连续未使用天数", "idle_days"),
        ("最近使用日期", "last_use"), ("功能使用总次数", "ops_total"), ("PubMed检索次数", "pubmed"), ("大纲生成次数", "outline"),
        ("内容库分享次数", "share"), ("PPT功能使用次数", "ppt_ops"), ("推文功能使用次数", "tweet_ops"), ("海报功能使用次数", "poster_ops"),
        ("PPT生成次数", "gen_ppt"), ("推文生成次数", "gen_tweet"), ("海报生成次数", "gen_poster"), ("总生成次数", "gen_total"),
        ("最近成功生成日期", "last_gen"), ("PPT导出次数", "exp_ppt"), ("推文导出次数", "exp_tweet"), ("海报导出次数", "exp_poster"),
        ("总导出次数", "exp_total")]
POSTER_KEYS = {"poster_ops", "gen_poster", "exp_poster"}


@router.get("/export")
def export_users(state: str = "all", enabled: str | None = None, region: str | None = None, q: str | None = None,
                 login_unused: bool = False, fmt: str = "xlsx", ctx: Ctx = Depends(common)):
    """导出当前 Tab 与筛选范围内的账号，行集合与 /list 一致(不分页)。"""
    res = VM.build(ctx, state, enabled, region, q, login_unused)
    for r in res["rows"]:
        r["logged_in_text"] = "是" if r.get("logged_in") else "否"
    cols = [c for c in COLS if config.POSTER_LIVE or c[1] not in POSTER_KEYS]
    rows = [[r.get(k) if r.get(k) is not None else None for _, k in cols] for r in res["rows"]]
    tab = {"all": "全部", "活跃": "活跃用户", "休眠": "休眠用户", "沉默": "沉默用户"}.get(state, state)
    filt = (f"用户状态={tab} DA={ctx.f.das or '全部'} 类型={ctx.f.account_types or '全部'} 来源={ctx.f.source_tag or '全部'} "
            f"身份={ctx.f.identity or '全部'} 可用状态={enabled or '全部'} 大区={region or '全部'} 搜索={q or '无'} 登录未使用={'是(优先唤醒名单)' if login_unused else '否'}")
    mr = _meta_rows(ctx.ds, f"用户明细-{tab}", f"{ctx.start} ~ {ctx.end}", filt)
    return _respond(fmt, {f"{tab}": ([c for c, _ in cols], rows)}, mr, f"用户明细_{tab}_{ctx.start}_{ctx.end}")
