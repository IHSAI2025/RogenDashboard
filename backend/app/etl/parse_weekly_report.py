"""解析 weekly_report_YYYYMMDD_YYYYMMDD.html（后台自动生成的周度项目明细报告）。

页面结构（已通过实际样本核实，见 backend/app/etl/parse_weekly_report.py 顶部的解析策略）：
- 顶部两张表：全局汇总表（指标/数值）、同比增长对比表（指标/上期/本期/环比变化）
- 每个用户一个 `<div class="user-section" data-user="姓名" data-uid="ID">`，内部依次是：
  - 汇总小表（资料库/PPT 项目/推文项目[/PPT 导出/推文导出]）
  - 环比小表（环比/PPT 数量/PPT Token/PPT 花费/推文数量/推文 Token/推文花费）
  - `<h3>N.1 PPT 项目</h3>` 后跟明细表（标题/创建时间/页数/时长/模型/场景/语言/速度/素材/Token/花费，末行"合计"）
  - `<h3>N.2 推文项目</h3>` 后跟明细表（标题/创建时间/时长/模型/场景/字数/素材/Token/花费，末行"合计"）

不同周之间全局汇总表的字段数量会变化（11~15项），因此一律按"指标名文本"取值，不依赖列位置/字段数量。
"""

from __future__ import annotations

from dataclasses import dataclass, field

from bs4 import BeautifulSoup

from .value_parsing import (
    parse_cost,
    parse_duration_minutes,
    parse_int,
    parse_number,
    parse_word_count,
)


@dataclass
class ProjectItemData:
    item_type: str  # ppt / article
    title: str
    created_date: str | None
    duration_min: float | None
    page_count: int | None
    word_count: int | None
    model: str | None
    scene: str | None
    language: str | None
    speed: str | None
    materials: str | None
    token: float | None
    cost: float | None


@dataclass
class UserSectionData:
    uid: int
    name: str
    summary: dict = field(default_factory=dict)
    ppt_items: list[ProjectItemData] = field(default_factory=list)
    article_items: list[ProjectItemData] = field(default_factory=list)


@dataclass
class WeeklyReportData:
    title: str | None
    generated_at: str | None
    global_summary: dict[str, str]
    wow_rows: list[dict[str, str]]
    users: list[UserSectionData]


def _table_header_texts(table) -> list[str]:
    header_row = table.find("tr")
    if header_row is None:
        return []
    return [th.get_text(strip=True) for th in header_row.find_all(["th", "td"])]


def _parse_key_value_table(table) -> dict[str, str]:
    """解析 `<tr><th>指标</th><th>数值</th></tr>` 这种两列表格。"""
    result = {}
    rows = table.find_all("tr")
    for row in rows[1:]:
        cells = row.find_all("td")
        if len(cells) >= 2:
            key = cells[0].get_text(strip=True)
            value = cells[1].get_text(strip=True)
            result[key] = value
    return result


def _parse_wow_table(table) -> list[dict[str, str]]:
    headers = _table_header_texts(table)
    rows = table.find_all("tr")
    result = []
    for row in rows[1:]:
        cells = row.find_all("td")
        if not cells:
            continue
        values = [c.get_text(strip=True) for c in cells]
        result.append(dict(zip(headers, values)))
    return result


def _classify_table(table) -> str:
    headers = _table_header_texts(table)
    header_text = "".join(headers)
    if headers and headers[0] == "环比":
        return "user_wow"
    if "资料库" in header_text and ("PPT 项目" in header_text or "PPT项目" in header_text):
        return "user_summary"
    if "标题" in headers and "页数" in headers:
        return "ppt_items"
    if "标题" in headers and "字数" in headers:
        return "article_items"
    return "unknown"


def _parse_project_table(table, item_type: str) -> list[ProjectItemData]:
    headers = _table_header_texts(table)
    idx = {h: i for i, h in enumerate(headers)}
    items = []
    for row in table.find_all("tr")[1:]:
        cells = row.find_all("td")
        if not cells:
            continue
        values = [c.get_text(strip=True) for c in cells]
        title = values[idx["标题"]] if idx.get("标题") is not None and idx["标题"] < len(values) else ""
        if title == "合计":
            continue  # 跳过合计行，合计由计算引擎自己汇总校验

        def get(col: str) -> str | None:
            i = idx.get(col)
            if i is None or i >= len(values):
                return None
            return values[i]

        items.append(
            ProjectItemData(
                item_type=item_type,
                title=title,
                created_date=get("创建时间"),
                duration_min=parse_duration_minutes(get("时长")),
                page_count=parse_int(get("页数")),
                word_count=parse_word_count(get("字数")),
                model=get("模型"),
                scene=get("场景"),
                language=get("语言"),
                speed=get("速度"),
                materials=get("素材"),
                token=parse_number(get("Token")),
                cost=parse_cost(get("花费")),
            )
        )
    return items


def parse_weekly_report_html(html_text: str) -> WeeklyReportData:
    soup = BeautifulSoup(html_text, "lxml")

    title_tag = soup.find("title")
    title = title_tag.get_text(strip=True) if title_tag else None

    generated_at = None
    for text_node in soup.stripped_strings:
        if text_node.startswith("生成时间"):
            generated_at = text_node.split("：", 1)[-1].split(":", 1)[-1].strip()
            if "：" in text_node or ":" in text_node:
                generated_at = text_node.split("时间", 1)[-1].lstrip("：: ").strip()
            break

    all_tables = soup.find_all("table")
    global_summary: dict[str, str] = {}
    wow_rows: list[dict[str, str]] = []
    for table in all_tables:
        if table.find_parent("div", class_="user-section") is not None:
            continue
        headers = _table_header_texts(table)
        if headers[:2] == ["指标", "数值"]:
            global_summary = _parse_key_value_table(table)
        elif headers[:1] == ["指标"] and "环比变化" in headers:
            wow_rows = _parse_wow_table(table)

    users: list[UserSectionData] = []
    for section in soup.find_all("div", class_="user-section"):
        uid_raw = section.get("data-uid")
        name = section.get("data-user", "")
        if uid_raw is None:
            continue
        uid = int(uid_raw)
        user_data = UserSectionData(uid=uid, name=name)

        for table in section.find_all("table"):
            kind = _classify_table(table)
            if kind == "user_summary":
                kv = {}
                headers = _table_header_texts(table)
                data_row = table.find_all("tr")[1] if len(table.find_all("tr")) > 1 else None
                if data_row is not None:
                    values = [c.get_text(strip=True) for c in data_row.find_all("td")]
                    kv = dict(zip(headers, values))
                user_data.summary = {
                    "repo_count": parse_int(kv.get("资料库")) or 0,
                    "ppt_count": parse_int(kv.get("PPT 项目")) or 0,
                    "article_count": parse_int(kv.get("推文项目")) or 0,
                    "ppt_export_count": parse_int(kv.get("PPT 导出")) or 0,
                    "article_export_count": parse_int(kv.get("推文导出")) or 0,
                }
            elif kind == "ppt_items":
                user_data.ppt_items = _parse_project_table(table, "ppt")
            elif kind == "article_items":
                user_data.article_items = _parse_project_table(table, "article")

        users.append(user_data)

    return WeeklyReportData(
        title=title,
        generated_at=generated_at,
        global_summary=global_summary,
        wow_rows=wow_rows,
        users=users,
    )
