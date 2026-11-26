"""乙方(商汤)接口适配器：把 docs/vendor-api-spec.md 的接口返回转成 Dataset(指标引擎唯一依赖的契约)。

只做「字段映射 + 分页拉取」，不计算任何指标；活跃/休眠/沉默、各种率等全部由 metrics/engine.py 计算。
DATA_SOURCE=vendor 时由 api/insight.load() 调用；角色由 services_scope 通过 userRoleInfo 解析。
"""
from __future__ import annotations

import datetime as dt
import time
from collections import defaultdict

import httpx

from .. import config
from . import dataset as D

DASHBOARD_API = "/api/dashboard"  # 乙方提供：dataStatus / usageDaily / costDaily

IDENTITY = {"customer": "客户", "staff": "员工"}
SUB_NAMES = {
    "literature_interpretation": "文献解读", "academic_creation_pro": "学术创作Pro",
    "medical_popular_science": "医学科普", "professional_academic": "专业学术", "guideline_policy": "指南/政策解读",
}
# eventType → (引擎事件类型, 是否生成类)
EVENT_KIND = {
    "login": (D.LOGIN, False), "pubmed_search": (D.PUBMED, False), "outline_generate": (D.OUTLINE, False), "library_share": (D.SHARE, False),
    "ppt_generate": (D.PPT_GEN, True), "article_generate": (D.TWEET_GEN, True), "poster_generate": (D.POSTER_GEN, True),
    "ppt_export": (D.PPT_EXP, False), "article_export": (D.TWEET_EXP, False), "poster_export": (D.POSTER_EXP, False),
}
# costDaily.feature → 引擎功能名(推文 article → tweet)；未知功能归 other
FEATURE = {"ppt": "ppt", "article": "tweet", "other": "other"}
ROLE_MAP = {"super-admin": "super_admin", "da-manager": "da_admin", "ordinary-user": "other"}


class VendorError(RuntimeError):
    pass


class VendorClient:
    """薄封装：统一响应 {code, message, data}(成功 code=0) 校验 + 分页。transport 可注入(测试用 httpx.MockTransport)。"""

    def __init__(self, base_url: str | None = None, token: str | None = None, transport: httpx.BaseTransport | None = None,
                 page_size: int | None = None, timeout: float | None = None):
        headers = {"Content-Type": "application/json"}
        tok = token if token is not None else config.VENDOR_API_TOKEN
        if tok:
            headers["Authorization"] = f"Bearer {tok}"
        self.page_size = min(page_size or config.VENDOR_PAGE_SIZE, 5000)
        self.http = httpx.Client(base_url=base_url or config.VENDOR_API_BASE_URL, headers=headers,
                                 timeout=timeout or config.VENDOR_TIMEOUT, transport=transport)

    def _unwrap(self, r: httpx.Response):
        if r.status_code != 200:
            raise VendorError(f"乙方接口 HTTP {r.status_code}: {r.text[:200]}")
        body = r.json()
        # 乙方定稿：成功 code=0；门户接口文档未到，兼容 200。失败信息取 message(旧草案为 msg)
        if body.get("code") not in (0, 200) or body.get("success") is False:
            raise VendorError(f"乙方接口失败: code={body.get('code')} message={body.get('message') or body.get('msg')}")
        return body.get("data")

    def get(self, path: str, params: dict | None = None, headers: dict | None = None):
        return self._unwrap(self.http.get(path, params=params, headers=headers))

    def post(self, path: str, body: dict):
        return self._unwrap(self.http.post(path, json=body))

    def pages(self, path: str, body: dict) -> list[dict]:
        """拉取全部分页(records/total)。"""
        out, page = [], 1
        while True:
            data = self.post(path, {**body, "page": page, "pageSize": self.page_size})
            recs = data.get("records") or []
            out.extend(recs)
            if not recs or len(out) >= (data.get("total") or 0):
                return out
            page += 1


_client_factory = VendorClient  # 测试里替换为带 MockTransport 的工厂


def make_client() -> VendorClient:
    if not config.VENDOR_API_BASE_URL:
        raise VendorError("未配置 VENDOR_API_BASE_URL")
    return _client_factory()


def portal(path: str) -> str:
    return config.VENDOR_PORTAL_API_PREFIX.rstrip("/") + path


def _d(s: str | None) -> dt.date | None:
    return dt.date.fromisoformat(s[:10]) if s else None


def _dt(s: str) -> dt.datetime:
    return dt.datetime.strptime(s[:19].replace("T", " "), "%Y-%m-%d %H:%M:%S")


def da_maps(client: VendorClient) -> tuple[dict[int, str | None], set[int]]:
    """daId -> daCode(无法识别为 None)、测试 DA 的 id 集合。"""
    code, tests = {}, set()
    for x in client.get(portal("/daList")) or []:
        code[x["daId"]] = x.get("daCode")
        if x.get("isTest"):
            tests.add(x["daId"])
    return code, tests


def map_account(x: dict, code: dict, test_das: set, other_identity: str | None = None) -> D.AccountRec:
    ident_raw = x.get("identity")
    other = (other_identity or config.VENDOR_OTHER_IDENTITY)
    identity = IDENTITY.get(ident_raw) or ("客户" if other == "customer" else "员工")
    daid = x.get("daId")
    da = code.get(daid) if daid is not None else None
    is_test = bool(x.get("isTestAccount")) or daid in test_das or (ident_raw not in IDENTITY and other == "test")
    return D.AccountRec(
        id=x["accountId"], name=x.get("name") or x.get("username") or str(x["accountId"]), phone=x.get("phone") or "",
        da=da, region=x.get("region"), circle_lead=x.get("colleagueName"), identity=identity,
        account_type=x.get("accountType") if x.get("accountType") in ("PLUS", "SUPER") else None,
        source_tag=x.get("sourceTag") if x.get("sourceTag") in ("采购", "免费") else None,
        status="停用" if x.get("accountStatus") == "disabled" else "正常",
        opened_at=_d(x.get("openedAt")), disabled_at=_d(x.get("disabledAt")), first_login_at=_d(x.get("firstLoginAt")),
        is_test=is_test, is_da=bool(x.get("isDaAccount", True)) and da is not None, remark=x.get("remark"),
    )


def map_usage(rows: list[dict]) -> list[D.Event]:
    """usageDaily → 引擎事件。生成类拆成「成功」「失败/取消」两条：count=发起次数，successCount=成功次数。"""
    events: list[D.Event] = []
    for r in rows:
        spec = EVENT_KIND.get(r.get("eventType"))
        if spec is None:
            continue  # 未知事件类型忽略(乙方新增事件不应拖垮看板)
        kind, is_gen = spec
        day, n = _d(r["date"]), int(r.get("count") or 0)
        if n <= 0:
            continue
        if not is_gen:
            events.append(D.Event(r["accountId"], day, kind, n))
            continue
        sub = SUB_NAMES.get(r.get("subType"), r.get("subType"))
        ok = min(int(r.get("successCount") if r.get("successCount") is not None else n), n)
        if ok:
            events.append(D.Event(r["accountId"], day, kind, ok, True, sub))
        if n - ok:
            events.append(D.Event(r["accountId"], day, kind, n - ok, False, sub))
    return events


def map_costs(rows: list[dict], rate: float | None = None) -> list[D.CostRec]:
    """costDaily → CostRec。乙方分币种返回，人民币金额 = amountCny + amountUsd × 汇率(config.USD_CNY_RATE)。
    乙方保证同一笔费用只计入一个币种；缺失的币种字段按 0 处理。"""
    fx = config.USD_CNY_RATE if rate is None else rate
    return [D.CostRec(r["accountId"], _d(r["date"]), float(r.get("amountCny") or 0) + float(r.get("amountUsd") or 0) * fx,
                      FEATURE.get(r.get("feature"), "other")) for r in rows]


def build_dataset_from_client(client: VendorClient) -> D.Dataset:
    status = client.get(DASHBOARD_API + "/dataStatus")
    as_of = _dt(status["asOf"])
    start = status.get("dataStartDate") or config.PLATFORM_LAUNCH_DATE
    rng = {"startDate": start, "endDate": as_of.date().isoformat()}

    code, test_das = da_maps(client)
    accounts = [map_account(x, code, test_das) for x in client.pages(portal("/accountList"), {})]
    by_id = {a.id: a for a in accounts}

    for h in client.pages(portal("/accountTypeHistory"), {"startDate": start, "endDate": rng["endDate"]}):
        a = by_id.get(h["accountId"])
        if a is not None and h.get("accountType") in ("PLUS", "SUPER"):
            a.type_history.append((_d(h["effectiveFrom"]), h["accountType"]))
    for a in accounts:
        a.type_history.sort()

    events = map_usage(client.pages(DASHBOARD_API + "/usageDaily", rng))
    costs = map_costs(client.pages(DASHBOARD_API + "/costDaily", rng))

    hist: dict[tuple[str, str], list] = defaultdict(list)
    for q in client.get(portal("/quotaConfig")) or []:
        da = code.get(q["daId"])
        if da and q.get("accountType") in ("PLUS", "SUPER"):
            hist[(da, q["accountType"])].append((_d(q["effectiveFrom"]), int(q["quota"])))
    quotas = {}
    for key, lst in hist.items():
        lst.sort()
        quotas[key] = [n for eff, n in lst if eff <= as_of.date()][-1] if any(eff <= as_of.date() for eff, _ in lst) else lst[0][1]

    return D.Dataset(accounts=accounts, events=events, costs=costs, quotas=quotas, as_of=as_of,
                     fx_version=f"usd-cny-{config.USD_CNY_RATE:g}", mock_fields=[], quota_history=dict(hist))


def build_dataset_from_vendor() -> D.Dataset:
    return build_dataset_from_client(make_client())


# ───────── 角色 ─────────
_role_cache: dict[str, tuple[float, dict]] = {}


def resolve_role(user_id: str) -> dict:
    """userRoleInfo → {'role': super_admin|da_admin|other, 'managed': [daCode] | None}。60 秒缓存。"""
    hit = _role_cache.get(user_id)
    if hit and time.time() - hit[0] < 60:
        return hit[1]
    c = make_client()
    info = c.get(portal("/userRoleInfo"), {"userId": user_id}, headers={"loggedInUserId": user_id})
    role = ROLE_MAP.get(info.get("roleCode"), "other")
    code, _ = da_maps(c)
    managed = None if role == "super_admin" else [code[i] for i in (info.get("managedDaIds") or []) if code.get(i)]
    res = {"role": role, "managed": managed, "name": info.get("userName")}
    _role_cache[user_id] = (time.time(), res)
    return res
