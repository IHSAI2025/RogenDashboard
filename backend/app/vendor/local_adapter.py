"""本地适配器：三份上传文件(落在 SQLite) + mock 补齐 -> Dataset。

真实来源：
- 账号/身份：user.json(identity: customer/staff/other)，花名册 xlsx 的「用户身份」优先
- DA/账号类型/大区/备注：花名册 xlsx 最新快照
- PPT/推文生成、花费：weekly_report 逐项目明细(创建日期、花费；花费为空=未成功生成)
- 导出：weekly_report 只有每账号每周总数，没有日粒度 -> 摊到该周账号有生成的日期上(日期为推断，记入 mock_fields)
mock：登录、PubMed/大纲/内容库分享、PPT 子功能、来源标签、可用状态、开通/首次登录日期、大区、SUPER 账号占比、配额。
"""
from __future__ import annotations

import datetime as dt
from collections import defaultdict

from sqlalchemy.orm import Session

from .. import config, models
from ..etl.da_dict import ALL_DAS, da_code, is_test_da
from ..etl.exclusions import get_exclusion_map
from . import dataset as D
from .mock_fill import PPT_SUBS, REGIONS, h, pick, rand_date

LAUNCH = dt.date.fromisoformat(config.PLATFORM_LAUNCH_DATE)
TWEET_SUB = {"医学科普": "医学科普", "专业学术": "专业学术", "guideline": "指南/政策解读"}
IDENT_USER_JSON = {"customer": "客户", "staff": "员工", "other": "员工", "unknown": "员工"}


def _latest_roster(db: Session) -> dict[int, models.RosterEntry]:
    snap = db.query(models.RosterSnapshot).order_by(models.RosterSnapshot.id.desc()).first()
    if not snap:
        return {}
    out: dict[int, models.RosterEntry] = {}
    for e in db.query(models.RosterEntry).filter_by(snapshot_id=snap.id):
        if e.account_id is not None:
            out[e.account_id] = e
    return out


def _real_items(db: Session) -> list[models.ProjectItem]:
    """相邻周报在边界日重叠(如 08-17)：同账号同一天的项目只取最新一次上传的那批，避免重复计数。"""
    rows = db.query(models.ProjectItem).filter(models.ProjectItem.created_date.isnot(None)).all()
    latest: dict[tuple, int] = {}
    for r in rows:
        k = (r.account_id, r.created_date)
        latest[k] = max(latest.get(k, 0), r.upload_id)
    return [r for r in rows if r.upload_id == latest[(r.account_id, r.created_date)]]


def build_dataset(db: Session) -> D.Dataset:
    mock = config.MOCK_FILL
    mock_fields: set[str] = set()
    roster = _latest_roster(db)
    excl = get_exclusion_map(db)
    items = _real_items(db)

    first_seen: dict[int, dt.date] = {}
    for it in items:
        first_seen[it.account_id] = min(first_seen.get(it.account_id, it.created_date), it.created_date)
    as_of_day = max((it.created_date for it in items), default=dt.date.today())
    as_of = dt.datetime.combine(as_of_day, dt.time(23, 59))

    accounts: list[D.AccountRec] = []
    for a in db.query(models.Account).all():
        r = roster.get(a.id)
        raw_da = r.da_raw if r else None
        da = da_code(raw_da)
        identity = (r.identity_raw if r and r.identity_raw in ("客户", "员工") else None) or IDENT_USER_JSON.get(a.identity, "员工")
        if a.identity == "customer":
            identity = "客户"
        atype = None
        if r and r.account_type:
            atype = "SUPER" if "SUPER" in r.account_type.upper() else "PLUS"
        elif mock:
            atype = "PLUS"
        region = r.sales_region if r else None
        if not region and mock and da:
            region = pick(REGIONS, a.id, "region"); mock_fields.add("region")
        if mock and atype == "PLUS" and h(a.id, "super") < 0.18:
            atype = "SUPER"; mock_fields.add("account_type")
        # 账号开通 / 首次登录 / 状态 / 来源：真实值优先，其次 mock
        opened = a.opened_at
        if opened is None and mock:
            seen = first_seen.get(a.id)
            hi = min(seen, as_of_day) if seen else as_of_day - dt.timedelta(days=7)
            opened = rand_date(LAUNCH, max(hi, LAUNCH), a.id, "opened"); mock_fields.add("opened_at")
        first_login = a.first_login_at
        if first_login is None and mock and opened:
            seen = first_seen.get(a.id)
            if seen:
                first_login = max(opened, min(seen, opened + dt.timedelta(days=int(h(a.id, "fl") * 5))))
            elif h(a.id, "activated") < 0.7:
                first_login = min(opened + dt.timedelta(days=int(h(a.id, "fl2") * 20)), as_of_day)
            mock_fields.add("first_login_at")
        status = a.status or ("正常" if not mock else ("停用" if h(a.id, "status") < 0.05 else "正常"))
        disabled = a.disabled_at
        if status == "停用" and disabled is None and opened:
            disabled = min(as_of_day, rand_date(max(opened, LAUNCH) + dt.timedelta(days=5), as_of_day, a.id, "dis"))
        if a.status is None and mock:
            mock_fields.add("status")
        source = a.source_tag or (("采购" if h(a.id, "src") < 0.7 else "免费") if mock else None)
        if a.source_tag is None and mock:
            mock_fields.add("source_tag")
        test = is_test_da(raw_da) or a.id in excl or a.is_excluded
        accounts.append(D.AccountRec(
            id=a.id, name=a.user_name, phone=a.phone_number or "", da=da, region=region,
            circle_lead=(r.colleague if r else None), identity=identity, account_type=atype,
            source_tag=source, status=status, opened_at=opened, disabled_at=disabled,
            first_login_at=first_login, is_test=test, is_da=da is not None,
            remark=(r.remark if r else None),
        ))
    by_id = {a.id: a for a in accounts}

    events: list[D.Event] = []
    costs: list[D.CostRec] = []
    gen_days: dict[int, list[dt.date]] = defaultdict(list)
    for it in items:
        acc = by_id.get(it.account_id)
        ok = it.cost is not None
        if it.item_type == "ppt":
            kind, sub, fn = D.PPT_GEN, pick(PPT_SUBS, it.account_id, it.title, "pptsub"), "ppt"
            mock_fields.add("ppt_sub_function")
        else:
            kind, sub, fn = D.TWEET_GEN, TWEET_SUB.get(it.scene or "", pick(list(TWEET_SUB.values()), it.title)), "tweet"
        events.append(D.Event(it.account_id, it.created_date, kind, 1, ok, sub))
        if ok:
            gen_days[it.account_id].append(it.created_date)
            costs.append(D.CostRec(it.account_id, it.created_date, float(it.cost), fn))

    # 导出：每账号每周总数 -> 摊到该周内该账号有生成的日子(没有则落在周末)
    for s in db.query(models.UserWeekSummary).join(models.WeeklyUpload).filter(models.WeeklyUpload.is_seed.is_(False)):
        up = s.upload
        days = sorted(d for d in gen_days.get(s.account_id, []) if up.week_start <= d <= up.week_end) or [min(up.week_end, as_of_day)]
        for kind, n in ((D.PPT_EXP, s.ppt_export_count), (D.TWEET_EXP, s.article_export_count)):
            for i in range(n or 0):
                events.append(D.Event(s.account_id, days[i % len(days)], kind))
    if events:
        mock_fields.add("export_day")

    # mock：登录 / PubMed / 大纲 / 分享
    if mock:
        real_days: dict[int, set[dt.date]] = defaultdict(set)
        for e in events:
            real_days[e.account_id].add(e.day)
        for a in accounts:
            if a.opened_at is None:
                continue
            end = min(as_of_day, a.disabled_at or as_of_day)
            d = max(a.opened_at, LAUNCH)
            while d <= end:
                has_real = d in real_days[a.id]
                p_login = 0.9 if has_real else (0.05 + 0.25 * h(a.id, "freq")) if a.first_login_at and d >= a.first_login_at else 0
                if h(a.id, d, "login") < p_login:
                    events.append(D.Event(a.id, d, D.LOGIN))
                    if has_real and h(a.id, d, "pm") < 0.5:
                        events.append(D.Event(a.id, d, D.PUBMED, 1 + int(h(a.id, d, "pmn") * 3)))
                    if has_real and h(a.id, d, "ol") < 0.3:
                        events.append(D.Event(a.id, d, D.OUTLINE))
                    if has_real and h(a.id, d, "sh") < 0.12:
                        events.append(D.Event(a.id, d, D.SHARE))
                d += dt.timedelta(days=1)
        mock_fields.update(["login", "pubmed", "outline", "share"])

    # 配额：按 DA 取真实配置，缺失时 mock (PLUS 按实有账号放大一点，SUPER 小额)
    quotas: dict[tuple[str, str], int] = {}
    quota_history: dict[tuple[str, str], list] = defaultdict(list)
    for q in db.query(models.QuotaConfig).order_by(models.QuotaConfig.effective_from):
        quotas[(q.da_code, q.account_type)] = q.quota
        quota_history[(q.da_code, q.account_type)].append((q.effective_from, q.quota))
    if mock:
        cnt: dict[tuple[str, str], int] = defaultdict(int)
        for a in accounts:
            if a.account_type and not a.is_test:
                cnt[(a.da or "待映射", a.account_type)] += 1
        for da in ALL_DAS + ["待映射"]:
            for t, v in (("PLUS", max(10, round(cnt[(da, "PLUS")] * 1.25))), ("SUPER", max(3, round(cnt[(da, "SUPER")] * 1.5)))):
                if (da, t) not in quotas:
                    quotas[(da, t)] = v
                    quota_history[(da, t)].append((LAUNCH, v))
        mock_fields.add("quota")

    return D.Dataset(accounts, events, costs, quotas, as_of, "report-cny-v0", sorted(mock_fields), dict(quota_history))
