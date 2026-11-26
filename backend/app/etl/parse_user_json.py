"""解析 user.json（账号主数据：id / userName / phoneNumber / account / identity）。"""

from __future__ import annotations

import json
from dataclasses import dataclass


@dataclass
class AccountData:
    id: int
    user_name: str
    phone_number: str
    account: str
    identity: str


def parse_user_json(json_text: str) -> list[AccountData]:
    raw = json.loads(json_text)
    result = []
    for item in raw:
        result.append(
            AccountData(
                id=int(item["id"]),
                user_name=item.get("userName", ""),
                phone_number=item.get("phoneNumber", ""),
                account=item.get("account", ""),
                identity=item.get("identity", ""),
            )
        )
    return result
