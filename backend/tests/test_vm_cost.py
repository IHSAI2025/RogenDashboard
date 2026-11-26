"""费用看板 view-model 接口 /api/vm/cost/*（PRD 5.x，验收 5/7/8/9）。"""
import warnings
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

warnings.filterwarnings("ignore")
SRC = Path(__file__).resolve().parents[2] / "临时后台开发数据包" / "数据源"
pytestmark = pytest.mark.skipif(not SRC.exists(), reason="无数据源目录")
BC = {"X-Role": "da_admin", "X-Managed-DAs": "BC"}
URL = "/api/vm/cost/summary?month=2026-08"


@pytest.fixture(scope="module")
def client():
    from app.main import app
    from scripts import seed_local
    with TestClient(app):
        seed_local.main(SRC)
        yield TestClient(app)


def test_totals_consistent(client):  # 验收 7
    d = client.get(URL).json()
    o = d["overview"]
    assert sum(r["spend"] for r in d["rank"]) == pytest.approx(o["spend"], abs=0.01)
    assert sum(p["spend"] for p in d["persons"]) == pytest.approx(o["spend"], abs=0.01)
    assert d["totals"]["rank_sum"] == pytest.approx(o["spend"], abs=0.01)
    assert sum(p["spend"] for p in d["daily"]["points"] if p["total"] is not None for p in [{"spend": p["total"]}]) == pytest.approx(o["spend"], abs=0.05)


def test_purchase_plus_free(client):  # 验收 8
    o = client.get(URL).json()["overview"]
    assert o["purchaseSpend"] + o["freeSpend"] + o["unlabeledSpend"] == pytest.approx(o["spend"], abs=0.01)
    for r in client.get(URL).json()["rank"]:
        assert r["purchaseSpend"] + r["freeSpend"] == pytest.approx(r["spend"], abs=0.01)


def test_budget_formula_and_ratio(client):  # 验收 9
    d = client.get(URL).json()
    o = d["overview"]
    assert o["budget"] == o["nPlus"] * 600 + o["nSuper"] * 1200
    assert o["rate"] == pytest.approx(o["rateNum"] / o["rateDen"])  # 0~1 小数
    assert 0 <= o["rate"] <= 1
    for r in d["rank"]:
        assert (r["perCapita"] is None) == (r["spenders"] == 0)
    assert d["level"] == "da"
    assert any(r["unmapped"] for r in d["rank"])  # 待映射单列


def test_da_admin_scoped(client):  # 验收 5
    assert client.get(URL + "&das=LC,GI", headers=BC).json()["persons"] == []  # 请求越权 DA -> 被裁剪为空
    d = client.get(URL, headers=BC).json()
    assert d["level"] == "region"
    assert all(p["daId"] == "BC" for p in d["persons"])
    assert sum(p["spend"] for p in d["persons"]) == pytest.approx(d["overview"]["spend"], abs=0.01)
    assert "*" in d["persons"][0]["phone"]  # 手机号脱敏
    full = client.get(URL).json()["persons"][0]["phone"]
    assert "*" not in full
    other_acc = next(p for p in client.get(URL).json()["persons"] if p["daId"] == "LC")
    assert client.get(f"/api/vm/cost/account/{other_acc['id']}?month=2026-08", headers=BC).status_code == 404


def test_other_role_403(client):
    h = {"X-Role": "other", "X-Managed-DAs": "BC"}
    assert client.get(URL, headers=h).status_code == 403
    assert client.get("/api/vm/cost/account/2468?month=2026-08", headers=h).status_code == 403
    assert client.get("/api/insight/export/cost?month=2026-08", headers=h).status_code == 403


def test_account_detail_and_bad_month(client):
    d = client.get("/api/vm/cost/account/2468?month=2026-08").json()
    assert len(d["months"]) == 12 and d["months"][0]["spend"] is None  # 上线前显示「—」
    assert sum(f["amount"] for f in d["byFunction"]) == pytest.approx(
        next(p["spend"] for p in client.get(URL).json()["persons"] if p["id"] == "2468"), abs=0.01)
    assert client.get("/api/vm/cost/summary?month=2026-8x").status_code == 400
