from pathlib import Path
import sqlite3

import pytest

from intraday_replay_fixtures import PlanFixture, insert_plan, write_replay_csv
from trading_x.db import init_db
from trading_x.intraday import run_replay


@pytest.mark.parametrize(
    ("replay_row", "plan_fixture", "alert_type", "expected_metadata"),
    [
        (
            "20260630,09:36:00,300001.SZ,12.00,1000,100,12.00,11.80\n",
            PlanFixture(official_pre_close=10.0, volume_min_abs_amount=10_000_000.0),
            "WATCH",
            ("LOW", "容量龙 WATCH", "VOLUME_GATE_FAILED"),
        ),
        (
            "20260630,09:36:00,300001.SZ,10.50,10000,1000,10.50,10.20\n",
            PlanFixture(official_pre_close=10.0, volume_min_abs_amount=1000.0),
            "BUY_READY",
            ("MEDIUM", "容量龙 BUY_READY", "B_BREAKOUT_READY"),
        ),
        (
            "20260630,09:36:00,300001.SZ,9.70,10000,1000,9.80,9.70\n",
            PlanFixture(official_pre_close=10.0, volume_min_abs_amount=1000.0),
            "ENTRY_CANCELLED",
            ("HIGH", "容量龙 ENTRY_CANCELLED", "ENTRY_CANCELLED_PRICE_OUT_OF_RANGE"),
        ),
    ],
)
def test_non_buy_trigger_alerts_keep_readable_metadata(
    tmp_path: Path,
    replay_row: str,
    plan_fixture: PlanFixture,
    alert_type: str,
    expected_metadata: tuple[str, str, str],
) -> None:
    db_path = tmp_path / "trading_x.db"
    input_path = tmp_path / "replay.csv"
    init_db(db_path)
    insert_plan(db_path, plan_fixture)
    write_replay_csv(input_path, replay_row)

    run_replay(db_path, "20260630", input_path, tmp_path / "reports")

    with sqlite3.connect(db_path) as conn:
        metadata_row = conn.execute(
            "SELECT severity, title, message FROM intraday_alerts WHERE alert_type = ?",
            (alert_type,),
        ).fetchone()
    assert metadata_row == expected_metadata
