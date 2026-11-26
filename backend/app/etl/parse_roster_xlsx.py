"""解析「用户批量导出_*.xlsx」花名册（姓名/电话/所属DA/所在部门等原始字段）。"""

from __future__ import annotations

from dataclasses import dataclass
from io import BytesIO
from typing import BinaryIO

import openpyxl

COLUMN_MAP = {
    "用户姓名": "user_name",
    "联系电话": "phone_number",
    "所属DA": "da_raw",
    "用户身份": "identity_raw",
    "账号类型": "account_type",
    "省份": "province",
    "城市": "city",
    "医院等级": "hospital_level",
    "是否T100": "is_t100",
    "职称": "title",
    "使用对象": "target_audience",
    "负责同事姓名": "colleague",
    "所在部门": "dept_raw",
    "销售大区": "sales_region",
    "平台权限": "platform_permission",
    "备注": "remark",
}


@dataclass
class RosterEntryData:
    user_name: str = ""
    phone_number: str = ""
    da_raw: str | None = None
    identity_raw: str | None = None
    account_type: str | None = None
    province: str | None = None
    city: str | None = None
    hospital_level: str | None = None
    is_t100: str | None = None
    title: str | None = None
    target_audience: str | None = None
    colleague: str | None = None
    dept_raw: str | None = None
    sales_region: str | None = None
    platform_permission: str | None = None
    remark: str | None = None


def _cell_str(value) -> str | None:
    if value is None:
        return None
    text = str(value).strip()
    return text or None


def parse_roster_xlsx(source: str | bytes | BinaryIO) -> list[RosterEntryData]:
    if isinstance(source, (bytes, bytearray)):
        source = BytesIO(source)
    wb = openpyxl.load_workbook(source, data_only=True)
    ws = wb.active

    rows_iter = ws.iter_rows(values_only=True)
    header = [str(h).strip() if h is not None else "" for h in next(rows_iter)]
    field_by_col = {i: COLUMN_MAP[h] for i, h in enumerate(header) if h in COLUMN_MAP}

    entries: list[RosterEntryData] = []
    for row in rows_iter:
        if row is None or all(v is None for v in row):
            continue
        kwargs = {}
        for i, field_name in field_by_col.items():
            kwargs[field_name] = _cell_str(row[i]) if i < len(row) else None
        if not kwargs.get("user_name") and not kwargs.get("phone_number"):
            continue
        entries.append(RosterEntryData(**{k: v for k, v in kwargs.items()}))
    return entries
