"""全景看板 view-model 接口（设计稿 features/overview 使用）。"""
from __future__ import annotations

import json

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from .. import models
from ..database import get_db
from ..insight import vm_overview as VM
from .vm_common import Ctx, common

router = APIRouter(prefix="/api/vm/overview", tags=["vm-overview"])


@router.get("/snapshots")
def snapshots(ctx: Ctx = Depends(common)):
    """累计存量(全平台/核心业务)、当期快照(当期+对比期)、账号分布、功能使用分布。"""
    return VM.snapshots(ctx)


@router.get("/trend")
def trend(granularity: str = "month", ctx: Ctx = Depends(common)):
    if granularity not in ("week", "month", "year"):
        raise HTTPException(400, "granularity 应为 week/month/year")
    return VM.trend(ctx, granularity)


def _key(ctx: Ctx, scope: str, p: dict) -> str:
    f = ctx.f
    return "vm|" + "|".join(str(x) for x in (scope, ctx.scope.role, ",".join(ctx.scope.managed or []), ctx.start, ctx.end, ctx.mode,
                                             f.das, f.account_types, f.source_tag, f.identity))


@router.get("/insight")
def insight(scope: str = "overview", ctx: Ctx = Depends(common), db: Session = Depends(get_db)):
    """AI 诊断及洞察：规则生成的四段事实陈述；若超管编辑过则返回编辑版本。仅超管可编辑。"""
    key = _key(ctx, scope, {})
    gen = VM.insight_sections(ctx, scope)
    note = db.query(models.InsightNote).filter_by(key=key).one_or_none()
    edited = None
    if note:
        try:
            edited = json.loads(note.content)
        except ValueError:
            edited = None
    return {"key": key, "sections": edited or gen, "generated": gen, "edited": edited is not None, "editable": ctx.scope.is_super}


@router.put("/insight")
def save_insight(payload: dict, ctx: Ctx = Depends(common), scope: str = "overview", db: Session = Depends(get_db)):
    if not ctx.scope.is_super:
        raise HTTPException(403, "仅超级管理员可编辑洞察")
    key = _key(ctx, scope, {})
    sections = payload.get("sections")
    note = db.query(models.InsightNote).filter_by(key=key).one_or_none()
    if not sections:  # 清空 = 恢复规则文案
        if note:
            db.delete(note)
    elif note:
        note.content = json.dumps(sections, ensure_ascii=False)
    else:
        db.add(models.InsightNote(key=key, content=json.dumps(sections, ensure_ascii=False)))
    db.commit()
    return {"ok": True}
