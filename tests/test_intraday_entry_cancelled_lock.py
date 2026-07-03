from pathlib import Path
import sqlite3

import pytest

from intraday_replay_fixtures import PlanFixture, alert_rows, insert_plan, write_replay_csv
from trading_x.db import init_db
from trading_x.intraday import run_replay


def test_entry_cancelled_lock_blocks_later_buy_trigger(tmp_path: Path) -> None:
    db_path = tmp_path / "trading_x.db"
    input_path = tmp_path / "replay.csv"
    init_db(db_path)
    insert_plan(db_path, PlanFixture(official_pre_close=10.0, volume_min_abs_amount=1000.0))
    write_replay_csv(
        input_path,
        "20260630,09:36:00,300001.SZ,9.70,10000,1000,9.80,9.70\n"
        "20260630,09:40:00,300001.SZ,12.00,11000,1000,12.10,11.90\n",
    )

    run_replay(db_path, "20260630", input_path, tmp_path / "reports")

    assert alert_rows(db_path) == [("ENTRY_CANCELLED", "ENTRY_CANCELLED_PRICE_OUT_OF_RANGE")]


def test_stop_break_after_buy_trigger_keeps_price_out_of_range_reason(tmp_path: Path) -> None:
    db_path = tmp_path / "trading_x.db"
    input_path = tmp_path / "replay.csv"
    init_db(db_path)
    insert_plan(db_path, PlanFixture(official_pre_close=10.0, volume_min_abs_amount=1000.0))
    write_replay_csv(
        input_path,
        "20260630,09:36:00,300001.SZ,11.50,10000,1000,11.60,11.40\n"
        "20260630,09:40:00,300001.SZ,9.70,11000,1100,9.80,9.70\n",
    )

    run_replay(db_path, "20260630", input_path, tmp_path / "reports")

    assert alert_rows(db_path) == [
        ("BUY_TRIGGER", "B_BUY_TRIGGERED"),
        ("ENTRY_CANCELLED", "ENTRY_CANCELLED_PRICE_OUT_OF_RANGE"),
    ]


def test_lock_rows_keep_alert_rule_and_created_time(tmp_path: Path) -> None:
    db_path = tmp_path / "trading_x.db"
    input_path = tmp_path / "replay.csv"
    init_db(db_path)
    insert_plan(db_path, PlanFixture(official_pre_close=10.0, volume_min_abs_amount=1000.0))
    write_replay_csv(
        input_path,
        "20260630,09:36:00,300001.SZ,11.50,10000,1000,11.60,11.40\n"
        "20260630,09:40:00,300001.SZ,9.70,11000,1100,9.80,9.70\n",
    )

    run_replay(db_path, "20260630", input_path, tmp_path / "reports")

    with sqlite3.connect(db_path) as conn:
        rows = conn.execute(
            "SELECT a.alert_type, l.locked, l.locked_at, a.created_at, l.rule_id, "
            "a.reason_code, l.reset_count, l.reset_reason "
            "FROM intraday_alerts a JOIN intraday_alert_locks l "
            "ON a.trade_date = l.trade_date AND a.ts_code = l.ts_code "
            "AND a.strategy_type = l.strategy_type AND a.alert_type = l.alert_type "
            "ORDER BY a.id"
        ).fetchall()
    assert [(row[0], row[1], row[4], row[5]) for row in rows] == [
        ("BUY_TRIGGER", 1, "B_BUY_TRIGGERED", "B_BUY_TRIGGERED"),
        (
            "ENTRY_CANCELLED",
            1,
            "ENTRY_CANCELLED_PRICE_OUT_OF_RANGE",
            "ENTRY_CANCELLED_PRICE_OUT_OF_RANGE",
        ),
    ]
    assert [(row[2], row[3]) for row in rows] == [(row[3], row[3]) for row in rows]
    assert [(row[6], row[7]) for row in rows] == [(0, None), (0, None)]


@pytest.mark.parametrize(
    ("replay_rows", "expected_state_before"),
    [
        (
            "20260630,09:36:00,300001.SZ,9.70,10000,1000,9.80,9.70\n",
            "OPEN_OBSERVING",
        ),
        (
            "20260630,09:36:00,300001.SZ,11.50,10000,1000,11.60,11.40\n"
            "20260630,09:40:00,300001.SZ,9.70,11000,1100,9.80,9.70\n",
            "ENTRY_ARMED",
        ),
    ],
)
def test_entry_cancelled_keeps_state_transition(
    tmp_path: Path,
    replay_rows: str,
    expected_state_before: str,
) -> None:
    db_path = tmp_path / "trading_x.db"
    input_path = tmp_path / "replay.csv"
    init_db(db_path)
    insert_plan(db_path, PlanFixture(official_pre_close=10.0, volume_min_abs_amount=1000.0))
    write_replay_csv(input_path, replay_rows)

    run_replay(db_path, "20260630", input_path, tmp_path / "reports")

    with sqlite3.connect(db_path) as conn:
        state_row = conn.execute(
            "SELECT state_before, state_after FROM intraday_alerts WHERE alert_type = ?",
            ("ENTRY_CANCELLED",),
        ).fetchone()
    assert state_row == (expected_state_before, "ENTRY_CANCELLED")


@pytest.mark.parametrize(
    ("row", "volume_min_abs_amount", "expected_alert"),
    [
        (
            "20260630,09:36:00,300001.SZ,12.00,1000,100,12.00,11.80\n",
            10_000_000.0,
            ("WATCH", "VOLUME_GATE_FAILED"),
        ),
        (
            "20260630,09:36:00,300001.SZ,10.50,10000,1000,10.50,10.20\n",
            1000.0,
            ("BUY_READY", "B_BREAKOUT_READY"),
        ),
    ],
)
def test_observation_alert_does_not_create_alert_lock(
    tmp_path: Path,
    row: str,
    volume_min_abs_amount: float,
    expected_alert: tuple[str, str],
) -> None:
    db_path = tmp_path / "trading_x.db"
    input_path = tmp_path / "replay.csv"
    init_db(db_path)
    insert_plan(db_path, PlanFixture(official_pre_close=10.0, volume_min_abs_amount=volume_min_abs_amount))
    write_replay_csv(input_path, row)

    run_replay(db_path, "20260630", input_path, tmp_path / "reports")

    with sqlite3.connect(db_path) as conn:
        lock_rows = conn.execute("SELECT alert_type FROM intraday_alert_locks").fetchall()
    assert alert_rows(db_path) == [expected_alert]
    assert lock_rows == []
