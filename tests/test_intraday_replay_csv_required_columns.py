from hashlib import sha256
from pathlib import Path
import sqlite3

from intraday_replay_fixtures import PlanFixture, insert_plan, write_text
from trading_x.db import init_db
from trading_x.intraday import run_replay


def test_replay_fails_when_planned_csv_lacks_volume_since_open(tmp_path: Path) -> None:
    db_path = tmp_path / "trading_x.db"
    input_path = tmp_path / "bad.csv"
    report_dir = tmp_path / "reports"
    init_db(db_path)
    insert_plan(db_path, PlanFixture(official_pre_close=10.0, volume_min_abs_amount=1000.0))
    write_text(
        input_path,
        "trade_date,quote_time,ts_code,price,amount_since_open,bar_high,bar_low\n"
        "20260630,09:36:00,300001.SZ,12.00,10000000,12.00,11.80\n",
    )

    result = run_replay(db_path, "20260630", input_path, report_dir)

    with sqlite3.connect(db_path) as conn:
        row = conn.execute(
            "SELECT input_file, input_sha256, status, started_at, ended_at, error_message "
            "FROM intraday_replay_runs WHERE trade_date = ?",
            ("20260630",),
        ).fetchone()
    report = (report_dir / "20260630_replay_report.md").read_text(encoding="utf-8")
    expected_hash = sha256(input_path.read_bytes()).hexdigest()
    assert result.status == "FAILED"
    assert result.error_message == "REPLAY_CSV_MISSING_REQUIRED_COLUMNS: volume_since_open"
    assert result.input_sha256 == expected_hash
    assert row == (
        str(input_path),
        expected_hash,
        "FAILED",
        result.started_at,
        result.ended_at,
        "REPLAY_CSV_MISSING_REQUIRED_COLUMNS: volume_since_open",
    )
    assert result.started_at <= result.ended_at
    assert f"- input_file: {input_path}" in report
    assert f"- input_sha256: {expected_hash}" in report
    assert "REPLAY_CSV_MISSING_REQUIRED_COLUMNS: volume_since_open" in report
