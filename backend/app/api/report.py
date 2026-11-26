"""PRD 4 导出报告(HTML)。数据范围由 Scope 服务端裁剪：DA 管理员只会得到授权 DA 的内容。"""
import datetime as dt
from urllib.parse import quote

from fastapi import APIRouter, Depends
from fastapi.responses import Response

from ..insight import report_html
from .vm_common import Ctx, common

router = APIRouter(prefix="/api/report", tags=["report"])


@router.get("/html")
def report_html_export(ctx: Ctx = Depends(common)):
    html = report_html.build(ctx, can_cost=ctx.scope.can_cost, full_phone=ctx.scope.is_super)
    name = f"神笔小罗分析报告_{ctx.start}_{ctx.end}.html"
    return Response(html, media_type="text/html; charset=utf-8",
                    headers={"Content-Disposition": f"attachment; filename*=UTF-8''{quote(name)}"})
