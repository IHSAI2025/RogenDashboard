"""weekly_report.html 里各种"带单位文本"数值的归一化工具。

样例：
- "677.7K" / "1.9M" -> Token 数（K=1e3, M=1e6）
- "¥9.07" -> 花费
- "7.3min" / "8.2h" -> 统一换算成分钟
- "13"（页数）/ "859字"（字数）
- "-" / "" / "—" -> None（缺失值）
"""

from __future__ import annotations

import re

EMPTY_VALUES = {"", "-", "—", "--"}


def parse_number(text: str | None) -> float | None:
    """解析带 K/M/B 后缀的数字，如 Token 数。"""
    if text is None:
        return None
    text = text.strip()
    if text in EMPTY_VALUES:
        return None
    text = text.replace(",", "")
    multiplier = 1.0
    if text and text[-1] in "KMB":
        multiplier = {"K": 1_000.0, "M": 1_000_000.0, "B": 1_000_000_000.0}[text[-1]]
        text = text[:-1]
    try:
        return float(text) * multiplier
    except ValueError:
        return None


def parse_cost(text: str | None) -> float | None:
    """解析形如 "¥9.07" 的花费。"""
    if text is None:
        return None
    text = text.strip()
    if text in EMPTY_VALUES:
        return None
    text = text.replace("¥", "").replace(",", "").strip()
    if text in EMPTY_VALUES:
        return None
    try:
        return float(text)
    except ValueError:
        return None


_DURATION_RE = re.compile(r"^([\d.]+)\s*(min|h|s)$")


def parse_duration_minutes(text: str | None) -> float | None:
    """解析形如 "7.3min" / "8.2h" 的时长，统一转换为分钟。"""
    if text is None:
        return None
    text = text.strip()
    if text in EMPTY_VALUES:
        return None
    m = _DURATION_RE.match(text)
    if not m:
        return None
    value, unit = float(m.group(1)), m.group(2)
    if unit == "min":
        return value
    if unit == "h":
        return value * 60
    if unit == "s":
        return value / 60
    return None


def parse_int(text: str | None) -> int | None:
    """解析整数，允许附带非数字单位文本（如"10 个"、"2 次"），取第一段数字。"""
    if text is None:
        return None
    text = text.strip()
    if text in EMPTY_VALUES:
        return None
    m = re.search(r"-?\d+(\.\d+)?", text)
    if not m:
        return None
    try:
        return int(float(m.group(0)))
    except ValueError:
        return None


def parse_word_count(text: str | None) -> int | None:
    """解析形如 "859字" 的字数。"""
    if text is None:
        return None
    return parse_int(text.replace("字", ""))
