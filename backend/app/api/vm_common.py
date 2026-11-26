"""给设计稿前端用的「view-model」接口的公共依赖。

约定（所有 /api/vm/* 接口）：
- 查询参数：start,end(YYYY-MM-DD) mode(mom|period) das(DA编码,逗号分隔;"__none__"=未选择) account_types source_tag identity view(platform|core)
- 比率一律输出 0~1 的小数(前端 fmtPct 会 ×100)，不是百分数；分母为 0 / 无可比周期输出 null
- 权限：Scope 由请求头决定，所有账号集合都经 engine.select_accounts 按 Scope.managed 服务端裁剪
- 指标口径只用 metrics/engine.py，不要在这里另写一套
"""
from __future__ import annotations

import datetime as dt
from dataclasses import dataclass

from fastapi import Depends, HTTPException
from sqlalchemy.orm import Session

from ..database import get_db
from ..metrics import engine as E
from ..metrics.engine import Filters
from ..services_scope import Scope, get_scope
from .insight import load, make_filters


@dataclass
class Ctx:
    ds: object
    idx: object
    f: Filters
    start: dt.date
    end: dt.date          # 已按数据截至日截断
    mode: str
    scope: Scope
    prev: tuple | None    # 对比周期 (start, end)，数据不完整为 None


def _d(v: str, name: str) -> dt.date:
    try:
        return dt.date.fromisoformat(v)
    except ValueError:
        raise HTTPException(400, f"{name} 日期格式应为 YYYY-MM-DD")


def common(start: str, end: str, mode: str = "mom", das: str | None = None, account_types: str | None = None,
           source_tag: str | None = None, identity: str | None = None, view: str = "platform",
           db: Session = Depends(get_db), scope: Scope = Depends(get_scope)) -> Ctx:
    ds, idx = load(db)
    f = make_filters(scope, das, account_types, source_tag, identity, view)
    s, e = _d(start, "start"), _d(end, "end")
    e = min(e, idx.as_of_day)
    return Ctx(ds, idx, f, s, e, mode, scope, E.prev_range(s, e, mode))


def ratio(num, den):
    """0~1 小数，分母为 0 返回 None"""
    return (num / den) if den else None
