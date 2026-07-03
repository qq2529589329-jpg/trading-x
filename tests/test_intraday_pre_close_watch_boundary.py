from pathlib import Path
import sqlite3

from intraday_replay_fixtures import PlanFixture, alert_rows, insert_plan, write_replay_csv
from trading_x.db import init_db
from trading_x.intraday import run_replay


def test_missing_pre_close_watch_stays_observing_without_lock(tmp_path: Path) -> None:
    db_path = tmp_path / "trading_x.db"
    input_path = tmp_path / "replay.csv"
    init_db(db_path)
    insert_plan(db_path, PlanFixture(official_pre_close=0.0, volume_min_abs_amount=1000.0))
    write_replay_csv(
        input_path,
        "20260630,09:36:00,300001.SZ,12.00,10000,1000,12.00,11.80\n",
    )

    run_replay(db_path, "20260630", input_path, tmp_path / "reports")

    with sqlite3.connect(db_path) as conn:
        state_row = conn.execute(
            "SELECT state_before, state_after FROM intraday_alerts WHERE reason_code = ?",
            ("PRE_CLOSE_MISSING",),
        ).fetchone()
        lock_rows = conn.execute("SELECT alert_type FROM intraday_alert_locks").fetchall()
    assert alert_rows(db_path) == [("WATCH", "PRE_CLOSE_MISSING")]
    assert state_row == ("OPEN_OBSERVING", "OPEN_OBSERVING")
    assert lock_rows == []
