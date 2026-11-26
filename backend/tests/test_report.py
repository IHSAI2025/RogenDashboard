"""PRD 4：导出报告(HTML)。"""
import re
import warnings
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

warnings.filterwarnings("ignore")
SRC = Path(__file__).resolve().parents[2] / "临时后台开发数据包" / "数据源"
pytestmark = pytest.mark.skipif(not SRC.exists(), reason="无数据源目录")
Q = "start=2026-08-01&end=2026-08-31"


@pytest.fixture(scope="module")
def client():
    from app.main import app
    from scripts import seed_local
    with TestClient(app):
        seed_local.main(SRC)
        yield TestClient(app)


def test_report_cover_and_slides(client):
    r = client.get(f"/api/report/html?{Q}")
    assert r.status_code == 200 and "attachment" in r.headers["content-disposition"]
    h = r.text
    assert "神笔小罗 分析报告" in h
    assert re.search(r"分析周期：2026-08-01 ～ 2026-08-23", h)            # 统计截止日 = 数据截至日
    assert re.search(r"报告日期：\d{4}-\d\d-\d\d \d\d:\d\d:\d\d", h)
    pages = h.count('<section class="slide')
    assert pages >= 8
    # 验收 4：每个正文页都有 周期 / 范围 / 数据截至 / 口径脚注 / 页码
    for body in h.split('<section class="slide')[2:]:
        assert "分析周期：" in body and "数据截至：" in body and "口径说明：" in body and re.search(r"\d+ / \d+", body)
    assert "viewBox" in h and "<title>" in h                              # 内联 SVG 图表 + 悬停提示
    assert "http://" not in h.replace("http://www.w3.org", "")           # 单文件，无外部依赖


def test_report_da_admin_is_clipped(client):
    h = client.get(f"/api/report/html?{Q}&das=LC,GI", headers={"X-Role": "da_admin", "X-Managed-DAs": "BC"}).text
    assert "授权 DA（BC）" in h
    for other in ("肺癌 LC", "肝癌 GI", "血液肿瘤 HEMA"):
        assert other not in h                                              # 其他 DA 不会出现
    assert "大区 三率看板" in h                                             # DA 管理员按大区


def test_report_other_role_has_no_cost_slide(client):
    h = client.get(f"/api/report/html?{Q}", headers={"X-Role": "other", "X-Managed-DAs": "BC"}).text
    assert "费用看板" not in h and "采购账号费用" not in h
    assert "费用看板" in client.get(f"/api/report/html?{Q}").text          # 超管有费用页
