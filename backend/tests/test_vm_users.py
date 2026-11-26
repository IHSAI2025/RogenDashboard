"""用户数据下钻 view-model 接口校验。"""
import io
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
        from app.database import SessionLocal
        from app import models
        db = SessionLocal()
        empty = db.query(models.WeeklyUpload).count() == 0
        db.close()
        if empty:
            seed_local.main(SRC)
        yield TestClient(app)


def test_states_partition_valid(client):
    d = client.get(f"/api/vm/users/list?{Q}").json()
    c = d["counts"]
    ov = client.get(f"/api/insight/overview?{Q}").json()["current"]
    assert c["活跃"] + c["休眠"] + c["沉默"] == ov["active"]["rate"]["den"]  # 有效账号数
    assert c["活跃"] == ov["active"]["count"]["value"]                         # 与全景活跃数一致
    assert c["all"] >= c["活跃"] + c["休眠"] + c["沉默"]                          # 全部含停用账号


def test_tab_rows_match_counts(client):
    d = client.get(f"/api/vm/users/list?{Q}").json()
    for s in ("活跃", "休眠", "沉默"):
        r = client.get("/api/vm/users/list", params={"start": "2026-08-01", "end": "2026-08-31", "state": s}).json()
        assert len(r["rows"]) == d["counts"][s] and all(x["state"] == s for x in r["rows"])


def test_region_and_enabled_filters(client):
    d = client.get(f"/api/vm/users/list?{Q}").json()
    reg = d["rows"][0]["region"]
    r = client.get("/api/vm/users/list", params={"start": "2026-08-01", "end": "2026-08-31", "region": reg}).json()
    assert r["rows"] and all(x["region"] == reg for x in r["rows"])
    r = client.get("/api/vm/users/list", params={"start": "2026-08-01", "end": "2026-08-31", "enabled": "停用"}).json()
    assert all(not x["enabled"] and x["state"] == "—" for x in r["rows"])


def test_da_admin_scoped(client):
    r = client.get(f"/api/vm/users/list?{Q}&das=LC,GI", headers=BC).json()
    assert r["rows"] == []
    r = client.get(f"/api/vm/users/list?{Q}", headers=BC).json()
    assert r["rows"] and {x["da"] for x in r["rows"]} == {"BC"}
    assert all("*" in x["phone"] for x in r["rows"])  # DA 管理员手机号脱敏
    full = client.get(f"/api/vm/users/list?{Q}").json()["rows"]
    assert all("*" not in x["phone"] for x in full)


def test_weekly_scoped(client):
    rows = client.get(f"/api/vm/users/list?{Q}").json()["rows"]
    other = next(x for x in rows if x["da"] != "BC" and x["da"] != "待映射")
    mine = next(x for x in rows if x["da"] == "BC")
    assert client.get(f"/api/vm/users/{other['id']}/weekly?end=2026-08-31", headers=BC).status_code == 404
    ok = client.get(f"/api/vm/users/{mine['id']}/weekly?end=2026-08-31", headers=BC)
    assert ok.status_code == 200 and len(ok.json()["points"]) == 12
    assert client.get("/api/vm/users/99999999/weekly?end=2026-08-31").status_code == 404


def test_export_rows_match_page(client):
    import openpyxl
    p = {"start": "2026-08-01", "end": "2026-08-31", "state": "活跃"}
    page = client.get("/api/vm/users/list", params=p).json()["rows"]
    x = client.get("/api/vm/users/export", params={**p, "fmt": "xlsx"})
    assert x.status_code == 200
    wb = openpyxl.load_workbook(io.BytesIO(x.content))
    assert "说明" in wb.sheetnames
    ws = wb[[n for n in wb.sheetnames if n != "说明"][0]]
    assert ws.max_row - 1 == len(page)
    meta = {r[0]: r[1] for r in wb["说明"].iter_rows(values_only=True)}
    assert {"统计周期", "筛选条件", "数据截至", "口径版本"} <= set(meta)
    c = client.get("/api/vm/users/export", params={**p, "fmt": "csv"}).content.decode("utf-8-sig").splitlines()
    assert len([l for l in c if not l.startswith("#")]) - 1 == len(page)
