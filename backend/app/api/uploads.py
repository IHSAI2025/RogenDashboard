from __future__ import annotations

import datetime as dt

from fastapi import APIRouter, Depends, File, Form, HTTPException, UploadFile
from sqlalchemy.orm import Session

from .. import models
from ..database import get_db
from ..etl.ingest import ingest_accounts, ingest_roster, ingest_weekly_report
from ..etl.parse_roster_xlsx import parse_roster_xlsx
from ..etl.parse_user_json import parse_user_json
from ..etl.parse_weekly_report import parse_weekly_report_html
from ..services_scope import Scope, get_scope

router = APIRouter(prefix="/api/uploads", tags=["uploads"])


def _label(s: dt.date, e: dt.date) -> str:
    return f"{s.month}.{s.day:02d}–{e.month}.{e.day:02d}"


@router.get("/current-sources")
def current_sources(db: Session = Depends(get_db)):
    b = db.query(models.AccountImportBatch).order_by(models.AccountImportBatch.imported_at.desc()).first()
    snap = db.query(models.RosterSnapshot).order_by(models.RosterSnapshot.id.desc()).first()
    uploads = db.query(models.WeeklyUpload).order_by(models.WeeklyUpload.week_start).all()
    return {
        "user_json": {"source_filename": b.source_filename, "imported_at": b.imported_at.isoformat(), "account_count": b.account_count} if b else None,
        "roster_xlsx": {"source_filename": snap.source_filename, "snapshot_date": snap.snapshot_date.isoformat(),
                        "entry_count": db.query(models.RosterEntry).filter_by(snapshot_id=snap.id).count()} if snap else None,
        "weeks": [{"label": u.label, "start": u.week_start.isoformat(), "end": u.week_end.isoformat(), "file": u.source_filename_html} for u in uploads],
    }


@router.post("")
async def create_weekly_upload(
    week_start: dt.date = Form(...), week_end: dt.date = Form(...),
    weekly_report_html: UploadFile = File(...), user_json: UploadFile | None = File(None), roster_xlsx: UploadFile | None = File(None),
    db: Session = Depends(get_db), scope: Scope = Depends(get_scope),
):
    """上传 weekly_report.html(必填) + user.json / 花名册 xlsx(有变化时传)。同一周重复上传会覆盖。"""
    if not scope.is_super:
        raise HTTPException(403, "仅超级管理员可上传")
    if user_json is not None:
        ingest_accounts(db, parse_user_json((await user_json.read()).decode("utf-8")), user_json.filename or "user.json")
        db.commit()
    if roster_xlsx is not None:
        ingest_roster(db, parse_roster_xlsx(await roster_xlsx.read()), dt.date.today(), roster_xlsx.filename or "roster.xlsx")
        db.commit()
    report = parse_weekly_report_html((await weekly_report_html.read()).decode("utf-8"))
    old = db.query(models.WeeklyUpload).filter_by(week_start=week_start, week_end=week_end).one_or_none()
    if old is not None:
        db.query(models.ProjectItem).filter_by(upload_id=old.id).delete()
        db.query(models.UserWeekSummary).filter_by(upload_id=old.id).delete()
        db.delete(old)
        db.commit()
    up = ingest_weekly_report(db, report, week_start, week_end, _label(week_start, week_end), weekly_report_html.filename or "weekly_report.html")
    up.status = "committed"
    db.commit()
    return {"upload_id": up.id, "label": up.label, "users": len(report.users)}
