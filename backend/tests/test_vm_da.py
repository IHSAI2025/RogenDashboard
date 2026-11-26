"""DA 下钻 view-model(/api/vm/da/*) 与既有口径接口的一致性、权限裁剪、比率约定。"""
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
    from app import models
    from app.database import SessionLocal
    from app.main import app
    from scripts import seed_local

    with TestClient(app) as c:
        db = SessionLocal()
        seeded = db.query(models.WeeklyUpload).count() > 0
        db.close()
        if not seeded:
            seed_local.main(SRC)
        yield c


def test_active_sum_matches_overview(client):
    ov = client.get(f"/api/insight/overview?{Q}").json()["current"]["active"]["count"]["value"]
    rows = client.get(f"/api/vm/da/groups?{Q}&dim=da&include_unmapped=true").json()["rows"]
    assert sum(r["active"] for r in rows) == ov
    for dim in ("region", "leader"):
        rs = client.get(f"/api/vm/da/groups?{Q}&dim={dim}&include_unmapped=true").json()["rows"]
        assert sum(r["active"] for r in rs) == ov


def test_rates_are_ratios_with_num_den(client):
    for r in client.get(f"/api/vm/da/groups?{Q}&dim=da").json()["rows"]:
        for k in ("activeRate", "silentRate"):
            c = r[k]
            assert {"numerator", "denominator", "rate"} <= set(c)
            assert c["rate"] is None or 0 <= c["rate"] <= 1
            assert c["rate"] == (c["numerator"] / c["denominator"] if c["denominator"] else None)
        assert r["importRate"] is None or r["importRate"] >= 0
        assert r["effective"] == r["active"] + r["dormant"] + r["silent"]


def test_import_rate_only_for_da_dim(client):
    assert all(r["quota"] is None for r in client.get(f"/api/vm/da/groups?{Q}&dim=region").json()["rows"])
    assert any(r["quota"] for r in client.get(f"/api/vm/da/groups?{Q}&dim=da").json()["rows"])


def test_prev_period_same_day(client):
    d = client.get(f"/api/vm/da/groups?{Q}&dim=da").json()
    assert d["period"]["prev"] == ["2026-07-01", "2026-07-23"]
    assert d["rows"][0]["prev"] is not None


def test_da_admin_clipped(client):
    rows = client.get(f"/api/vm/da/groups?{Q}&dim=da&das=LC,GI", headers=BC).json()["rows"]
    assert rows == []
    rows = client.get(f"/api/vm/da/groups?{Q}&dim=da", headers=BC).json()["rows"]
    assert [r["key"] for r in rows] == ["BC"]
    tr = client.get(f"/api/vm/da/trend?{Q}&granularity=month&focus_dim=da&focus_key=LC", headers=BC).json()["points"]
    assert all(p["activeRate"] is None and p["genTotal"] == 0 for p in tr)
    # 导出同样被裁剪：只含 BC
    r = client.get(f"/api/vm/da/export?{Q}&dim=da&fmt=csv", headers=BC)
    assert r.status_code == 200 and "LC" not in r.text.split("\n", 8)[-1].split(",")[0]


def test_focus_and_platform(client):
    d = client.get(f"/api/vm/da/groups?{Q}&dim=region&focus_dim=da&focus_key=BC").json()
    bc = [r for r in client.get(f"/api/vm/da/groups?{Q}&dim=da").json()["rows"] if r["key"] == "BC"][0]
    assert sum(r["effective"] for r in d["rows"]) == bc["effective"]
    assert d["platform"]["activeRate"]["denominator"] >= bc["effective"]


def test_trend_buckets(client):
    m = client.get(f"/api/vm/da/trend?{Q}&granularity=month").json()["points"]
    assert [p["label"] for p in m] == ["26年7月", "26年8月"]
    assert client.get(f"/api/vm/da/trend?{Q}&granularity=bad").status_code == 400
