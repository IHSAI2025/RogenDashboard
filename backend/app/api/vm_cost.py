"""费用看板 view-model 接口（设计稿 features/cost）。口径全部来自 insight/cost.py（PRD 5.x），这里只做形状转换：
比率 0~1 小数，环比 = (cur-prev)/prev 的小数（比率类为差值小数，单位 pp 由前端 ×100 展示）。
权限：仅 super_admin / da_admin；DA 范围由 Scope.managed 服务端裁剪；手机号仅超管明文。"""
from __future__ import annotations

import datetime as dt

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from ..database import get_db
from ..insight import cost as COST
from ..services_scope import Scope, get_scope
from .insight import load, make_filters, meta_of

router = APIRouter(prefix="/api/vm/cost", tags=["vm-cost"])

UNMAPPED_KEY = "__unmapped__"
UNMAPPED = "待映射"


def _need(scope: Scope):
    if not scope.can_cost:
        raise HTTPException(403, "无权查看费用看板")


def _r(v):  # 百分数 -> 小数
    return None if v is None else v / 100.0


def _check_month(month: str):
    try:
        dt.datetime.strptime(month, "%Y-%m")
    except ValueError:
        raise HTTPException(400, "month 格式应为 YYYY-MM")


def shape_summary(res: dict, daily: dict, level: str, meta: dict) -> dict:
    o = res["overview"]
    cost, bud, use = o["cost"], o["budget"], o["usage"]
    rank = []
    for r in res["rank"]:
        key = r["key"]
        unmapped = key == UNMAPPED
        rank.append({
            "key": UNMAPPED_KEY if (unmapped and level == "da") else key, "label": key, "unmapped": unmapped,
            "accountCount": r["n_accounts"], "budget": r["budget"], "spend": r["cost"], "purchaseSpend": r["purchase"],
            "freeSpend": r["free"], "rate": _r(r["usage"]), "rateNum": r["usage_num"], "rateDen": r["usage_den"],
            "perCapita": r["per_capita"], "spenders": r["paying"], "mom": _r(r["mom"]),
        })
    persons = []
    for d in res["detail"]:
        persons.append({
            "id": str(d["id"]), "name": d["name"], "phone": d["phone"], "daId": None if d["da"] == UNMAPPED else d["da"],
            "region": d["region"], "identity": d["identity"], "accountType": None if d["account_type"] == UNMAPPED else d["account_type"],
            "source": d["source_tag"], "enabled": d["status"] != "停用", "budget": d["budget"], "spend": d["cost"],
            "rate": _r(d["usage"]), "ytd": d["ytd"], "lastUsedDate": d["last_use"],
        })
    pts = []
    for p in daily["points"]:
        day = int(p["day"])
        has = p["cum"] is not None
        pts.append({"day": day, "date": f"{res['month']}-{day:02d}", "purchase": p["purchase"], "free": p["free"],
                    "total": round(p["purchase"] + p["free"], 2) if has else None, "cumulative": p["cum"]})
    return {
        "month": res["month"], "partial": res["partial"], "end": res["end"], "level": level,
        "overview": {
            "spend": cost["value"], "prevSpend": cost["prev"], "spendMom": _r(cost["mom"]),
            "purchaseSpend": cost["purchase"], "freeSpend": cost["free"], "unlabeledSpend": cost["unlabeled"],
            "budget": bud["value"], "prevBudget": bud["prev"], "budgetMom": _r(bud["mom"]),
            "nPlus": bud["n_plus"], "nSuper": bud["n_super"], "unmappedBudget": bud["unmapped"],
            "rate": _r(use["value"]), "prevRate": _r(use["prev"]), "rateDiff": _r(use["mom"]), "rateNum": use["num"], "rateDen": use["den"],
            "ytd": o["ytd"]["value"], "ytdPurchase": o["ytd"]["purchase"], "ytdFree": o["ytd"]["free"],
            "accountCount": len(res["detail"]), "spenders": sum(1 for d in res["detail"] if d["cost"] > 0),
            "asOf": o["as_of"], "fxVersion": o["fx_version"],
        },
        "rank": rank, "persons": persons,
        "daily": {"points": pts, "budget": daily["budget"]},
        "totals": res["totals"], "meta": meta,
    }


@router.get("/summary")
def summary(month: str, das: str | None = None, account_types: str | None = None, source_tag: str | None = None,
            identity: str | None = None, db: Session = Depends(get_db), scope: Scope = Depends(get_scope)):
    _need(scope)
    _check_month(month)
    ds, idx = load(db)
    f = make_filters(scope, das, account_types, source_tag, identity)
    res = COST.build(ds, idx, f, month, scope.level, scope.is_super)
    daily = COST.daily(ds, idx, f, month)
    return shape_summary(res, daily, scope.level, meta_of(ds))


@router.get("/account/{account_id}")
def account(account_id: int, month: str, db: Session = Depends(get_db), scope: Scope = Depends(get_scope)):
    _need(scope)
    _check_month(month)
    ds, idx = load(db)
    acc = next((a for a in ds.accounts if a.id == account_id), None)
    if acc is None or acc.is_test or (scope.managed is not None and acc.da not in scope.managed):
        raise HTTPException(404, "账号不存在或无权查看")
    d = COST.account_detail(ds, idx, account_id, month)
    return {
        "id": str(d["id"]), "budget": d["budget"], "accountType": d["account_type"],
        "months": [{"key": m["month"], "label": m["month"][2:].replace("-", "/"), "spend": m["cost"]} for m in d["months"]],
        "byFunction": [{"key": k, "label": p["name"], "amount": p["value"], "ratio": _r(p["ratio"])}
                       for k, p in zip(("ppt", "tweet", "poster", "other"), d["by_function"])],
        "note": d["by_function_note"],
    }
