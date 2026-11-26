"""模拟乙方服务：按 docs/vendor-api-spec.md 实现 8 个接口(httpx.MockTransport)，含分页、统一响应包装、userRoleInfo。"""
from __future__ import annotations

import json
from collections import defaultdict

import httpx

from app.vendor import dataset as D

DA_CODES = ["BC", "LC", "GI", "HEMA", "OPH", "NS&RD", "INF", "IMMU", "NMA", "HSA", "MCE"]
KIND_TO_EVENT = {D.LOGIN: "login", D.PUBMED: "pubmed_search", D.OUTLINE: "outline_generate", D.SHARE: "library_share",
                 D.PPT_GEN: "ppt_generate", D.TWEET_GEN: "tweet_generate", D.POSTER_GEN: "poster_generate",
                 D.PPT_EXP: "ppt_export", D.TWEET_EXP: "tweet_export", D.POSTER_EXP: "poster_export"}
SUB_CODES = {"文献解读": "literature_interpretation", "学术创作Pro": "academic_creation_pro", "医学科普": "medical_popular_science",
             "专业学术": "professional_academic", "指南/政策解读": "guideline_policy"}


class FakeVendor:
    def __init__(self, status=None, das=None, accounts=None, type_history=None, quotas=None, usage=None, costs=None, roles=None):
        self.status = status or {"asOf": "2026-09-30 23:59:00", "dataStartDate": "2026-07-01", "updateFrequency": "T+1", "fxVersion": "v-test"}
        self.das = das or []
        self.accounts, self.type_history, self.quotas = accounts or [], type_history or [], quotas or []
        self.usage, self.costs, self.roles = usage or [], costs or [], roles or {}
        self.calls: list[tuple[str, int]] = []

    # —— 响应包装 / 分页 ——
    @staticmethod
    def ok(data):
        return httpx.Response(200, json={"code": 200, "success": True, "msg": "ok", "data": data})

    def paged(self, name, rows, body):
        page, size = int(body.get("page", 1)), min(int(body.get("pageSize", 1000)), 5000)
        self.calls.append((name, page))
        return self.ok({"total": len(rows), "page": page, "pageSize": size, "records": rows[(page - 1) * size: page * size]})

    @staticmethod
    def in_range(rows, body, key="date"):
        s, e = body.get("startDate"), body.get("endDate")
        return [r for r in rows if (not s or r[key] >= s) and (not e or r[key] <= e)]

    def handler(self, req: httpx.Request) -> httpx.Response:
        path = req.url.path.split("/api/shenbiDashboardApi")[-1]
        body = json.loads(req.content) if req.content else {}
        if path == "/dataStatus":
            return self.ok(self.status)
        if path == "/daList":
            return self.ok(self.das)
        if path == "/accountList":
            return self.paged(path, self.accounts, body)
        if path == "/accountTypeHistory":
            return self.paged(path, self.type_history, body)
        if path == "/quotaConfig":
            return self.ok(self.quotas)
        if path == "/usageDaily":
            return self.paged(path, self.in_range(self.usage, body), body)
        if path == "/costDaily":
            return self.paged(path, self.in_range(self.costs, body), body)
        if path == "/userRoleInfo":
            uid = req.url.params.get("userId")
            if uid not in self.roles:
                return httpx.Response(200, json={"code": 500, "success": False, "msg": "用户不存在", "data": None})
            return self.ok(self.roles[uid])
        return httpx.Response(404)

    def transport(self):
        return httpx.MockTransport(self.handler)


def from_dataset(ds: D.Dataset, roles=None) -> FakeVendor:
    """把内部 Dataset 序列化成乙方响应(用于「往返对账」：适配器 + 引擎的输出应与直接用 Dataset 完全一致)。"""
    das = [{"daId": i + 1, "daCode": c, "daName": c, "groupName": "", "isTest": False} for i, c in enumerate(DA_CODES)]
    cid = {c: i + 1 for i, c in enumerate(DA_CODES)}
    accounts = [{
        "accountId": a.id, "username": f"u{a.id}", "name": a.name, "phone": a.phone, "daId": cid.get(a.da), "region": a.region,
        "colleagueName": a.circle_lead, "identity": "customer" if a.identity == "客户" else "staff", "accountType": a.account_type,
        "sourceTag": a.source_tag, "accountStatus": "disabled" if a.status == "停用" else "enabled",
        "disabledAt": a.disabled_at.isoformat() + " 00:00:00" if a.disabled_at else None,
        "openedAt": a.opened_at.isoformat() + " 09:00:00" if a.opened_at else None,
        "firstLoginAt": a.first_login_at.isoformat() + " 09:30:00" if a.first_login_at else None,
        "isTestAccount": a.is_test, "isDaAccount": a.is_da, "remark": a.remark, "updatedAt": "2026-09-01 00:00:00",
    } for a in ds.accounts]
    agg = defaultdict(lambda: [0, 0])  # (acc, day, eventType, sub) -> [count, success]
    for e in ds.events:
        k = (e.account_id, e.day.isoformat(), KIND_TO_EVENT[e.kind], SUB_CODES.get(e.sub) if e.kind in D.GEN_KINDS else None)
        agg[k][0] += e.n
        if e.ok:
            agg[k][1] += e.n
    gen_types = {"ppt_generate", "tweet_generate", "poster_generate"}
    usage = [{"accountId": a, "date": d, "eventType": t, "subType": s, "count": c, "successCount": (ok if t in gen_types else None)}
             for (a, d, t, s), (c, ok) in sorted(agg.items())]
    costs = [{"accountId": c.account_id, "date": c.day.isoformat(), "feature": c.fn, "tokenCount": 0, "amountCny": c.amount, "fxVersion": ds.fx_version}
             for c in ds.costs]
    quotas = [{"daId": cid[da], "accountType": t, "quota": n, "effectiveFrom": eff.isoformat(), "note": None}
              for (da, t), hist in ds.quota_history.items() for eff, n in hist if da in cid]
    status = {"asOf": ds.as_of.strftime("%Y-%m-%d %H:%M:%S"), "dataStartDate": "2026-07-01", "updateFrequency": "T+1", "fxVersion": ds.fx_version}
    return FakeVendor(status, das, accounts, [], quotas, usage, costs, roles)
