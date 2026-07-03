from pathlib import Path

from intraday_replay_fixtures import PlanFixture, alert_rows, insert_plan, write_replay_csv
from trading_x.db import init_db
from trading_x.intraday import run_replay


def test_entry_cancelled_takes_priority_when_volume_is_missing(tmp_path: Path) -> None:
    db_path = tmp_path / "trading_x.db"
    input_path = tmp_path / "replay.csv"
    init_db(db_path)
    insert_plan(db_path, PlanFixture(official_pre_close=10.0, volume_min_abs_amount=1000.0))
    write_replay_csv(input_path, "20260630,09:36:00,300001.SZ,9.70,10000,0,9.80,9.70\n")

    run_replay(db_path, "20260630", input_path, tmp_path / "reports")

    assert alert_rows(db_path) == [("ENTRY_CANCELLED", "ENTRY_CANCELLED_PRICE_OUT_OF_RANGE")]


def test_entry_cancelled_before_vwap_active_time_blocks_later_buy_trigger(tmp_path: Path) -> None:
    db_path = tmp_path / "trading_x.db"
    input_path = tmp_path / "replay.csv"
    init_db(db_path)
    insert_plan(db_path, PlanFixture(official_pre_close=10.0, volume_min_abs_amount=1000.0))
    write_replay_csv(
        input_path,
        "20260630,09:34:00,300001.SZ,9.70,10000,1000,9.80,9.70\n"
        "20260630,09:36:00,300001.SZ,11.50,11000,1000,11.60,11.40\n",
    )

    run_replay(db_path, "20260630", input_path, tmp_path / "reports")

    assert alert_rows(db_path) == [("ENTRY_CANCELLED", "ENTRY_CANCELLED_PRICE_OUT_OF_RANGE")]
