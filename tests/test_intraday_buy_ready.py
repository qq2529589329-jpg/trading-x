from pathlib import Path
import sqlite3

import pytest

from intraday_replay_fixtures import PlanFixture, alert_rows, insert_plan, write_replay_csv
from trading_x.db import init_db
from trading_x.intraday_replay import run_replay


def test_replay_writes_buy_ready_before_breakout(tmp_path: Path) -> None:
    db_path = tmp_path / "trading_x.db"
    input_path = tmp_path / "replay.csv"
    init_db(db_path)
    insert_plan(db_path, PlanFixture(official_pre_close=10.0, volume_min_abs_amount=1000.0))
    write_replay_csv(
        input_path,
        "20260630,09:36:00,300001.SZ,10.50,10000,1000,10.50,10.20\n",
    )

    run_replay(db_path, "20260630", input_path, tmp_path / "reports")

    assert alert_rows(db_path) == [("BUY_READY", "B_BREAKOUT_READY")]


@pytest.mark.parametrize(
    ("replay_row", "volume_min_abs_amount", "alert_type", "expected_state_after"),
    [
        (
            "20260630,09:36:00,300001.SZ,12.00,1000,100,12.00,11.80\n",
            10_000_000.0,
            "WATCH",
            "OPEN_OBSERVING",
        ),
        (
            "20260630,09:36:00,300001.SZ,10.50,10000,1000,10.50,10.20\n",
            1000.0,
            "BUY_READY",
            "BUY_READY",
        ),
    ],
)
def test_observation_alert_keeps_state_transition(
    tmp_path: Path,
    replay_row: str,
    volume_min_abs_amount: float,
    alert_type: str,
    expected_state_after: str,
) -> None:
    db_path = tmp_path / "trading_x.db"
    input_path = tmp_path / "replay.csv"
    init_db(db_path)
    insert_plan(db_path, PlanFixture(official_pre_close=10.0, volume_min_abs_amount=volume_min_abs_amount))
    write_replay_csv(input_path, replay_row)

    run_replay(db_path, "20260630", input_path, tmp_path / "reports")

    with sqlite3.connect(db_path) as conn:
        state_row = conn.execute(
            "SELECT state_before, state_after FROM intraday_alerts WHERE alert_type = ?",
            (alert_type,),
        ).fetchone()
    assert state_row == ("OPEN_OBSERVING", expected_state_after)
