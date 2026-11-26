"""PRD 2.1 DA 字典：把花名册「所属DA」原始值归一到 PRD 的 DA 代码。

无法映射(其他/呼吸/非医学部/测试)的账号 da=None，页面显示「待映射」，且视为「非 DA 账号」(核心业务口径剔除)。
CE 轨道(如 肺癌LC_CE)归到同一个 DA，不另列。
"""
from __future__ import annotations

DA_GROUPS: dict[str, list[str]] = {
    "肿瘤": ["BC", "LC", "GI", "HEMA"],
    "非肿瘤": ["OPH", "NS&RD", "INF", "IMMU"],
    "Access": ["NMA", "HSA", "MCE"],
}
ALL_DAS = [d for g in DA_GROUPS.values() for d in g]
UNMAPPED = "待映射"

# (关键字(大写比对), DA)；先匹配先得
_RULES = [
    ("HSA", "HSA"), ("MCE", "MCE"), ("NMA", "NMA"),
    ("HEMA", "HEMA"), ("NS&RD", "NS&RD"), ("OPH", "OPH"), ("INF", "INF"),
    ("RENAL", "IMMU"), ("IMMU", "IMMU"), ("肾病", "IMMU"),
    ("BC", "BC"), ("乳腺", "BC"),
    ("LC", "LC"), ("肺癌", "LC"),
    ("GI", "GI"), ("肝癌", "GI"),
    ("血液", "HEMA"), ("神经", "NS&RD"), ("眼科", "OPH"), ("流感", "INF"),
    ("大客户", "HSA"), ("多渠道", "MCE"),
]


def is_test_da(raw: str | None) -> bool:
    return bool(raw) and "测试" in raw


def da_code(raw: str | None) -> str | None:
    if not raw or is_test_da(raw):
        return None
    up = raw.upper()
    for key, code in _RULES:
        if key in up:
            return code
    return None
