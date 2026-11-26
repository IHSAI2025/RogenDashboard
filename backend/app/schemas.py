import datetime as dt

from pydantic import BaseModel


class ExclusionRuleIn(BaseModel):
    account_id: int | None = None
    account_name_pattern: str | None = None
    rule_type: str
    week_start: dt.date | None = None
    week_end: dt.date | None = None
    note: str | None = None
    active: bool = True


class QuotaIn(BaseModel):
    da_code: str
    account_type: str  # PLUS / SUPER
    quota: int
    effective_from: dt.date = dt.date(2026, 7, 1)
    note: str | None = None


class AccountAttrIn(BaseModel):
    source_tag: str | None = None
    status: str | None = None
    opened_at: dt.date | None = None
    disabled_at: dt.date | None = None
    first_login_at: dt.date | None = None
