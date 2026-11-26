"""部门 / 治疗领域(TA) 归一化。

策略：优先查 DeptMapping/TaMapping 表里管理员已确认过的精确映射；
没有精确匹配时用关键词兜底猜一个归类（同时把这条新遇到的原始值写入映射表，
标成待确认状态，方便管理员之后去后台核实/修正），确保新出现的部门/DA
字符串不会导致解析失败，只会进"未匹配"桶或者一个还算合理的猜测桶。
"""

from __future__ import annotations

from sqlalchemy.orm import Session

from .. import models

_DEPT_KEYWORDS = [
    ("医学部", "医学部 MED"),
    ("销售部", "销售部 TAM"),
    ("市场部", "市场部 MKT"),
    ("患者解决方案", "患者解决方案 PST"),
    ("准入", "准入 ACC"),
    ("其他", "其他 OTH"),
]

_SPECIAL_TA_KEYWORDS = [
    ("大客户", "大客户HSA"),
    ("多渠道", "多渠道MCE"),
    ("非医学部", "其他/未分类"),
]

_DISEASE_TA_KEYWORDS = [
    ("肺癌", "肺癌LC"),
    ("乳腺癌", "乳腺癌BC"),
    ("血液", "血液HEMA"),
    ("肝癌", "肝癌GI"),
    ("神经科学", "神经科学"),
    ("眼科", "眼科"),
    ("肾病", "肾病免疫"),
    ("呼吸", "呼吸"),
    ("流感", "流感"),
]

UNMATCHED_DEPT = "未匹配"
UNMATCHED_TA = "未匹配"


def normalize_dept(db: Session, dept_raw: str | None) -> str:
    if not dept_raw:
        return UNMATCHED_DEPT

    existing = db.query(models.DeptMapping).filter_by(raw_value=dept_raw).one_or_none()
    if existing:
        return existing.normalized

    normalized = UNMATCHED_DEPT
    if "NMA" in dept_raw:
        normalized = "准入 ACC"
    else:
        for keyword, bucket in _DEPT_KEYWORDS:
            if keyword in dept_raw:
                normalized = bucket
                break

    db.add(models.DeptMapping(raw_value=dept_raw, normalized=normalized))
    db.flush()
    return normalized


def normalize_ta(db: Session, da_raw: str | None) -> tuple[str, str | None, bool]:
    """返回 (ta_base, track, is_test)。track 取值 'CE' / '医学部' / None（特殊分类无轨道）。"""
    if not da_raw:
        return UNMATCHED_TA, None, False

    existing = db.query(models.TaMapping).filter_by(raw_value=da_raw).one_or_none()
    if existing:
        return existing.ta_base, existing.track, existing.is_test

    is_test = "测试" in da_raw
    ta_base = UNMATCHED_TA
    track: str | None = None
    is_special = False

    if is_test:
        ta_base = "测试"
        is_special = True
    elif "NMA" in da_raw:
        ta_base = "NMA"
        is_special = True
    else:
        for keyword, bucket in _SPECIAL_TA_KEYWORDS:
            if keyword in da_raw:
                ta_base = bucket
                is_special = True
                break
        else:
            for keyword, bucket in _DISEASE_TA_KEYWORDS:
                if keyword in da_raw:
                    ta_base = bucket
                    track = "CE" if "CE" in da_raw.upper() else "医学部"
                    break
            else:
                if "其他" in da_raw:
                    ta_base = "其他/未分类"
                    is_special = True

    db.add(
        models.TaMapping(
            raw_value=da_raw,
            ta_base=ta_base,
            track=track,
            is_special=is_special,
            is_test=is_test,
        )
    )
    db.flush()
    return ta_base, track, is_test
