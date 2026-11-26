"""用 临时后台开发数据包/数据源 里的原始文件初始化本地库：python -m scripts.seed_local [数据源目录]"""
from __future__ import annotations

import datetime as dt
import glob
import re
import sys
from pathlib import Path

from app.database import SessionLocal, init_db
from app.etl.exclusions import seed_default_exclusion_rules
from app.etl.ingest import ingest_accounts, ingest_roster, ingest_weekly_report
from app.etl.parse_roster_xlsx import parse_roster_xlsx
from app.etl.parse_user_json import parse_user_json
from app.etl.parse_weekly_report import parse_weekly_report_html
from app import models

DEFAULT = Path(__file__).resolve().parents[2] / "临时后台开发数据包" / "数据源"


def main(src: Path):
    init_db()
    db = SessionLocal()
    try:
        seed_default_exclusion_rules(db)
        ingest_accounts(db, parse_user_json((src / "user.json").read_text("utf-8")), "user.json")
        xl = sorted(glob.glob(str(src / "用户批量导出*.xlsx")))[-1]
        ingest_roster(db, parse_roster_xlsx(Path(xl).read_bytes()), dt.date.today(), Path(xl).name)
        db.commit()
        for f in sorted(glob.glob(str(src / "weekly_report_*.html"))):
            m = re.search(r"(\d{8})_(\d{8})", f)
            s, e = (dt.datetime.strptime(x, "%Y%m%d").date() for x in m.groups())
            if db.query(models.WeeklyUpload).filter_by(week_start=s, week_end=e).first():
                continue
            up = ingest_weekly_report(db, parse_weekly_report_html(Path(f).read_text("utf-8")), s, e, f"{s.month}.{s.day:02d}–{e.month}.{e.day:02d}", Path(f).name)
            up.status = "committed"
            db.commit()
            print("ingested", Path(f).name)
    finally:
        db.close()


if __name__ == "__main__":
    main(Path(sys.argv[1]) if len(sys.argv) > 1 else DEFAULT)
