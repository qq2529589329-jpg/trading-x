from pathlib import Path
import sqlite3

from intraday_replay_fixtures import PlanFixture, alert_rows, insert_plan, write_replay_csv
from trading_x.db import init_db
from trading_x.intraday import run_replay


def test_replay_never_emits_sell_trigger_when_triggered_plan_breaks_stop(tmp_path: Path) -> None:
    db_path = tmp_path / "trading_x.db"
    input_path = tmp_path / "replay.csv"
    init_db(db_path)
    insert_plan(db_path, PlanFixture(official_pre_close=10.0, volume_min_abs_amount=1000.0))
    write_replay_csv(
        input_path,
        "20260630,09:36:00,300001.SZ,12.00,11000,1000,12.10,11.90\n"
        "20260630,09:40:00,300001.SZ,9.70,12000,1000,9.80,9.60\n",
    )

    run_replay(db_path, "20260630", input_path, tmp_path / "reports")

    with sqlite3.connect(db_path) as conn:
        sell_count = conn.execute(
            "SELECT COUNT(*) FROM intraday_alerts WHERE alert_type = ?",
            ("SELL_TRIGGER",),
        ).fetchone()[0]

    assert alert_rows(db_path) == [
        ("BUY_TRIGGER", "B_BUY_TRIGGERED"),
        ("ENTRY_CANCELLED", "ENTRY_CANCELLED_PRICE_OUT_OF_RANGE"),
    ]
    assert sell_count == 0
