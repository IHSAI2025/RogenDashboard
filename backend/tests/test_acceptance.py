"""PRD 一期验收标准的自动化校验(基于 数据源 里的真实文件 + 默认 mock)。"""
import datetime as dt
import warnings
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

warnings.filterwarnings("ignore")
SRC = Path(__file__).resolve().parents[2] / "临时后台开发数据包" / "数据源"
pytestmark = pytest.mark.skipif(not SRC.exists(), reason="无数据源目录")


@pytest.fixture(scope="module")
def client():
    from app.main import app
    from scripts import seed_local
    with TestClient(app):  # 触发 startup 建表
        seed_local.main(SRC)
        yield TestClient(app)


Q = "start=2026-08-01&end=2026-08-31"


def test_cost_totals_consistent(client):  # 验收 7、8
    d = client.get("/api/insight/cost?month=2026-08").json()
    o = d["overview"]
    assert d["totals"]["rank_sum"] == pytest.approx(o["cost"]["value"], abs=0.01)
    assert d["totals"]["detail_sum"] == pytest.approx(o["cost"]["value"], abs=0.01)
    assert o["cost"]["purchase"] + o["cost"]["free"] + o["cost"]["unlabeled"] == pytest.approx(o["cost"]["value"], abs=0.01)


def test_budget_formula(client):  # 验收 9
    o = client.get("/api/insight/cost?month=2026-08").json()["overview"]["budget"]
    assert o["value"] == o["n_plus"] * 600 + o["n_super"] * 1200


def test_active_consistent_across_tabs(client):  # 验收 2
    ov = client.get(f"/api/insight/overview?{Q}").json()["current"]["active"]["count"]["value"]
    da = client.get(f"/api/insight/da?{Q}").json()["rows"]
    assert sum(r["active"]["value"] for r in da) == ov
    us = client.get(f"/api/insight/users?{Q}&state=活跃").json()
    assert len(us["rows"]) == ov


def test_rates_have_num_den(client):  # 验收 3
    ov = client.get(f"/api/insight/overview?{Q}").json()
    for k in ("rate",):
        assert {"num", "den"} <= set(ov["current"]["active"][k])
    for r in client.get(f"/api/insight/da?{Q}").json()["rows"]:
        assert {"num", "den"} <= set(r["active_rate"]) and {"num", "den"} <= set(r["silent_rate"])


def test_usage_states_partition_valid(client):
    c = client.get(f"/api/insight/users?{Q}&state=all").json()["counts"]
    cur = client.get(f"/api/insight/overview?{Q}").json()["current"]
    assert c.get("活跃", 0) + c.get("休眠", 0) + c.get("沉默", 0) == round(
        cur["active"]["rate"]["den"])


def test_da_admin_cannot_read_other_da(client):  # 验收 5
    h = {"X-Role": "da_admin", "X-Managed-DAs": "BC"}
    rows = client.get(f"/api/insight/da?{Q}&das=LC,GI", headers=h).json()["rows"]
    assert rows == [] or all(r["key"] == "BC" for r in rows)
    assert client.get(f"/api/insight/users?{Q}&das=LC&state=all", headers=h).json()["rows"] == []
    assert client.get("/api/insight/cost?month=2026-08", headers={"X-Role": "other"}).status_code == 403
    for r in client.get("/api/insight/cost?month=2026-08", headers=h).json()["detail"]:
        assert r["da"] == "BC"
    assert client.get("/api/insight/export/users?start=2026-08-01&end=2026-08-31&das=LC&fmt=csv", headers=h).status_code == 200


def test_mom_prev_period_same_day(client):
    p = client.get(f"/api/insight/overview?{Q}").json()["period"]
    assert p["end"] == "2026-08-23" and p["prev"] == ["2026-07-01", "2026-07-23"]
