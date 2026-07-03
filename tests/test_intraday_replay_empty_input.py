from pathlib import Path
import sqlite3

from intraday_replay_fixtures import PlanFixture, alert_rows, insert_plan, write_replay_csv
from trading_x.db import init_db
from trading_x.intraday import run_replay


def test_replay_fails_when_plans_exist_but_csv_has_no_rows(tmp_path: Path) -> None:
    db_path = tmp_path / "trading_x.db"
    input_path = tmp_path / "replay.csv"
    report_dir = tmp_path / "reports"
    init_db(db_path)
    insert_plan(db_path, PlanFixture(official_pre_close=10.0, volume_min_abs_amount=1000.0))
    write_replay_csv(input_path, "")

    result = run_replay(db_path, "20260630", input_path, report_dir)

    with sqlite3.connect(db_path) as conn:
        row = conn.execute(
            "SELECT plan_count, alert_count, status, error_message "
            "FROM intraday_replay_runs WHERE trade_date = ?",
            ("20260630",),
        ).fetchone()
    report = (report_dir / "20260630_replay_report.md").read_text(encoding="utf-8")
    assert result.status == "FAILED"
    assert result.error_message == "REPLAY_CSV_NO_ROWS"
    assert row == (1, 0, "FAILED", "REPLAY_CSV_NO_ROWS")
    assert alert_rows(db_path) == []
    assert "REPLAY_CSV_NO_ROWS" in report


def test_replay_disables_invalid_plan_even_when_csv_has_no_rows(tmp_path: Path) -> None:
    db_path = tmp_path / "trading_x.db"
    input_path = tmp_path / "replay.csv"
    report_dir = tmp_path / "reports"
    init_db(db_path)
    insert_plan(db_path, PlanFixture(official_pre_close=10.0, volume_min_abs_amount=1000.0, stop_price=0.0))
    write_replay_csv(input_path, "")

    result = run_replay(db_path, "20260630", input_path, report_dir)

    with sqlite3.connect(db_path) as conn:
        status = conn.execute(
            "SELECT plan_status FROM intraday_plans WHERE trade_date = ? AND ts_code = ?",
            ("20260630", "300001.SZ"),
        ).fetchone()[0]
    report = (report_dir / "20260630_replay_report.md").read_text(encoding="utf-8")
    assert result.status == "FAILED"
    assert result.error_message == "REPLAY_CSV_NO_ROWS"
    assert status == "DISABLED"
    assert "PLAN_INVALID" in report


def test_replay_allows_empty_csv_when_no_intraday_plans(tmp_path: Path) -> None:
    db_path = tmp_path / "trading_x.db"
    input_path = tmp_path / "replay.csv"
    report_dir = tmp_path / "reports"
    init_db(db_path)
    write_replay_csv(input_path, "")

    result = run_replay(db_path, "20260630", input_path, report_dir)

    with sqlite3.connect(db_path) as conn:
        row = conn.execute(
            "SELECT plan_count, alert_count, status, error_message "
            "FROM intraday_replay_runs WHERE trade_date = ?",
            ("20260630",),
        ).fetchone()
    report = (report_dir / "20260630_replay_report.md").read_text(encoding="utf-8")
    assert result.status == "SUCCESS"
    assert result.plan_count == 0
    assert result.alert_count == 0
    assert result.error_message is None
    assert row == (0, 0, "SUCCESS", None)
    assert "今日无 intraday_plans，未执行回放" in report
