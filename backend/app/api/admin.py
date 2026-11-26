from __future__ import annotations

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from .. import models, schemas
from ..database import get_db
from ..etl.da_dict import ALL_DAS
from ..services_scope import Scope, get_scope

router = APIRouter(prefix="/api/admin", tags=["admin"])


def _d(obj) -> dict:
    return {c.name: getattr(obj, c.name) for c in obj.__table__.columns}


def _super(scope: Scope):
    if not scope.is_super:
        raise HTTPException(403, "仅超级管理员可操作")


@router.get("/exclusions")
def list_exclusions(db: Session = Depends(get_db), scope: Scope = Depends(get_scope)):
    _super(scope)
    return [_d(r) for r in db.query(models.ExclusionRule).all()]


@router.post("/exclusions")
def create_exclusion(p: schemas.ExclusionRuleIn, db: Session = Depends(get_db), scope: Scope = Depends(get_scope)):
    _super(scope)
    r = models.ExclusionRule(**p.model_dump())
    db.add(r); db.commit(); db.refresh(r)
    return _d(r)


@router.delete("/exclusions/{rule_id}")
def delete_exclusion(rule_id: int, db: Session = Depends(get_db), scope: Scope = Depends(get_scope)):
    _super(scope)
    r = db.get(models.ExclusionRule, rule_id)
    if r is None:
        raise HTTPException(404, "rule not found")
    db.delete(r); db.commit()
    return {"ok": True}


@router.get("/quotas")
def list_quotas(db: Session = Depends(get_db), scope: Scope = Depends(get_scope)):
    _super(scope)
    return [_d(q) for q in db.query(models.QuotaConfig).order_by(models.QuotaConfig.da_code, models.QuotaConfig.effective_from)]


@router.post("/quotas")
def create_quota(p: schemas.QuotaIn, db: Session = Depends(get_db), scope: Scope = Depends(get_scope)):
    _super(scope)
    if p.da_code not in ALL_DAS or p.account_type not in ("PLUS", "SUPER"):
        raise HTTPException(400, "da_code 须在 DA 字典内，account_type 为 PLUS/SUPER")
    q = models.QuotaConfig(**p.model_dump())
    db.add(q); db.commit(); db.refresh(q)
    return _d(q)


@router.delete("/quotas/{qid}")
def delete_quota(qid: int, db: Session = Depends(get_db), scope: Scope = Depends(get_scope)):
    _super(scope)
    q = db.get(models.QuotaConfig, qid)
    if q is None:
        raise HTTPException(404, "not found")
    db.delete(q); db.commit()
    return {"ok": True}


@router.put("/accounts/{account_id}")
def update_account_attrs(account_id: int, p: schemas.AccountAttrIn, db: Session = Depends(get_db), scope: Scope = Depends(get_scope)):
    """补录账号来源标签/可用状态/开通与首次登录日期(商汤接口接入前的人工入口)。"""
    _super(scope)
    a = db.get(models.Account, account_id)
    if a is None:
        raise HTTPException(404, "account not found")
    for k, v in p.model_dump(exclude_unset=True).items():
        setattr(a, k, v)
    db.commit()
    return _d(a)
