from pathlib import Path
import sqlite3

import pytest

from intraday_replay_fixtures import PlanFixture, alert_rows, insert_plan, write_replay_csv
from trading_x.db import init_db
from trading_x.intraday import run_replay


@pytest.mark.parametrize(
    "update_sql",
    [
        "UPDATE intraday_plans SET entry_low = 'bad' WHERE trade_date = ?",
        "UPDATE intraday_plans SET official_pre_close = 'bad' WHERE trade_date = ?",
        "UPDATE intraday_plans SET vwap_above_confirm_seconds = 'bad' WHERE trade_date = ?",
        "UPDATE intraday_plans SET vwap_above_confirm_seconds = 1.5 WHERE trade_date = ?",
        "UPDATE intraday_plans SET vwap_above_confirm_seconds = NULL WHERE trade_date = ?",
    ],
)
def test_replay_disables_plan_when_loaded_numeric_field_is_malformed(
    tmp_path: Path,
    update_sql: str,
) -> None:
    db_path = tmp_path / "trading_x.db"
    input_path = tmp_path / "replay.csv"
    report_dir = tmp_path / "reports"
    init_db(db_path)
    insert_plan(db_path, PlanFixture(official_pre_close=10.0, volume_min_abs_amount=1000.0))
    with sqlite3.connect(db_path) as conn:
        conn.execute(update_sql, ("20260630",))
    write_replay_csv(input_path, "20260630,09:36:00,300001.SZ,12.00,10000,1000,12.00,11.80\n")

    try:
        run_replay(db_path, "20260630", input_path, report_dir)
    except ValueError as exc:
        pytest.fail(f"malformed numeric plan field escaped validation: {exc}")

    with sqlite3.connect(db_path) as conn:
        status = conn.execute(
            "SELECT plan_status FROM intraday_plans WHERE trade_date = ? AND ts_code = ?",
            ("20260630", "300001.SZ"),
        ).fetchone()[0]
    report = (report_dir / "20260630_replay_report.md").read_text(encoding="utf-8")
    assert status == "DISABLED"
    assert alert_rows(db_path) == []
    assert "PLAN_INVALID" in report
