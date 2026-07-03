from pathlib import Path
import sqlite3

from intraday_replay_fixtures import PlanFixture, alert_rows, insert_plan, write_replay_csv
from trading_x.db import init_db
from trading_x.intraday import run_replay


def test_negative_pre_close_disables_plan_before_missing_pre_close_watch(tmp_path: Path) -> None:
    db_path = tmp_path / "trading_x.db"
    input_path = tmp_path / "replay.csv"
    report_dir = tmp_path / "reports"
    init_db(db_path)
    insert_plan(db_path, PlanFixture(official_pre_close=-1.0, volume_min_abs_amount=1000.0))
    write_replay_csv(
        input_path,
        "20260630,09:36:00,300001.SZ,12.00,10000,1000,12.00,11.80\n",
    )

    result = run_replay(db_path, "20260630", input_path, report_dir)

    with sqlite3.connect(db_path) as conn:
        plan_status = conn.execute("SELECT plan_status FROM intraday_plans").fetchone()[0]
    report = (report_dir / "20260630_replay_report.md").read_text(encoding="utf-8")
    assert result.alert_count == 0
    assert plan_status == "DISABLED"
    assert alert_rows(db_path) == []
    assert "300001.SZ:B_CAPACITY_LEADER:PLAN_INVALID" in report
