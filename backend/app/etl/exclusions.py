"""排除名单 / 特殊口径规则。

这是人工维护的名单，不是能从原始文件里自动推导出来的规则，且含真实人员信息，**不写进代码/仓库**：
- 运行时数据在 ExclusionRule 表，通过管理后台(api/admin.py)增删改。
- 首次初始化时可选读取本地种子文件 `backend/data/exclusion_seed.json`(在 .gitignore 内)；文件不存在则不种。

种子文件格式(列表，每项对应 ExclusionRule 一行)：
[
  {"account_name_pattern": "某测试账号", "rule_type": "full_exclude", "note": "..."},
  {"account_id": 123, "rule_type": "dual_track_cost_only", "note": "..."}
]
rule_type：full_exclude=全量剔除；dual_track_cost_only=使用口径剔除但花费仍计入。
"""

from __future__ import annotations

import datetime as dt
import json

from sqlalchemy.orm import Session

from .. import config, models

FULL_EXCLUDE = "full_exclude"
DUAL_TRACK_COST_ONLY = "dual_track_cost_only"

SEED_FILE = config.DATA_DIR / "exclusion_seed.json"


def seed_default_exclusion_rules(db: Session) -> None:
    if not SEED_FILE.exists():
        return
    rows = db.query(models.ExclusionRule).all()
    patterns = {r.account_name_pattern for r in rows if r.account_name_pattern}
    ids = {r.account_id for r in rows if r.account_id}

    for item in json.loads(SEED_FILE.read_text(encoding="utf-8")):
        pat, acc = item.get("account_name_pattern"), item.get("account_id")
        if (pat and pat in patterns) or (acc and acc in ids):
            continue
        db.add(models.ExclusionRule(
            account_name_pattern=pat, account_id=acc,
            rule_type=item.get("rule_type", FULL_EXCLUDE), note=item.get("note"), active=True,
        ))
    db.flush()


def get_exclusion_map(
    db: Session, week_start: dt.date | None = None, week_end: dt.date | None = None
) -> dict[int, str]:
    """返回 {account_id: rule_type}，同一账号命中多条规则时 full_exclude 优先。"""
    rules = db.query(models.ExclusionRule).filter_by(active=True).all()
    result: dict[int, str] = {}

    for rule in rules:
        if rule.week_start and week_end and rule.week_start > week_end:
            continue
        if rule.week_end and week_start and rule.week_end < week_start:
            continue

        account_ids: set[int] = set()
        if rule.account_id is not None:
            account_ids.add(rule.account_id)
        if rule.account_name_pattern:
            pattern = f"%{rule.account_name_pattern}%"
            matches = (
                db.query(models.Account.id)
                .filter(
                    (models.Account.account.ilike(pattern))
                    | (models.Account.user_name.ilike(pattern))
                )
                .all()
            )
            account_ids.update(i for (i,) in matches)

        for account_id in account_ids:
            if result.get(account_id) == FULL_EXCLUDE:
                continue
            result[account_id] = rule.rule_type

    return result
