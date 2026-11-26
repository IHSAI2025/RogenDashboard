"""把三个解析器的输出落库：Account / RosterSnapshot+RosterEntry / WeeklyUpload+ProjectItem+UserWeekSummary。

调用顺序固定：先 ingest_accounts，再 ingest_roster（依赖 Account 做手机号->账号的关联），
最后 ingest_weekly_report（依赖 Account 做 uid 关联）。
"""

from __future__ import annotations

import datetime as dt

from sqlalchemy.orm import Session

from .. import models
from .parse_roster_xlsx import RosterEntryData
from .parse_user_json import AccountData
from .parse_weekly_report import WeeklyReportData
from .taxonomy import normalize_dept, normalize_ta


def ingest_accounts(
    db: Session, accounts: list[AccountData], source_filename: str = "user.json"
) -> None:
    for a in accounts:
        existing = db.get(models.Account, a.id)
        if existing is None:
            db.add(
                models.Account(
                    id=a.id,
                    user_name=a.user_name,
                    phone_number=a.phone_number,
                    account=a.account,
                    identity=a.identity,
                )
            )
        else:
            existing.user_name = a.user_name
            existing.phone_number = a.phone_number
            existing.account = a.account
            existing.identity = a.identity
    db.add(
        models.AccountImportBatch(
            source_filename=source_filename,
            account_count=len(accounts),
        )
    )
    db.flush()


def ingest_roster(
    db: Session,
    entries: list[RosterEntryData],
    snapshot_date: dt.date,
    source_filename: str,
    upload_id: int | None = None,
) -> models.RosterSnapshot:
    phone_to_account_id = {
        acc.phone_number: acc.id for acc in db.query(models.Account).all() if acc.phone_number
    }

    snapshot = models.RosterSnapshot(
        upload_id=upload_id,
        snapshot_date=snapshot_date,
        source_filename=source_filename,
    )
    db.add(snapshot)
    db.flush()

    for e in entries:
        dept_norm = normalize_dept(db, e.dept_raw)
        ta_base, ta_track, is_test = normalize_ta(db, e.da_raw)
        db.add(
            models.RosterEntry(
                snapshot_id=snapshot.id,
                account_id=phone_to_account_id.get(e.phone_number),
                user_name=e.user_name,
                phone_number=e.phone_number,
                da_raw=e.da_raw,
                identity_raw=e.identity_raw,
                account_type=e.account_type,
                province=e.province,
                city=e.city,
                hospital_level=e.hospital_level,
                is_t100=e.is_t100,
                title=e.title,
                target_audience=e.target_audience,
                colleague=e.colleague,
                dept_raw=e.dept_raw,
                sales_region=e.sales_region,
                platform_permission=e.platform_permission,
                remark=e.remark,
                dept_norm=dept_norm,
                ta_base=ta_base,
                ta_track=ta_track,
                is_test=is_test,
            )
        )
    db.flush()
    return snapshot


def ingest_weekly_report(
    db: Session,
    report: WeeklyReportData,
    week_start: dt.date,
    week_end: dt.date,
    label: str,
    source_filename: str,
) -> models.WeeklyUpload:
    upload = models.WeeklyUpload(
        week_start=week_start,
        week_end=week_end,
        label=label,
        source_filename_html=source_filename,
        status="draft",
        raw_summary=report.global_summary,
        raw_wow=report.wow_rows,
    )
    db.add(upload)
    db.flush()

    known_account_ids = {a.id for a in db.query(models.Account.id).all()}

    for user in report.users:
        if user.uid not in known_account_ids:
            # user.json 里没有这个账号，先自动补一条最小记录，避免 FK 失败；
            # 后续应重新上传 user.json 补全资料。
            db.add(
                models.Account(
                    id=user.uid,
                    user_name=user.name,
                    phone_number="",
                    account="",
                    identity="unknown",
                )
            )
            db.flush()
            known_account_ids.add(user.uid)

        db.add(
            models.UserWeekSummary(
                upload_id=upload.id,
                account_id=user.uid,
                repo_count=user.summary.get("repo_count", 0),
                ppt_count=user.summary.get("ppt_count", 0),
                article_count=user.summary.get("article_count", 0),
                ppt_export_count=user.summary.get("ppt_export_count", 0),
                article_export_count=user.summary.get("article_export_count", 0),
            )
        )

        for item in user.ppt_items + user.article_items:
            created_date = None
            if item.created_date:
                try:
                    created_date = dt.date.fromisoformat(item.created_date)
                except ValueError:
                    created_date = None
            db.add(
                models.ProjectItem(
                    upload_id=upload.id,
                    account_id=user.uid,
                    item_type=item.item_type,
                    title=item.title,
                    created_date=created_date,
                    duration_min=item.duration_min,
                    page_count=item.page_count,
                    word_count=item.word_count,
                    model=item.model,
                    scene=item.scene,
                    language=item.language,
                    speed=item.speed,
                    materials=item.materials,
                    token=item.token,
                    cost=item.cost,
                )
            )

    db.flush()
    return upload
