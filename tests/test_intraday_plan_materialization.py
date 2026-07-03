from pathlib import Path
import json
import sqlite3

from trading_x.candidate_models import CandidateReport
from trading_x.candidate_snapshots import CandidateRunRecord, persist_candidate_run
from trading_x.db import init_db
from trading_x.intraday import materialize_intraday_plans
from trading_x.types import CandidateGrade, Confidence, DataCapabilityLevel, StrategyType


def test_materialize_intraday_plans_uses_latest_structured_candidate_snapshot(tmp_path: Path) -> None:
    db_path = tmp_path / "trading_x.db"
    init_db(db_path)
    _seed_reference_prices(db_path)
    persist_candidate_run(
        db_path,
        _run("run-1", "2026-07-01T16:00:00+00:00"),
        [_candidate()],
    )

    count = materialize_intraday_plans(db_path, "20260701")

    with sqlite3.connect(db_path) as conn:
        row = conn.execute(
            "SELECT entry_low, entry_high, breakout_price, stop_price, plan_json "
            "FROM intraday_plans WHERE trade_date = ? AND ts_code = ?",
            ("20260701", "300001.SZ"),
        ).fetchone()

    assert count == 1
    assert row[:4] == (20.1, 21.2, 21.0, 19.5)
    assert '"entry_low": 20.1' in row[4]


def test_materialize_intraday_plans_ignores_conflicting_snapshot_prose_prices(
    tmp_path: Path,
) -> None:
    db_path = tmp_path / "trading_x.db"
    init_db(db_path)
    _seed_reference_prices(db_path)
    persist_candidate_run(
        db_path,
        _run("run-conflicting-prose", "2026-07-01T16:00:30+00:00"),
        [_candidate()],
    )
    with sqlite3.connect(db_path) as conn:
        plan_json = json.dumps(
            {
                "entry_low": 20.1,
                "entry_high": 21.2,
                "breakout_price": 21.0,
                "stop_price": 19.5,
                "buy_observation": "free text says buy 99.99",
                "max_chase_limit": "free text says breakout 88.88",
                "structural_stop": "free text says stop 1.11",
            },
            ensure_ascii=False,
            sort_keys=True,
        )
        conn.execute(
            "UPDATE candidate_snapshots SET plan_json = ? WHERE run_id = ?",
            (plan_json, "run-conflicting-prose"),
        )

    count = materialize_intraday_plans(db_path, "20260701")

    with sqlite3.connect(db_path) as conn:
        row = conn.execute(
            "SELECT entry_low, entry_high, breakout_price, stop_price "
            "FROM intraday_plans WHERE trade_date = ? AND ts_code = ?",
            ("20260701", "300001.SZ"),
        ).fetchone()

    assert count == 1
    assert row == (20.1, 21.2, 21.0, 19.5)


def test_materialize_intraday_plans_does_not_fallback_when_latest_snapshot_is_empty(
    tmp_path: Path,
) -> None:
    db_path = tmp_path / "trading_x.db"
    init_db(db_path)
    _seed_reference_prices(db_path)
    _seed_manual_candidate(db_path)
    persist_candidate_run(db_path, _run("run-empty", "2026-07-01T16:01:00+00:00"), [])

    count = materialize_intraday_plans(db_path, "20260701")

    with sqlite3.connect(db_path) as conn:
        plan_count = conn.execute("SELECT COUNT(*) FROM intraday_plans WHERE trade_date = ?", ("20260701",)).fetchone()[0]

    assert count == 0
    assert plan_count == 0


def test_materialize_intraday_plans_preserves_missing_snapshot_risk_budget(
    tmp_path: Path,
) -> None:
    db_path = tmp_path / "trading_x.db"
    init_db(db_path)
    _seed_reference_prices(db_path)
    persist_candidate_run(
        db_path,
        _run("run-missing-risk", "2026-07-01T16:02:00+00:00"),
        [_candidate(plan_max_position_cash=None, plan_max_loss=None)],
    )

    count = materialize_intraday_plans(db_path, "20260701")

    with sqlite3.connect(db_path) as conn:
        row = conn.execute(
            "SELECT max_position_cash, max_loss FROM intraday_plans WHERE trade_date = ? AND ts_code = ?",
            ("20260701", "300001.SZ"),
        ).fetchone()

    assert count == 1
    assert row == (0.0, 0.0)


def test_materialize_intraday_plans_preserves_missing_snapshot_plan_json(
    tmp_path: Path,
) -> None:
    db_path = tmp_path / "trading_x.db"
    init_db(db_path)
    _seed_reference_prices(db_path)
    persist_candidate_run(
        db_path,
        _run("run-missing-plan-json", "2026-07-01T16:03:00+00:00"),
        [_candidate()],
    )
    with sqlite3.connect(db_path) as conn:
        conn.execute("UPDATE candidate_snapshots SET plan_json = NULL WHERE run_id = ?", ("run-missing-plan-json",))

    count = materialize_intraday_plans(db_path, "20260701")

    with sqlite3.connect(db_path) as conn:
        plan_json = conn.execute(
            "SELECT plan_json FROM intraday_plans WHERE trade_date = ? AND ts_code = ?",
            ("20260701", "300001.SZ"),
        ).fetchone()[0]

    assert count == 1
    assert plan_json == ""


def test_materialize_intraday_plans_preserves_malformed_snapshot_numbers(
    tmp_path: Path,
) -> None:
    db_path = tmp_path / "trading_x.db"
    init_db(db_path)
    _seed_reference_prices(db_path)
    persist_candidate_run(
        db_path,
        _run("run-malformed-number", "2026-07-01T16:04:00+00:00"),
        [_candidate()],
    )
    with sqlite3.connect(db_path) as conn:
        conn.execute("UPDATE candidate_snapshots SET entry_low = ? WHERE run_id = ?", ("bad", "run-malformed-number"))

    count = materialize_intraday_plans(db_path, "20260701")

    with sqlite3.connect(db_path) as conn:
        entry_low = conn.execute(
            "SELECT entry_low FROM intraday_plans WHERE trade_date = ? AND ts_code = ?",
            ("20260701", "300001.SZ"),
        ).fetchone()[0]

    assert count == 1
    assert entry_low == 0.0


def test_materialize_intraday_plans_breaks_snapshot_run_timestamp_ties(
    tmp_path: Path,
) -> None:
    db_path = tmp_path / "trading_x.db"
    init_db(db_path)
    _seed_reference_prices(db_path)
    generated_at = "2026-07-01T16:05:00+00:00"
    persist_candidate_run(db_path, _run("run-a", generated_at), [_candidate()])
    persist_candidate_run(db_path, _run("run-b", generated_at), [_candidate()])
    with sqlite3.connect(db_path) as conn:
        conn.execute(
            "UPDATE candidate_snapshots SET entry_low = ?, entry_high = ?, "
            "breakout_price = ?, stop_price = ? WHERE run_id = ?",
            (22.1, 22.8, 22.5, 21.6, "run-b"),
        )

    count = materialize_intraday_plans(db_path, "20260701")

    with sqlite3.connect(db_path) as conn:
        row = conn.execute(
            "SELECT source_candidate_id, entry_low FROM intraday_plans WHERE trade_date = ? AND ts_code = ?",
            ("20260701", "300001.SZ"),
        ).fetchone()
    assert count == 1
    assert row == ("run-b:300001.SZ:B_CAPACITY_LEADER", 22.1)


def _seed_reference_prices(db_path: Path) -> None:
    with sqlite3.connect(db_path) as conn:
        conn.execute(
            "INSERT INTO daily_quotes ("
            "trade_date, ts_code, open, high, low, close, pre_close, pct_chg, vol, amount"
            ") VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            ("20260701", "300001.SZ", 10.0, 10.8, 9.8, 10.2, 9.9, 2.0, 1000.0, 100000.0),
        )
        conn.execute(
            "INSERT INTO stk_limit_prices (trade_date, ts_code, pre_close, up_limit, down_limit) "
            "VALUES (?, ?, ?, ?, ?)",
            ("20260701", "300001.SZ", 10.0, 11.0, 9.0),
        )


def _seed_manual_candidate(db_path: Path) -> None:
    with sqlite3.connect(db_path) as conn:
        conn.execute(
            "INSERT INTO candidates (trade_date, ts_code, strategy_type, candidate_grade, risk_pass) "
            "VALUES (?, ?, ?, ?, ?)",
            ("20260701", "300001.SZ", StrategyType.B_CAPACITY_LEADER, CandidateGrade.B_CORE, 1),
        )


def _run(run_id: str, generated_at: str) -> CandidateRunRecord:
    return CandidateRunRecord(
        run_id=run_id,
        trade_date="20260701",
        system_version="v1.0",
        strategy_version="rules-v1",
        threshold_version="threshold-v1",
        config_hash="config-hash",
        data_capability=DataCapabilityLevel.BASIC_WITH_THEME_FALLBACK,
        p0_complete=True,
        theme_coverage_ratio=1.0,
        generated_at=generated_at,
        report_json_path=Path("reports/20260701_report.json"),
        report_md_path=Path("reports/20260701_report.md"),
        notes=None,
    )


def _candidate(
    plan_max_position_cash: float | None = 12000.0,
    plan_max_loss: float | None = 600.0,
) -> CandidateReport:
    return CandidateReport(
        ts_code="300001.SZ",
        name="容量龙",
        strategy_type=StrategyType.B_CAPACITY_LEADER,
        candidate_grade=CandidateGrade.B_CORE,
        theme_name="机器人",
        theme_tags="机器人;智能制造",
        theme_rank_today=1,
        theme_strength_score=88.0,
        theme_position="成交额第 1，涨幅第 2",
        entry_reason="所属机器人题材今日强度排名第 1。",
        veto_items="P0 风控通过。",
        buy_observation="明日只观察放量突破或回踩承接。",
        abandon_conditions="跌回平台内则放弃。",
        max_chase_limit="不追高超过计划买点 5%。",
        structural_stop="跌破当日低点 19.50。",
        suggested_position="观察仓 10%-20%。",
        max_loss="单笔最大亏损控制在总资金 1% 内。",
        data_confidence=Confidence.MEDIUM,
        theme_confidence=Confidence.MEDIUM,
        event_confidence=Confidence.UNAVAILABLE,
        plan_entry_low=20.1,
        plan_entry_high=21.2,
        plan_breakout_price=21.0,
        plan_stop_price=19.5,
        plan_max_position_cash=plan_max_position_cash,
        plan_max_loss=plan_max_loss,
    )
