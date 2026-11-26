"""mock 补齐：现有三份上传文件里没有、但 PRD 指标依赖的字段。

全部用「账号 id + 字段名」做哈希，结果确定性(同一账号每次相同)，不会随刷新跳变。
真实数据优先：只有真实值缺失时才补；补了哪些字段会记入 Dataset.mock_fields，前端据此显示「含模拟数据」。
商汤接口就绪后这些字段改由接口提供，本文件即可整体下线。
"""
from __future__ import annotations

import datetime as dt
import hashlib

REGIONS = ["东区", "南区", "西区", "北区", "中一区", "中二区"]
PPT_SUBS = ["文献解读", "学术创作Pro"]


def h(*parts) -> float:
    """[0,1) 的确定性伪随机数。"""
    d = hashlib.md5("|".join(map(str, parts)).encode()).digest()
    return int.from_bytes(d[:6], "big") / float(1 << 48)


def pick(seq, *parts):
    return seq[int(h(*parts) * len(seq)) % len(seq)]


def rand_date(lo: dt.date, hi: dt.date, *parts) -> dt.date:
    span = max((hi - lo).days, 0)
    return lo + dt.timedelta(days=int(h(*parts) * (span + 1)))
