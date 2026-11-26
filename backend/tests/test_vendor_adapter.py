"""乙方接口适配器：用模拟乙方服务(tests/vendor_fake.py，按 docs/vendor-api-spec.md)验证
  1. 字段映射与分页（单元）
  2. 手算小数据集：PRD 口径逐条核对（使用/休眠/沉默/登录未使用/额度历史/月末账号类型/预算/花费/测试与非 DA 账号）
  3. 端到端 API（DATA_SOURCE=vendor）：角色经 userRoleInfo 解析、越权裁剪、X-Role 伪造无效
  4. 往返对账：本地数据集 → 乙方响应 → 适配器 → 引擎，结果与直接使用本地数据集完全一致
"""
import datetime as dt
import warnings
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from app import config
from app.api.vm_common import Ctx
from app.insight import cost as COST, vm_da, vm_overview as VO, vm_users as VU
from app.metrics import engine as E
from app.services_scope import Scope
from app.vendor import dataset as D, vendor_adapter as VA
from tests.vendor_fake import DA_CODES, FakeVendor, from_dataset

warnings.filterwarnings("ignore")
SRC = Path(__file__).resolve().parents[2] / "临时后台开发数据包" / "数据源"

DAS = [{"daId": 1, "daCode": "BC", "daName": "乳腺癌 BC", "groupName": "肿瘤", "isTest": False},
       {"daId": 2, "daCode": "LC", "daName": "肺癌 LC", "groupName": "肿瘤", "isTest": False},
       {"daId": 3, "daCode": "HEMA", "daName": "测试DA", "groupName": "肿瘤", "isTest": True}]


def acc(i, **kw):
    base = dict(accountId=i, username=f"u{i}", name=f"账号{i}", phone=f"1380000{i:04d}", daId=1, region="东区", colleagueName=None,
                identity="staff", accountType="PLUS", sourceTag="采购", accountStatus="enabled", disabledAt=None,
                openedAt="2026-07-01 09:00:00", firstLoginAt="2026-07-02 09:00:00", isTestAccount=False, isDaAccount=True,
                remark=None, updatedAt="2026-09-01 00:00:00")
    base.update(kw)
    return base


def ev(a, day, t, count=1, ok=None, sub=None):
    return {"accountId": a, "date": day, "eventType": t, "subType": sub, "count": count, "successCount": ok}


def small_vendor() -> FakeVendor:
    accounts = [
        acc(1),                                                                     # A 活跃(PubMed + 成功生成)
        acc(2, identity="customer", accountType="SUPER", sourceTag="免费"),          # B 只登录 → 休眠 + 登录未使用
        acc(3),                                                                     # C 7/15 后无使用 → 沉默 + 登录未使用
        acc(4, daId=2, openedAt="2026-09-10 09:00:00", firstLoginAt=None),          # D 开通不满 60 天 → 休眠
        acc(5, daId=2, identity="other", sourceTag="免费"),                          # E 失败生成+纯导出 → 休眠(identity=other→员工)
        acc(6, daId=2, accountType=None, accountStatus="disabled", disabledAt="2026-08-15 10:00:00"),  # F 停用、缺账号类型
        acc(7, isTestAccount=True),                                                 # G 测试账号 → 剔除
        acc(8, daId=3),                                                             # H 测试 DA → 剔除
        acc(9, daId=None, isDaAccount=False),                                       # I 非 DA 账号(核心业务剔除)
        acc(10, accountType="SUPER"),                                               # J 月中由 PLUS 改 SUPER
    ]
    usage = [
        ev(1, "2026-09-03", "login", 2), ev(1, "2026-09-03", "pubmed_search", 1),
        ev(1, "2026-09-05", "ppt_generate", 2, 1, "literature_interpretation"), ev(1, "2026-09-06", "ppt_export", 2),
        ev(2, "2026-09-12", "login", 3), ev(2, "2026-08-20", "pubmed_search", 1),
        ev(3, "2026-07-15", "pubmed_search", 1), ev(3, "2026-09-12", "login", 1),
        ev(5, "2026-08-25", "library_share", 1),
        ev(5, "2026-09-04", "tweet_generate", 3, 0, "medical_popular_science"), ev(5, "2026-09-04", "tweet_export", 1),
        ev(9, "2026-09-02", "outline_generate", 1),
        ev(10, "2026-09-08", "tweet_generate", 2, 2, "professional_academic"),
        ev(7, "2026-09-02", "pubmed_search", 5),                                     # 测试账号的事件不应进入统计
        ev(1, "2026-09-07", "future_event_x", 9),                                    # 未知事件类型：忽略
        ev(1, "2026-09-07", "pubmed_search", 0),                                     # count=0：忽略
    ]
    costs = [
        {"accountId": 1, "date": "2026-09-05", "feature": "ppt", "tokenCount": 1, "amountCny": 28.31, "fxVersion": "v-test"},
        {"accountId": 10, "date": "2026-09-08", "feature": "tweet", "tokenCount": 1, "amountCny": 7.92, "fxVersion": "v-test"},
        {"accountId": 5, "date": "2026-09-04", "feature": "other", "tokenCount": 1, "amountCny": 1.00, "fxVersion": "v-test"},
        {"accountId": 2, "date": "2026-08-20", "feature": "ppt", "tokenCount": 1, "amountCny": 5.55, "fxVersion": "v-test"},
        {"accountId": 7, "date": "2026-09-03", "feature": "ppt", "tokenCount": 1, "amountCny": 100.0, "fxVersion": "v-test"},
    ]
    history = [{"accountId": 10, "accountType": "PLUS", "effectiveFrom": "2026-07-01"}, {"accountId": 10, "accountType": "SUPER", "effectiveFrom": "2026-09-20"}]
    quotas = [{"daId": 1, "accountType": "PLUS", "quota": 10, "effectiveFrom": "2026-07-01", "note": None},
              {"daId": 1, "accountType": "PLUS", "quota": 12, "effectiveFrom": "2026-09-15", "note": "活动激励"},
              {"daId": 1, "accountType": "SUPER", "quota": 3, "effectiveFrom": "2026-07-01", "note": None},
              {"daId": 2, "accountType": "PLUS", "quota": 5, "effectiveFrom": "2026-07-01", "note": None}]
    roles = {"1": {"userId": 1, "userName": "超管", "roleCode": "super-admin", "daId": None, "managedDaIds": [1, 2]},
             "100": {"userId": 100, "userName": "王经理", "roleCode": "da-manager", "daId": 1, "managedDaIds": [1]},
             "200": {"userId": 200, "userName": "普通", "roleCode": "ordinary-user", "daId": 1, "managedDaIds": [1]}}
    return FakeVendor(das=DAS, accounts=accounts, type_history=history, quotas=quotas, usage=usage, costs=costs, roles=roles)


def client_for(fake: FakeVendor, page_size=2) -> VA.VendorClient:
    return VA.VendorClient(base_url="http://vendor.test", transport=fake.transport(), page_size=page_size)


def make_ctx(ds, start="2026-09-01", end="2026-09-30", scope=None, view="platform", das=None):
    s, e = dt.date.fromisoformat(start), min(dt.date.fromisoformat(end), ds.as_of.date())
    f = E.Filters(scope=view, das=das, allowed_das=(scope.managed if scope else None))
    return Ctx(ds, E.Index(ds), f, s, e, "mom", scope or Scope("super_admin", None), E.prev_range(s, e, "mom"))


# ─────────────────────────── 1. 映射与分页 ───────────────────────────
def test_adapter_pagination_and_mapping():
    fake = small_vendor()
    ds = VA.build_dataset_from_client(client_for(fake, page_size=2))
    assert len(ds.accounts) == 10                                    # 10 个账号分 5 页拉全
    assert [p for n, p in fake.calls if n == "/accountList"] == [1, 2, 3, 4, 5]
    assert ds.as_of == dt.datetime(2026, 9, 30, 23, 59) and ds.fx_version == "v-test" and ds.mock_fields == []
    a = {x.id: x for x in ds.accounts}
    assert a[1].da == "BC" and a[2].identity == "客户" and a[2].account_type == "SUPER" and a[2].source_tag == "免费"
    assert a[5].identity == "员工"                                    # identity=other 默认按员工
    assert a[6].status == "停用" and a[6].disabled_at == dt.date(2026, 8, 15) and a[6].account_type is None
    assert a[7].is_test and a[8].is_test                              # 测试账号 / 测试 DA
    assert a[9].da is None and a[9].is_da is False                    # daId=null → 非 DA 账号
    assert a[4].first_login_at is None and a[1].opened_at == dt.date(2026, 7, 1)
    assert a[10].type_history == [(dt.date(2026, 7, 1), "PLUS"), (dt.date(2026, 9, 20), "SUPER")]


def test_usage_mapping_splits_success_and_failure_and_ignores_unknown():
    ds = VA.build_dataset_from_client(client_for(small_vendor()))
    ppt = [e for e in ds.events if e.account_id == 1 and e.kind == D.PPT_GEN]
    assert sorted((e.n, e.ok) for e in ppt) == [(1, False), (1, True)]          # count=2、success=1 → 成功 1 + 失败 1
    assert all(e.sub == "文献解读" for e in ppt)
    tw = [e for e in ds.events if e.account_id == 5 and e.kind == D.TWEET_GEN]
    assert [(e.n, e.ok, e.sub) for e in tw] == [(3, False, "医学科普")]           # successCount=0 → 全部失败
    assert not [e for e in ds.events if e.n <= 0] and len(ds.events) == 15       # 未知类型、count=0 被忽略(18 行 → 15 个事件)


def test_other_identity_config(monkeypatch):
    monkeypatch.setattr(config, "VENDOR_OTHER_IDENTITY", "test")
    ds = VA.build_dataset_from_client(client_for(small_vendor()))
    assert {x.id: x for x in ds.accounts}[5].is_test is True                    # other 可配置为按测试账号剔除


def test_vendor_error_is_raised():
    fake = small_vendor()
    fake.status = None
    with pytest.raises(Exception):
        VA.build_dataset_from_client(client_for(fake))


# ─────────────────────────── 2. 手算口径 ───────────────────────────
@pytest.fixture(scope="module")
def ds():
    return VA.build_dataset_from_client(client_for(small_vendor()))


def test_states_and_login_unused(ds):
    ctx = make_ctx(ds)
    accts = E.select_accounts(ds, ctx.f)
    assert {a.id for a in accts} == {1, 2, 3, 4, 5, 6, 9, 10}                   # 测试账号 / 测试 DA 剔除
    b = E.period_bundle(ds, ctx.idx, accts, ctx.start, ctx.end)
    st = b["state"]
    assert (st[1], st[2], st[3], st[4], st[5], st[9], st[10]) == ("活跃", "休眠", "沉默", "休眠", "休眠", "活跃", "活跃")
    assert 6 not in st                                                          # F 已停用，不判状态、不进分母
    assert (b["n_valid"], b["n_active"], b["n_dormant"], b["n_silent"]) == (7, 3, 3, 1)
    assert b["n_valid"] == b["n_active"] + b["n_dormant"] + b["n_silent"]       # 三类互斥且相加 = 有效账号
    assert (b["n_login_unused_dormant"], b["n_login_unused_silent"]) == (1, 1)  # B、C


def test_period_metrics(ds):
    ctx = make_ctx(ds)
    b = E.period_bundle(ds, ctx.idx, E.select_accounts(ds, ctx.f), ctx.start, ctx.end)
    assert b["ops_total"] == 9                      # A: 1+2, E: 3(失败也算), I: 1, J: 2
    assert b["gen_total"] == 3 and b["gen"][D.PPT_GEN] == 1 and b["gen"][D.TWEET_GEN] == 2
    assert b["n_gen_accts"] == 2                    # A、J（E 只有失败生成）
    assert b["exp_total"] == 3 and b["n_exp_accts"] == 2
    snap = VO.snapshots(ctx)["period"]["current"]
    assert snap["activeRate"] == pytest.approx(3 / 7) and snap["perActiveFeature"] == pytest.approx(9 / 3)
    assert snap["perCapitaGeneration"] == pytest.approx(3 / 2) and snap["loginUnusedDormant"] == 1 and snap["loginUnusedSilent"] == 1


def test_active_days_and_idle_days(ds):
    ctx = make_ctx(ds)
    stats = E.stats(ctx.idx, [a for a in ds.accounts if a.id in (1, 2, 3)], ctx.start, ctx.end)
    assert len(stats[1].days) == 2                  # 9/3(PubMed)、9/5(成功生成)；登录和 9/6 的导出不计活跃天
    assert stats[2].last_use == dt.date(2026, 8, 20) and (ctx.end - stats[2].last_use).days == 41   # 连续未使用天数
    assert stats[3].last_use == dt.date(2026, 7, 15) and stats[3].logged_in


def test_stock_quota_history_and_import_rate(ds):
    ctx = make_ctx(ds)
    cum = VO.snapshots(ctx)["cumulative"]["all"]
    cur = cum["current"]
    assert cur["quota"] == {"total": 20, "plus": 17, "super": 3}                # 取 9/30 生效额度：BC PLUS 12(9/15 起) + LC 5 + BC SUPER 3
    assert cur["opened"]["total"] == 8                                          # 含后来停用的 F
    assert (cur["opened"]["plus"], cur["opened"]["super"]) == (5, 2)            # J 在 9/30 为 SUPER
    assert cur["importRate"] == pytest.approx(8 / 20)
    assert cur["valid"]["total"] == 7 and cur["activated"]["total"] == 7 and cur["activationRate"] == pytest.approx(7 / 8)
    prev_q = cum["previous"]["quota"]                                           # 对比周期 8/1~8/30 末(8/30)：BC PLUS 仍为 10
    assert prev_q == {"total": 18, "plus": 15, "super": 3}


def test_core_view_excludes_non_da(ds):
    core = VO.snapshots(make_ctx(ds, view="core"))["cumulative"]["core"]["current"]
    assert core["opened"]["total"] == 7                                         # 剔除非 DA 账号 I


def test_cost_budget_uses_month_end_type(ds):
    ctx = make_ctx(ds)
    res = COST.build(ds, ctx.idx, ctx.f, "2026-09", "da", True)
    o = res["overview"]
    assert (o["budget"]["n_plus"], o["budget"]["n_super"]) == (5, 2)            # J 取月末类型 SUPER
    assert o["budget"]["value"] == 5 * 600 + 2 * 1200                           # 停用于 8 月的 F 不在 9 月生效范围
    assert o["cost"]["value"] == pytest.approx(37.23)                           # 测试账号 G 的 100 元不计
    assert o["cost"]["purchase"] == pytest.approx(36.23) and o["cost"]["free"] == pytest.approx(1.00)
    assert o["cost"]["purchase"] + o["cost"]["free"] == pytest.approx(o["cost"]["value"])      # 验收 8
    assert res["totals"]["rank_sum"] == pytest.approx(o["cost"]["value"]) == pytest.approx(res["totals"]["detail_sum"])   # 验收 7
    assert o["usage"]["value"] == pytest.approx(37.23 / 5400 * 100)
    assert o["ytd"]["value"] == pytest.approx(42.78)                            # 7/1 起累计(含 8 月 B 的 5.55)
    prev = o["cost"]["prev"]
    assert prev == pytest.approx(5.55)                                          # 上月花费
    assert o["budget"]["prev"] == 4200                                          # 8 月：J 当时为 PLUS(600)，F 无类型不计预算


def test_unmapped_account_type_budget_is_pending(ds):
    ctx = make_ctx(ds, "2026-08-01", "2026-08-31")
    res = COST.build(ds, ctx.idx, ctx.f, "2026-08", "da", True)
    f_row = next(d for d in res["detail"] if d["id"] == 6)                       # F 在 8 月中停用，仍列出
    assert f_row["budget"] is None and f_row["account_type"] == "待映射" and f_row["status"] == "停用"


# ─────────────────────────── 3. 端到端 API（DATA_SOURCE=vendor） ───────────────────────────
@pytest.fixture()
def vendor_client(monkeypatch):
    from app.api import insight
    from app.main import app
    fake = small_vendor()
    monkeypatch.setattr(config, "DATA_SOURCE", "vendor")
    monkeypatch.setattr(config, "VENDOR_API_BASE_URL", "http://vendor.test")
    monkeypatch.setattr(VA, "_client_factory", lambda: client_for(fake, page_size=3))
    insight._cache.clear()
    VA._role_cache.clear()
    with TestClient(app) as c:
        yield c, fake
    insight._cache.clear()
    VA._role_cache.clear()


Q = "start=2026-09-01&end=2026-09-30"


def hdr(uid, **extra):
    return {"loggedInUserId": uid, **extra}


def test_api_requires_logged_in_user(vendor_client):
    c, _ = vendor_client
    assert c.get(f"/api/vm/overview/snapshots?{Q}").status_code == 401
    assert c.get(f"/api/vm/overview/snapshots?{Q}", headers=hdr("999")).status_code == 502      # userRoleInfo 报错 → 网关错误


def test_api_super_admin_sees_everything(vendor_client):
    c, fake = vendor_client
    d = c.get(f"/api/vm/overview/snapshots?{Q}", headers=hdr("1")).json()
    cur = d["period"]["current"]
    assert (cur["valid"], cur["active"], cur["dormant"], cur["silent"]) == (7, 3, 3, 1)
    meta = c.get("/api/insight/meta", headers=hdr("1")).json()
    assert meta["role"] == "super_admin" and meta["can_cost"] and meta["as_of"] == "2026-09-30 23:59" and meta["mock_fields"] == []
    assert any(p > 1 for n, p in fake.calls if n == "/usageDaily")                                # 分页确实发生


def test_api_da_manager_is_clipped_server_side_and_xrole_cannot_be_spoofed(vendor_client):
    c, _ = vendor_client
    spoof = hdr("100", **{"X-Role": "super_admin", "X-Managed-DAs": "BC,LC"})                    # 伪造头应被忽略
    d = c.get(f"/api/vm/overview/snapshots?{Q}&das=LC", headers=spoof).json()                    # 越权请求 LC
    assert d["period"]["current"]["valid"] == 0
    d = c.get(f"/api/vm/overview/snapshots?{Q}", headers=spoof).json()["period"]["current"]
    assert d["valid"] == 4 and d["active"] == 2                                                  # BC 内：A、B、C、J 有效；A、J 活跃
    users = c.get(f"/api/vm/users/list?{Q}&state=all", headers=spoof).json()["rows"]
    assert {r["da"] for r in users} == {"BC"} and all("*" in r["phone"] for r in users)          # 只见 BC；手机号脱敏
    cost = c.get("/api/vm/cost/summary?month=2026-09", headers=spoof).json()
    assert cost["level"] == "region" and [r["key"] for r in cost["rank"]] == ["东区"]            # DA 管理员按大区排行
    o = cost["overview"]
    assert (o["nPlus"], o["nSuper"], o["budget"]) == (2, 2, 600 + 1200 + 600 + 1200)             # A、C=PLUS；B、J(月末)=SUPER
    assert o["spend"] == pytest.approx(28.31 + 7.92) and o["prevBudget"] == 3000                 # 8 月 J 仍为 PLUS
    assert c.get(f"/api/report/html?{Q}", headers=spoof).text.count("肺癌 LC") == 0
    assert c.get("/api/insight/export/users?" + Q + "&das=LC&fmt=csv", headers=spoof).status_code == 200


def test_api_ordinary_user_has_no_cost(vendor_client):
    c, _ = vendor_client
    assert c.get("/api/vm/cost/summary?month=2026-09", headers=hdr("200")).status_code == 403
    assert c.get("/api/insight/meta", headers=hdr("200")).json()["can_cost"] is False


def test_api_users_list_login_unused_filter(vendor_client):
    c, _ = vendor_client
    r = c.get(f"/api/vm/users/list?{Q}&state=休眠&login_unused=true", headers=hdr("1")).json()
    assert [x["id"] for x in r["rows"]] == [2] and r["rows"][0]["logged_in"] is True
    r = c.get(f"/api/vm/users/list?{Q}&state=沉默&login_unused=true", headers=hdr("1")).json()
    assert [x["id"] for x in r["rows"]] == [3]
    assert r["loginUnusedCounts"] == {"休眠": 1, "沉默": 1}
    # 「全部」Tab + 登录未使用：只有休眠/沉默里登录过的账号(B、C)；活跃的 A 登录过但已使用，不是「登录未使用」
    r = c.get(f"/api/vm/users/list?{Q}&state=all&login_unused=true", headers=hdr("1")).json()
    assert sorted(x["id"] for x in r["rows"]) == [2, 3]


def test_api_cost_super_admin_matches_engine(vendor_client):
    c, _ = vendor_client
    d = c.get("/api/vm/cost/summary?month=2026-09", headers=hdr("1")).json()
    o = d["overview"]
    assert d["level"] == "da" and o["spend"] == pytest.approx(37.23) and o["budget"] == 5400
    assert o["purchaseSpend"] + o["freeSpend"] == pytest.approx(o["spend"])                       # 验收 8
    assert o["rate"] == pytest.approx(37.23 / 5400) and o["rateNum"] == pytest.approx(37.23) and o["rateDen"] == 5400
    assert o["ytd"] == pytest.approx(42.78) and o["prevSpend"] == pytest.approx(5.55)


# ─────────────────────────── 4. 往返对账 ───────────────────────────
pytestmark_roundtrip = pytest.mark.skipif(not SRC.exists(), reason="无数据源目录")


@pytestmark_roundtrip
def test_roundtrip_local_dataset_equals_vendor_pipeline():
    """本地数据集(真实周报 + mock) → 序列化为乙方响应 → 适配器 → 引擎，输出必须与直接使用本地数据集逐项一致。"""
    from app.api.insight import load
    from app.database import SessionLocal
    from app.main import app
    from scripts import seed_local
    with TestClient(app):
        seed_local.main(SRC)
    db = SessionLocal()
    try:
        local, _ = load(db)
    finally:
        db.close()
    # 乙方侧不存在「待映射」额度：把本地 mock 额度里的待映射项去掉，两侧口径一致
    local.quotas = {k: v for k, v in local.quotas.items() if k[0] in DA_CODES}
    local.quota_history = {k: v for k, v in local.quota_history.items() if k[0] in DA_CODES}
    vendor = VA.build_dataset_from_client(client_for(from_dataset(local), page_size=1000))
    assert len(vendor.accounts) == len(local.accounts)

    for scope in (Scope("super_admin", None), Scope("da_admin", ["BC"])):
        for (s, e) in (("2026-08-01", "2026-08-31"), ("2026-07-13", "2026-08-09")):
            a, b = make_ctx(local, s, e, scope), make_ctx(vendor, s, e, scope)
            assert VO.snapshots(a) == VO.snapshots(b), (scope.role, s, e, "overview")
            assert VO.trend(a, "month") == VO.trend(b, "month")
            assert VO.trend(a, "week") == VO.trend(b, "week")
            for dim in ("da", "region"):
                assert vm_da.groups(a, dim) == vm_da.groups(b, dim), (scope.role, dim)
            ra, rb = VU.build(a, "all"), VU.build(b, "all")
            assert ra["rows"] == rb["rows"] and ra["counts"] == rb["counts"]
        a, b = make_ctx(local, "2026-08-01", "2026-08-31", scope), make_ctx(vendor, "2026-08-01", "2026-08-31", scope)
        ca = COST.build(local, a.idx, a.f, "2026-08", "da", True)
        cb = COST.build(vendor, b.idx, b.f, "2026-08", "da", True)
        assert ca["overview"] == cb["overview"] and ca["totals"] == cb["totals"]
        assert ca["rank"] == cb["rank"] and ca["detail"] == cb["detail"]
