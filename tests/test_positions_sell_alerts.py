from pathlib import Path
import sqlite3

from intraday_replay_fixtures import PlanFixture, alert_rows, insert_plan, write_replay_csv
from trading_x.db import init_db
from trading_x.intraday import run_replay


def test_no_position_stop_break_still_emits_entry_cancelled_only(tmp_path: Path) -> None:
    db_path = tmp_path / "trading_x.db"
    input_path = tmp_path / "replay.csv"
    init_db(db_path)
    insert_plan(db_path, PlanFixture(official_pre_close=10.0, volume_min_abs_amount=1000.0))
    write_replay_csv(input_path, "20260630,09:36:00,300001.SZ,9.70,10000,1000,9.80,9.70\n")

    run_replay(db_path, "20260630", input_path, tmp_path / "reports")

    assert alert_rows(db_path) == [("ENTRY_CANCELLED", "ENTRY_CANCELLED_PRICE_OUT_OF_RANGE")]
    assert _sell_side_alert_count(db_path) == 0


def test_held_position_stop_break_emits_sell_trigger(tmp_path: Path) -> None:
    db_path = tmp_path / "trading_x.db"
    input_path = tmp_path / "replay.csv"
    init_db(db_path)
    insert_plan(db_path, PlanFixture(official_pre_close=10.0, volume_min_abs_amount=1000.0))
    _insert_position(db_path, available_shares=500.0)
    write_replay_csv(input_path, "20260630,09:36:00,300001.SZ,9.70,10000,1000,9.80,9.70\n")

    run_replay(db_path, "20260630", input_path, tmp_path / "reports")

    assert alert_rows(db_path) == [("SELL_TRIGGER", "SELL_TRIGGER_STOP_BREAK")]


def test_zero_available_position_stop_break_emits_t1_risk_only(tmp_path: Path) -> None:
    db_path = tmp_path / "trading_x.db"
    input_path = tmp_path / "replay.csv"
    init_db(db_path)
    insert_plan(db_path, PlanFixture(official_pre_close=10.0, volume_min_abs_amount=1000.0))
    _insert_position(db_path, available_shares=0.0)
    write_replay_csv(input_path, "20260630,09:36:00,300001.SZ,9.70,10000,1000,9.80,9.70\n")

    run_replay(db_path, "20260630", input_path, tmp_path / "reports")

    assert alert_rows(db_path) == [("RISK_ALERT", "SELL_BLOCKED_T1_NO_AVAILABLE_SHARES")]
    assert _sell_trigger_count(db_path) == 0


def _insert_position(db_path: Path, *, available_shares: float) -> None:
    with sqlite3.connect(db_path) as conn:
        conn.execute(
            "INSERT INTO positions ("
            "trade_date, ts_code, name, total_shares, available_shares, avg_cost, market_value, "
            "source, source_run_id, created_at"
            ") VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (
                "20260630",
                "300001.SZ",
                "容量龙",
                500.0,
                available_shares,
                10.2,
                5100.0,
                "fixture",
                1,
                "2026-06-30T09:00:00",
            ),
        )


def _sell_side_alert_count(db_path: Path) -> int:
    with sqlite3.connect(db_path) as conn:
        return int(
            conn.execute(
                "SELECT COUNT(*) FROM intraday_alerts WHERE alert_type IN (?, ?, ?)",
                ("SELL_TRIGGER", "SELL_WARN", "RISK_ALERT"),
            ).fetchone()[0]
        )


def _sell_trigger_count(db_path: Path) -> int:
    with sqlite3.connect(db_path) as conn:
        return int(
            conn.execute(
                "SELECT COUNT(*) FROM intraday_alerts WHERE alert_type = ?",
                ("SELL_TRIGGER",),
            ).fetchone()[0]
        )
