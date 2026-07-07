from pathlib import Path
import sqlite3

from intraday_replay_fixtures import PlanFixture, alert_rows, insert_plan, write_replay_csv
from trading_x.db import init_db
from trading_x.intraday import run_replay


def test_init_db_migrates_existing_intraday_plans_for_replay(tmp_path: Path) -> None:
    db_path = tmp_path / "trading_x.db"
    input_path = tmp_path / "replay.csv"
    report_dir = tmp_path / "reports"
    with sqlite3.connect(db_path) as conn:
        conn.execute(
            "CREATE TABLE intraday_plans ("
            "trade_date TEXT, ts_code TEXT, strategy_type TEXT, entry_low REAL, "
            "entry_high REAL, breakout_price REAL, stop_price REAL, max_stop_distance REAL, "
            "vwap_active_after TEXT, volume_gate_enabled INTEGER, allow_trade INTEGER, system_version TEXT, "
            "PRIMARY KEY (trade_date, ts_code, strategy_type)"
            ")"
        )
    init_db(db_path)
    with sqlite3.connect(db_path) as conn:
        plan_columns = conn.execute("PRAGMA table_info(intraday_plans)").fetchall()
        pk_columns = tuple(
            row[1]
            for row in sorted(plan_columns, key=lambda row: row[5])
            if row[5] > 0
        )
        not_null_columns = {row[1] for row in plan_columns if row[3] > 0}
        column_names = {row[1] for row in plan_columns}
    insert_plan(db_path, PlanFixture(official_pre_close=10.0, volume_min_abs_amount=1000.0))
    write_replay_csv(input_path, "20260630,09:36:00,300001.SZ,12.00,11000,1000,12.00,11.80\n")

    result = run_replay(db_path, "20260630", input_path, report_dir)

    assert pk_columns == ("trade_date", "ts_code", "strategy_type")
    assert {"trade_date", "ts_code", "strategy_type"} <= not_null_columns
    assert "rule_version_at_signal" in column_names
    assert "rule_regime_at_signal" in column_names
    assert result.status == "SUCCESS"
    assert alert_rows(db_path) == [("BUY_TRIGGER", "B_BUY_TRIGGERED")]


def test_init_db_migrates_existing_intraday_output_tables_for_replay(tmp_path: Path) -> None:
    db_path = tmp_path / "trading_x.db"
    input_path = tmp_path / "replay.csv"
    report_dir = tmp_path / "reports"
    with sqlite3.connect(db_path) as conn:
        conn.execute(
            "CREATE TABLE intraday_alerts ("
            "trade_date TEXT, ts_code TEXT, strategy_type TEXT, alert_time TEXT, "
            "alert_type TEXT, reason_code TEXT"
            ")"
        )
        conn.execute(
            "CREATE TABLE intraday_alert_locks (trade_date TEXT, ts_code TEXT, strategy_type TEXT)"
        )
        conn.execute("CREATE TABLE intraday_replay_runs (trade_date TEXT)")
    init_db(db_path)
    insert_plan(db_path, PlanFixture(official_pre_close=10.0, volume_min_abs_amount=1000.0))
    write_replay_csv(input_path, "20260630,09:36:00,300001.SZ,12.00,11000,1000,12.00,11.80\n")

    result = run_replay(db_path, "20260630", input_path, report_dir)

    with sqlite3.connect(db_path) as conn:
        alert_columns = conn.execute("PRAGMA table_info(intraday_alerts)").fetchall()
        lock_columns = conn.execute("PRAGMA table_info(intraday_alert_locks)").fetchall()
        replay_run_columns = conn.execute("PRAGMA table_info(intraday_replay_runs)").fetchall()
        run_row = conn.execute(
            "SELECT id, status, alert_count FROM intraday_replay_runs WHERE trade_date = ?",
            ("20260630",),
        ).fetchone()
        alert_id = conn.execute(
            "SELECT id FROM intraday_alerts WHERE trade_date = ?",
            ("20260630",),
        ).fetchone()[0]
    required_alert_columns = {row[1] for row in alert_columns if row[3] > 0}
    required_lock_columns = {row[1] for row in lock_columns if row[3] > 0}
    required_replay_run_columns = {row[1] for row in replay_run_columns if row[3] > 0}
    alert_pk_columns = tuple(row[1] for row in sorted(alert_columns, key=lambda row: row[5]) if row[5] > 0)
    lock_pk_columns = tuple(row[1] for row in sorted(lock_columns, key=lambda row: row[5]) if row[5] > 0)
    replay_run_pk_columns = tuple(row[1] for row in sorted(replay_run_columns, key=lambda row: row[5]) if row[5] > 0)
    assert result.status == "SUCCESS"
    assert alert_pk_columns == ("id",)
    assert lock_pk_columns == ("trade_date", "ts_code", "strategy_type", "alert_type")
    assert replay_run_pk_columns == ("id",)
    assert {
        "trade_date",
        "ts_code",
        "strategy_type",
        "alert_time",
        "alert_type",
        "reason_code",
    } <= required_alert_columns
    assert {
        "trade_date",
        "ts_code",
        "strategy_type",
        "alert_type",
    } <= required_lock_columns
    assert {
        "trade_date",
        "input_file",
        "input_sha256",
        "plan_count",
        "alert_count",
        "status",
        "started_at",
        "ended_at",
    } <= required_replay_run_columns
    assert run_row == (1, "SUCCESS", 1)
    assert alert_id == 1
    assert alert_rows(db_path) == [("BUY_TRIGGER", "B_BUY_TRIGGERED")]


def test_init_db_migrates_existing_alert_lock_key_columns_to_required(
    tmp_path: Path,
) -> None:
    db_path = tmp_path / "trading_x.db"
    with sqlite3.connect(db_path) as conn:
        conn.execute(
            "CREATE TABLE intraday_alert_locks ("
            "trade_date TEXT, ts_code TEXT, strategy_type TEXT, alert_type TEXT, locked INTEGER, "
            "locked_at TEXT, rule_id TEXT, reset_count INTEGER DEFAULT 0, reset_reason TEXT, "
            "PRIMARY KEY (trade_date, ts_code, strategy_type, alert_type)"
            ")"
        )

    init_db(db_path)

    with sqlite3.connect(db_path) as conn:
        lock_columns = conn.execute("PRAGMA table_info(intraday_alert_locks)").fetchall()
    required_columns = {row[1] for row in lock_columns if row[3] > 0}
    assert {"trade_date", "ts_code", "strategy_type", "alert_type"} <= required_columns


def test_init_db_drops_legacy_replay_runs_missing_required_audit_fields(
    tmp_path: Path,
) -> None:
    db_path = tmp_path / "trading_x.db"
    with sqlite3.connect(db_path) as conn:
        conn.execute(
            "CREATE TABLE intraday_replay_runs ("
            "id INTEGER, trade_date TEXT, input_file TEXT, input_sha256 TEXT, "
            "plan_count INTEGER, alert_count INTEGER, status TEXT, started_at TEXT, "
            "ended_at TEXT, error_message TEXT"
            ")"
        )
        conn.execute(
            "INSERT INTO intraday_replay_runs VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (
                1,
                "20260630",
                "ok.csv",
                "hash",
                0,
                0,
                "SUCCESS",
                "2026-06-30T09:00:00+00:00",
                "2026-06-30T09:00:01+00:00",
                None,
            ),
        )
        conn.execute(
            "INSERT INTO intraday_replay_runs VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (
                2,
                "20260630",
                "bad.csv",
                None,
                0,
                0,
                "SUCCESS",
                "2026-06-30T09:00:00+00:00",
                "2026-06-30T09:00:01+00:00",
                None,
            ),
        )
        conn.execute(
            "INSERT INTO intraday_replay_runs VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (
                3,
                "20260630",
                "blank-status.csv",
                "hash",
                0,
                0,
                "   ",
                "2026-06-30T09:00:00+00:00",
                "2026-06-30T09:00:01+00:00",
                None,
            ),
        )
        conn.execute(
            "INSERT INTO intraday_replay_runs VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (
                4,
                "20260630",
                "broken-status.csv",
                "hash",
                0,
                0,
                "BROKEN",
                "2026-06-30T09:00:00+00:00",
                "2026-06-30T09:00:01+00:00",
                None,
            ),
        )

    init_db(db_path)

    with sqlite3.connect(db_path) as conn:
        rows = conn.execute(
            "SELECT trade_date, input_file, input_sha256, status FROM intraday_replay_runs"
        ).fetchall()
    assert rows == [("20260630", "ok.csv", "hash", "SUCCESS")]
