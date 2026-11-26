"""全景看板 view-model 接口：与 /api/insight/overview 口径一致、权限裁剪、比率 0~1、洞察编辑。"""
import warnings
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

warnings.filterwarnings("ignore")
SRC = Path(__file__).resolve().parents[2] / "临时后台开发数据包" / "数据源"
pytestmark = pytest.mark.skipif(not SRC.exists(), reason="无数据源目录")

Q = "start=2026-08-01&end=2026-08-31"
BC = {"X-Role": "da_admin", "X-Managed-DAs": "BC"}


@pytest.fixture(scope="module")
def client():
    from app.main import app
    from scripts import seed_local
    with TestClient(app):
        seed_local.main(SRC)
        yield TestClient(app)


def snap(c, qs="", headers=None, base=Q):
    r = c.get(f"/api/vm/overview/snapshots?{base}{qs}", headers=headers or {})
    assert r.status_code == 200, r.text
    return r.json()


def test_active_matches_insight_overview(client):
    vm = snap(client)["period"]["current"]
    ov = client.get(f"/api/insight/overview?{Q}").json()["current"]
    assert vm["active"] == ov["active"]["count"]["value"]
    assert vm["valid"] == ov["active"]["rate"]["den"]
    assert vm["dormant"] == ov["idle"]["dormant_count"]["value"]
    assert vm["silent"] == ov["idle"]["silent_count"]["value"]
    assert vm["featureTotal"] == ov["efficiency"]["ops"]["value"]
    assert vm["generation"]["total"] == ov["generation"]["gen"]["value"]
    # 活跃 + 休眠 + 沉默 = 有效账号
    assert vm["active"] + vm["dormant"] + vm["silent"] == vm["valid"]


def test_ratios_are_zero_to_one(client):
    d = snap(client)
    cur = d["period"]["current"]
    cum = d["cumulative"]["all"]["current"]
    for v in (cur["activeRate"], cur["dormantRate"], cur["silentRate"], cum["activationRate"], cum["importRate"]):
        assert v is None or 0 <= v <= 1
    assert abs(cur["activeRate"] - cur["active"] / cur["valid"]) < 1e-12


def test_import_rate_is_opened_over_quota(client):
    c = snap(client)["cumulative"]["all"]["current"]
    assert c["quota"]["total"] == c["quota"]["plus"] + c["quota"]["super"]
    assert c["importRate"] == pytest.approx(c["opened"]["total"] / c["quota"]["total"])
    # 开通账号含后来停用：>= 有效账号
    assert c["opened"]["total"] >= c["valid"]["total"]


def test_core_view_excludes_non_da(client):
    d = snap(client)["cumulative"]
    assert d["core"]["current"]["opened"]["total"] < d["all"]["current"]["opened"]["total"]


def test_previous_period_same_day(client):
    r = snap(client)["range"]
    assert r["end"] == "2026-08-23" and r["prev"] == ["2026-07-01", "2026-07-23"]
    # 对比周期早于上线日 → 无环比
    d = snap(client, base="start=2026-07-01&end=2026-07-31")
    assert d["period"]["previous"] is None and d["cumulative"]["all"]["previous"] is None


def test_da_admin_is_clipped_server_side(client):
    mine = snap(client, headers=BC)["cumulative"]["all"]["current"]["opened"]["total"]
    sup_bc = snap(client, "&das=BC")["cumulative"]["all"]["current"]["opened"]["total"]
    assert mine == sup_bc and mine > 0
    # 越权参数：请求 LC，只能得到 BC∩LC = 空
    other = snap(client, "&das=LC", headers=BC)
    assert other["cumulative"]["all"]["current"]["opened"]["total"] == 0
    assert other["period"]["current"]["valid"] == 0
    # 不带 das 参数时也不会看到别的 DA
    assert snap(client, headers=BC)["period"]["current"]["valid"] < snap(client)["period"]["current"]["valid"]


def test_function_distribution_prd(client):
    f = snap(client)["functions"]
    names = {(x["group"], x["label"]) for x in f["subs"]}
    assert names == {("PPT", "文献解读"), ("PPT", "学术创作Pro"), ("推文", "医学科普"), ("推文", "专业学术"), ("推文", "指南/政策解读")}
    assert [x["value"] for x in f["subs"]] == sorted((x["value"] for x in f["subs"]), reverse=True)
    top = sum(x["value"] for x in f["subs"][: f["topN"]])
    assert top / sum(x["value"] for x in f["subs"]) >= 0.5
    assert all(x["label"] != "海报" for x in f["core"])  # 海报未上线


def test_trend_sums_to_cumulative(client):
    t = client.get(f"/api/vm/overview/trend?{Q}&granularity=month").json()["rows"]
    cum = snap(client)["cumulative"]["all"]["current"]["generation"]
    assert sum(r["total"]["ppt"] for r in t) == cum["ppt"]
    assert sum(r["total"]["tweet"] for r in t) == cum["tweet"]
    assert client.get(f"/api/vm/overview/trend?{Q}&granularity=day").status_code == 400


def test_insight_edit_permissions(client):
    r = client.get(f"/api/vm/overview/insight?{Q}").json()
    assert [s["id"] for s in r["sections"]] == ["conclusion", "risk", "highlight", "other"]
    assert r["editable"] and not r["edited"]
    edited = [{"id": "conclusion", "kind": "conclusion", "title": "核心结论", "body": [{"text": "人工编辑"}]}]
    assert client.put(f"/api/vm/overview/insight?{Q}", json={"sections": edited}, headers=BC).status_code == 403
    assert client.put(f"/api/vm/overview/insight?{Q}", json={"sections": edited}).status_code == 200
    r2 = client.get(f"/api/vm/overview/insight?{Q}").json()
    assert r2["edited"] and r2["sections"][0]["body"][0]["text"] == "人工编辑"
    # DA 管理员只读，且看不到超管对「超管视角」的编辑
    rb = client.get(f"/api/vm/overview/insight?{Q}", headers=BC).json()
    assert not rb["editable"] and not rb["edited"]
    client.put(f"/api/vm/overview/insight?{Q}", json={"sections": []})
    assert not client.get(f"/api/vm/overview/insight?{Q}").json()["edited"]
