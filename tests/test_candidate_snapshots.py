from pathlib import Path
from dataclasses import replace
import json
import sqlite3

from trading_x.candidate_models import CandidateReport
from trading_x.candidate_snapshots import CandidateRunRecord, persist_candidate_run
from trading_x.db import init_db
from trading_x.types import CandidateGrade, Confidence, DataCapabilityLevel, StrategyType


def test_persist_candidate_run_keeps_each_report_run(tmp_path: Path) -> None:
    db_path = tmp_path / "trading_x.db"
    init_db(db_path)

    persist_candidate_run(db_path, _run("run-1", "2026-07-01T16:00:00+00:00"), [_candidate("300001.SZ")])
    persist_candidate_run(db_path, _run("run-2", "2026-07-01T16:01:00+00:00"), [_candidate("300002.SZ")])

    with sqlite3.connect(db_path) as conn:
        run_count = conn.execute("SELECT COUNT(*) FROM candidate_runs").fetchone()[0]
        snapshots = conn.execute(
            "SELECT run_id, rank, ts_code FROM candidate_snapshots ORDER BY created_at"
        ).fetchall()

    assert run_count == 2
    assert snapshots == [("run-1", 1, "300001.SZ"), ("run-2", 1, "300002.SZ")]


def test_candidates_latest_reads_latest_snapshot_run(tmp_path: Path) -> None:
    db_path = tmp_path / "trading_x.db"
    init_db(db_path)

    persist_candidate_run(db_path, _run("run-1", "2026-07-01T16:00:00+00:00"), [_candidate("300001.SZ")])
    persist_candidate_run(db_path, _run("run-2", "2026-07-01T16:01:00+00:00"), [_candidate("300002.SZ")])

    with sqlite3.connect(db_path) as conn:
        rows = conn.execute(
            "SELECT run_id, ts_code FROM candidates_latest ORDER BY rank"
        ).fetchall()

    assert rows == [("run-2", "300002.SZ")]


def test_candidates_latest_is_empty_when_latest_run_has_no_candidates(
    tmp_path: Path,
) -> None:
    db_path = tmp_path / "trading_x.db"
    init_db(db_path)

    persist_candidate_run(db_path, _run("run-1", "2026-07-01T16:00:00+00:00"), [_candidate("300001.SZ")])
    persist_candidate_run(db_path, _run("run-2", "2026-07-01T16:01:00+00:00"), [])

    with sqlite3.connect(db_path) as conn:
        rows = conn.execute("SELECT run_id, ts_code FROM candidates_latest").fetchall()

    assert rows == []


def test_candidate_snapshot_stores_reasons_and_plan_json(tmp_path: Path) -> None:
    db_path = tmp_path / "trading_x.db"
    init_db(db_path)

    candidate = replace(
        _candidate("300001.SZ"),
        plan_max_position_cash=12000.0,
        plan_max_loss=600.0,
    )
    persist_candidate_run(db_path, _run("run-1", "2026-07-01T16:00:00+00:00"), [candidate])

    with sqlite3.connect(db_path) as conn:
        row = conn.execute(
            "SELECT include_reasons_json, reject_reasons_json, plan_json "
            "FROM candidate_snapshots WHERE run_id = ?",
            ("run-1",),
        ).fetchone()

    assert json.loads(row[0]) == ["所属机器人题材今日强度排名第 1。"]
    assert json.loads(row[1]) == ["P0 风控通过。"]
    plan = json.loads(row[2])
    assert plan["buy_observation"] == "明日只观察放量突破或回踩承接。"
    assert plan["max_position_cash"] == 12000.0
    assert plan["max_loss"] == 600.0
    assert plan["max_loss_text"] == "单笔最大亏损控制在总资金 1% 内。"
    assert "plan_max_loss" not in plan


def test_candidate_snapshot_stores_structured_plan_prices(tmp_path: Path) -> None:
    db_path = tmp_path / "trading_x.db"
    init_db(db_path)

    persist_candidate_run(
        db_path,
        _run("run-1", "2026-07-01T16:00:00+00:00"),
        [
            _candidate(
                "300001.SZ",
                plan_entry_low=20.1,
                plan_entry_high=21.2,
                plan_breakout_price=21.0,
                plan_stop_price=19.5,
            )
        ],
    )

    with sqlite3.connect(db_path) as conn:
        row = conn.execute(
            "SELECT entry_low, entry_high, breakout_price, stop_price, plan_json "
            "FROM candidate_snapshots WHERE run_id = ?",
            ("run-1",),
        ).fetchone()

    assert row[:4] == (20.1, 21.2, 21.0, 19.5)
    assert json.loads(row[4])["breakout_price"] == 21.0


def test_init_db_migrates_existing_candidate_snapshots_for_structured_plan_fields(
    tmp_path: Path,
) -> None:
    db_path = tmp_path / "trading_x.db"
    with sqlite3.connect(db_path) as conn:
        conn.execute(
            "CREATE TABLE candidate_snapshots ("
            "run_id TEXT, trade_date TEXT, rank INTEGER, ts_code TEXT, name TEXT, "
            "strategy_type TEXT, leader_status TEXT, theme_name TEXT, theme_confidence TEXT, "
            "theme_strength_score REAL, data_capability TEXT, include_reasons_json TEXT, "
            "reject_reasons_json TEXT, plan_json TEXT, created_at TEXT, "
            "PRIMARY KEY (run_id, ts_code, strategy_type)"
            ")"
        )
    init_db(db_path)

    persist_candidate_run(
        db_path,
        _run("run-migrated", "2026-07-01T16:02:00+00:00"),
        [
            _candidate(
                "300001.SZ",
                plan_entry_low=20.1,
                plan_entry_high=21.2,
                plan_breakout_price=21.0,
                plan_stop_price=19.5,
            )
        ],
    )

    with sqlite3.connect(db_path) as conn:
        row = conn.execute(
            "SELECT entry_low, entry_high, breakout_price, stop_price "
            "FROM candidate_snapshots WHERE run_id = ?",
            ("run-migrated",),
        ).fetchone()

    assert row == (20.1, 21.2, 21.0, 19.5)


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
    ts_code: str,
    plan_entry_low: float | None = None,
    plan_entry_high: float | None = None,
    plan_breakout_price: float | None = None,
    plan_stop_price: float | None = None,
) -> CandidateReport:
    return CandidateReport(
        ts_code=ts_code,
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
        structural_stop="跌破当日低点 19.80。",
        suggested_position="观察仓 10%-20%。",
        max_loss="单笔最大亏损控制在总资金 1% 内。",
        data_confidence=Confidence.MEDIUM,
        theme_confidence=Confidence.MEDIUM,
        event_confidence=Confidence.UNAVAILABLE,
        plan_entry_low=plan_entry_low,
        plan_entry_high=plan_entry_high,
        plan_breakout_price=plan_breakout_price,
        plan_stop_price=plan_stop_price,
    )
