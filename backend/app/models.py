import datetime as dt

from sqlalchemy import (
    Boolean,
    Date,
    DateTime,
    Float,
    ForeignKey,
    Integer,
    JSON,
    String,
    Text,
    UniqueConstraint,
)
from sqlalchemy.orm import Mapped, mapped_column, relationship

from .database import Base


class Account(Base):
    """来自 user.json 的账号主数据，id 与 weekly_report 里的 data-uid 一致。"""

    __tablename__ = "accounts"

    id: Mapped[int] = mapped_column(Integer, primary_key=True, autoincrement=False)
    user_name: Mapped[str] = mapped_column(String(128))
    phone_number: Mapped[str] = mapped_column(String(32), index=True)
    account: Mapped[str] = mapped_column(String(128))
    identity: Mapped[str] = mapped_column(String(32))
    is_excluded: Mapped[bool] = mapped_column(Boolean, default=False)
    exclude_reason: Mapped[str | None] = mapped_column(String(255), nullable=True)
    # —— PRD 新增属性：现有三份上传文件里没有，待商汤接口/后台补录；为空时由 mock 适配器兜底 ——
    source_tag: Mapped[str | None] = mapped_column(String(8), nullable=True)  # 采购 / 免费
    status: Mapped[str | None] = mapped_column(String(8), nullable=True)  # 正常 / 停用
    opened_at: Mapped[dt.date | None] = mapped_column(Date, nullable=True)
    disabled_at: Mapped[dt.date | None] = mapped_column(Date, nullable=True)
    first_login_at: Mapped[dt.date | None] = mapped_column(Date, nullable=True)

    project_items: Mapped[list["ProjectItem"]] = relationship(back_populates="account")


class AccountImportBatch(Base):
    """每次上传 user.json 的记录，供后台展示"当前生效的账号库是哪次上传的"。

    Account 表本身只有合并后的最新状态（按 id upsert），没有版本历史，所以单独记一笔。
    """

    __tablename__ = "account_import_batches"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    imported_at: Mapped[dt.datetime] = mapped_column(DateTime, default=dt.datetime.utcnow)
    source_filename: Mapped[str] = mapped_column(String(255))
    account_count: Mapped[int] = mapped_column(Integer)


class RosterSnapshot(Base):
    """每次上传 xlsx 花名册的一份快照。"""

    __tablename__ = "roster_snapshots"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    upload_id: Mapped[int | None] = mapped_column(ForeignKey("weekly_uploads.id"), nullable=True)
    snapshot_date: Mapped[dt.date] = mapped_column(Date)
    source_filename: Mapped[str] = mapped_column(String(255))
    created_at: Mapped[dt.datetime] = mapped_column(DateTime, default=dt.datetime.utcnow)

    entries: Mapped[list["RosterEntry"]] = relationship(back_populates="snapshot")


class RosterEntry(Base):
    """xlsx「用户批量导出」里的一行，保留原始字段 + 归一化后的部门/TA。"""

    __tablename__ = "roster_entries"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    snapshot_id: Mapped[int] = mapped_column(ForeignKey("roster_snapshots.id"))
    account_id: Mapped[int | None] = mapped_column(ForeignKey("accounts.id"), nullable=True)

    user_name: Mapped[str] = mapped_column(String(128))
    phone_number: Mapped[str] = mapped_column(String(32), index=True)
    da_raw: Mapped[str | None] = mapped_column(String(64), nullable=True)
    identity_raw: Mapped[str | None] = mapped_column(String(32), nullable=True)
    account_type: Mapped[str | None] = mapped_column(String(32), nullable=True)
    province: Mapped[str | None] = mapped_column(String(32), nullable=True)
    city: Mapped[str | None] = mapped_column(String(32), nullable=True)
    hospital_level: Mapped[str | None] = mapped_column(String(32), nullable=True)
    is_t100: Mapped[str | None] = mapped_column(String(16), nullable=True)
    title: Mapped[str | None] = mapped_column(String(64), nullable=True)
    target_audience: Mapped[str | None] = mapped_column(String(64), nullable=True)
    colleague: Mapped[str | None] = mapped_column(String(64), nullable=True)
    dept_raw: Mapped[str | None] = mapped_column(String(64), nullable=True)
    sales_region: Mapped[str | None] = mapped_column(String(64), nullable=True)
    platform_permission: Mapped[str | None] = mapped_column(String(64), nullable=True)
    remark: Mapped[str | None] = mapped_column(String(255), nullable=True)

    dept_norm: Mapped[str | None] = mapped_column(String(64), nullable=True)
    ta_base: Mapped[str | None] = mapped_column(String(64), nullable=True)
    ta_track: Mapped[str | None] = mapped_column(String(16), nullable=True)
    is_test: Mapped[bool] = mapped_column(Boolean, default=False)

    snapshot: Mapped["RosterSnapshot"] = relationship(back_populates="entries")


class WeeklyUpload(Base):
    """一次周报上传批次。"""

    __tablename__ = "weekly_uploads"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    week_start: Mapped[dt.date] = mapped_column(Date)
    week_end: Mapped[dt.date] = mapped_column(Date)
    label: Mapped[str] = mapped_column(String(32))
    uploaded_at: Mapped[dt.datetime] = mapped_column(DateTime, default=dt.datetime.utcnow)
    source_filename_html: Mapped[str | None] = mapped_column(String(255), nullable=True)
    source_filename_json: Mapped[str | None] = mapped_column(String(255), nullable=True)
    source_filename_xlsx: Mapped[str | None] = mapped_column(String(255), nullable=True)
    status: Mapped[str] = mapped_column(String(16), default="draft")  # draft/committed
    is_seed: Mapped[bool] = mapped_column(Boolean, default=False)
    raw_summary: Mapped[dict | None] = mapped_column(JSON, nullable=True)
    raw_wow: Mapped[dict | None] = mapped_column(JSON, nullable=True)

    __table_args__ = (UniqueConstraint("week_start", "week_end", name="uq_week_range"),)

    project_items: Mapped[list["ProjectItem"]] = relationship(back_populates="upload")
    user_summaries: Mapped[list["UserWeekSummary"]] = relationship(back_populates="upload")


class ProjectItem(Base):
    """逐条 PPT/推文项目记录。"""

    __tablename__ = "project_items"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    upload_id: Mapped[int] = mapped_column(ForeignKey("weekly_uploads.id"), index=True)
    account_id: Mapped[int] = mapped_column(ForeignKey("accounts.id"), index=True)

    item_type: Mapped[str] = mapped_column(String(16))  # ppt / article
    title: Mapped[str] = mapped_column(String(512))
    created_date: Mapped[dt.date | None] = mapped_column(Date, nullable=True)
    duration_min: Mapped[float | None] = mapped_column(Float, nullable=True)
    page_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    word_count: Mapped[int | None] = mapped_column(Integer, nullable=True)
    model: Mapped[str | None] = mapped_column(String(64), nullable=True)
    scene: Mapped[str | None] = mapped_column(String(64), nullable=True)
    language: Mapped[str | None] = mapped_column(String(16), nullable=True)
    speed: Mapped[str | None] = mapped_column(String(16), nullable=True)
    materials: Mapped[str | None] = mapped_column(Text, nullable=True)
    token: Mapped[float | None] = mapped_column(Float, nullable=True)
    cost: Mapped[float | None] = mapped_column(Float, nullable=True)

    upload: Mapped["WeeklyUpload"] = relationship(back_populates="project_items")
    account: Mapped["Account"] = relationship(back_populates="project_items")


class UserWeekSummary(Base):
    """weekly_report 里每个用户的小汇总表（含导出次数，项目明细里没有的字段）。"""

    __tablename__ = "user_week_summaries"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    upload_id: Mapped[int] = mapped_column(ForeignKey("weekly_uploads.id"), index=True)
    account_id: Mapped[int] = mapped_column(ForeignKey("accounts.id"), index=True)

    repo_count: Mapped[int] = mapped_column(Integer, default=0)
    ppt_count: Mapped[int] = mapped_column(Integer, default=0)
    article_count: Mapped[int] = mapped_column(Integer, default=0)
    ppt_export_count: Mapped[int] = mapped_column(Integer, default=0)
    article_export_count: Mapped[int] = mapped_column(Integer, default=0)

    upload: Mapped["WeeklyUpload"] = relationship(back_populates="user_summaries")

    __table_args__ = (UniqueConstraint("upload_id", "account_id", name="uq_upload_account"),)


class ExclusionRule(Base):
    """人工维护的排除/特殊口径名单。"""

    __tablename__ = "exclusion_rules"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    account_id: Mapped[int | None] = mapped_column(ForeignKey("accounts.id"), nullable=True)
    account_name_pattern: Mapped[str | None] = mapped_column(String(128), nullable=True)
    rule_type: Mapped[str] = mapped_column(String(32))  # full_exclude / dual_track_cost_only
    week_start: Mapped[dt.date | None] = mapped_column(Date, nullable=True)
    week_end: Mapped[dt.date | None] = mapped_column(Date, nullable=True)
    note: Mapped[str | None] = mapped_column(String(255), nullable=True)
    active: Mapped[bool] = mapped_column(Boolean, default=True)


class DeptMapping(Base):
    """xlsx「所在部门」原始值 -> 归一化部门桶。"""

    __tablename__ = "dept_mappings"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    raw_value: Mapped[str] = mapped_column(String(64), unique=True)
    normalized: Mapped[str] = mapped_column(String(64))


class TaMapping(Base):
    """xlsx「所属DA」原始值 -> 归一化治疗领域 + 轨道。"""

    __tablename__ = "ta_mappings"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    raw_value: Mapped[str] = mapped_column(String(64), unique=True)
    ta_base: Mapped[str] = mapped_column(String(64))
    track: Mapped[str | None] = mapped_column(String(16), nullable=True)  # CE / 医学部 / None
    is_special: Mapped[bool] = mapped_column(Boolean, default=False)
    is_test: Mapped[bool] = mapped_column(Boolean, default=False)


class QuotaConfig(Base):
    """配置额度(个数)：按 DA + 账号类型。动态可编辑(活动激励会改变额度)，取 effective_from 最新且 <= 统计截止日的一条。"""

    __tablename__ = "quota_configs"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    da_code: Mapped[str] = mapped_column(String(32), index=True)
    account_type: Mapped[str] = mapped_column(String(8))  # PLUS / SUPER
    quota: Mapped[int] = mapped_column(Integer)
    effective_from: Mapped[dt.date] = mapped_column(Date, default=dt.date(2026, 7, 1))
    note: Mapped[str | None] = mapped_column(String(255), nullable=True)


class InsightNote(Base):
    """超级管理员编辑过的 AI 洞察文本(1.2 / 2.2)。key = tab + 周期 + 范围，DA 管理员只读。"""

    __tablename__ = "insight_notes"

    id: Mapped[int] = mapped_column(Integer, primary_key=True)
    key: Mapped[str] = mapped_column(String(255), unique=True, index=True)
    content: Mapped[str] = mapped_column(Text)
    updated_at: Mapped[dt.datetime] = mapped_column(DateTime, default=dt.datetime.utcnow)
