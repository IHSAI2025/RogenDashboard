"""PRD 最新版 三·0 / 三·2 / 三·3：使用、休眠、沉默、登录未使用 的口径(合成数据，不依赖数据源文件)。"""
import datetime as dt

from app.metrics import engine as E
from app.vendor import dataset as D

d = dt.date
START, END = d(2026, 9, 1), d(2026, 9, 30)


def acc(i, opened=d(2026, 7, 1)):
    return D.AccountRec(id=i, name=f"u{i}", phone="13800000000", da="BC", region="东区", circle_lead=None, identity="员工",
                        account_type="PLUS", source_tag="采购", status="正常", opened_at=opened, disabled_at=None,
                        first_login_at=opened)


def build(events, accounts):
    ds = D.Dataset(accounts=accounts, events=events, costs=[], quotas={}, as_of=dt.datetime(2026, 9, 30, 23, 59))
    return E.period_bundle(ds, E.Index(ds), accounts, START, END)


def state_of(b, a):
    return b["state"][a.id]


def test_login_only_is_not_use():
    a = acc(1)
    b = build([D.Event(1, d(2026, 9, 5), D.LOGIN), D.Event(1, d(2026, 8, 20), D.PUBMED)], [a])
    assert state_of(b, a) == "休眠"          # 8/20 在 60 天窗口内 → 不是沉默
    assert b["n_active"] == 0 and b["n_login_unused_dormant"] == 1


def test_failed_generation_and_export_do_not_count_as_use_but_count_as_ops():
    a = acc(2)
    ev = [D.Event(2, d(2026, 9, 3), D.PPT_GEN, ok=False), D.Event(2, d(2026, 9, 4), D.PPT_EXP), D.Event(2, d(2026, 8, 25), D.SHARE)]
    b = build(ev, [a])
    assert state_of(b, a) == "休眠"
    assert b["ops_total"] == 1               # 周期内只有失败的生成算有效功能操作(8/25 的分享在周期之前)
    assert b["gen_total"] == 0 and b["exp_total"] == 1


def test_successful_generation_is_active():
    a = acc(3)
    b = build([D.Event(3, d(2026, 9, 3), D.TWEET_GEN, ok=True)], [a])
    assert state_of(b, a) == "活跃" and b["n_active"] == 1
    assert len(b["stats"][3].days) == 1       # 活跃天数 = 有使用记录的去重自然日


def test_silent_needs_60_days_no_use_and_opened_60_days():
    old_silent = acc(4)                        # 7/1 开通，7/15 后再无使用
    new_unused = acc(5, opened=d(2026, 9, 10))  # 开通不满 60 天
    ev = [D.Event(4, d(2026, 7, 15), D.PUBMED), D.Event(4, d(2026, 9, 12), D.LOGIN)]
    b = build(ev, [old_silent, new_unused])
    assert state_of(b, old_silent) == "沉默"
    assert state_of(b, new_unused) == "休眠"   # 开通未满 60 天不判沉默
    assert b["n_login_unused_silent"] == 1 and b["n_login_unused_dormant"] == 0


def test_silent_boundary_exactly_60_days():
    a = acc(6)
    # 截止日 9/30 往前连续 60 天 = 8/2 ~ 9/30；8/2 有使用 → 不是沉默；8/1 有使用 → 沉默
    assert state_of(build([D.Event(6, d(2026, 8, 2), D.PUBMED)], [a]), a) == "休眠"
    assert state_of(build([D.Event(6, d(2026, 8, 1), D.PUBMED)], [a]), a) == "沉默"


def test_states_partition_valid_accounts():
    accs = [acc(i) for i in range(10, 16)]
    ev = [D.Event(10, d(2026, 9, 2), D.PUBMED), D.Event(11, d(2026, 8, 10), D.OUTLINE), D.Event(12, d(2026, 9, 9), D.LOGIN)]
    b = build(ev, accs)
    assert b["n_active"] + b["n_dormant"] + b["n_silent"] == b["n_valid"] == 6


def _row(key, valid, ops, per_active):
    return {"key": key, "valid": {"value": valid}, "ops": {"value": ops}, "ops_per_active": {"value": per_active}}


def test_low_usage_risk_depth_and_scale():
    """PRD 2.2「功能使用规模或使用深度偏低」：阈值为暂定预警线(config.WARN_*_RATIO=50%)。"""
    from app.insight.text import low_usage
    rows = [_row("A", 20, 400, 20.0), _row("B", 20, 380, 19.0), _row("C", 20, 90, 4.0), _row("待映射", 20, 1, 0.1), _row("D", 3, 1, 0.1)]
    low = low_usage(rows, overall_per_active=15.0)
    assert [k for k, _ in low["depth"]] == ["C"]       # 4.0 < 15×50%；「待映射」与有效账号<5 的分组不参与
    assert [k for k, _ in low["scale"]] == ["C"]       # 90 < 均值((400+380+90)/3=290)×50%


def test_silent_requires_opened_at_least_60_days_boundary():
    """开通满 60 天才判沉默：截止日 9/30，8/1 开通=满 60 天(沉默)，8/2 开通=59 天(休眠)；30~59 天一律休眠。"""
    a60, a59, a46 = acc(20, opened=d(2026, 8, 1)), acc(21, opened=d(2026, 8, 2)), acc(22, opened=d(2026, 8, 15))
    b = build([], [a60, a59, a46])
    assert (state_of(b, a60), state_of(b, a59), state_of(b, a46)) == ("沉默", "休眠", "休眠")
