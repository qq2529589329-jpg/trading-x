from pathlib import Path
import sqlite3

from trading_x.db import init_db
from trading_x.intraday import run_replay


def test_replay_rejects_malformed_command_date_when_input_file_is_missing(tmp_path: Path) -> None:
    db_path = tmp_path / "trading_x.db"
    input_path = tmp_path / "missing.csv"
    report_dir = tmp_path / "reports"
    init_db(db_path)

    result = run_replay(db_path, "2026-06-30", input_path, report_dir)

    with sqlite3.connect(db_path) as conn:
        row = conn.execute(
            "SELECT status, error_message FROM intraday_replay_runs WHERE trade_date = ?",
            ("2026-06-30",),
        ).fetchone()
    report = (report_dir / "2026-06-30_replay_report.md").read_text(encoding="utf-8")
    assert result.status == "FAILED"
    assert result.error_message == "REPLAY_DATE_INVALID"
    assert row == ("FAILED", "REPLAY_DATE_INVALID")
    assert "REPLAY_DATE_INVALID" in report


def test_replay_records_failed_run_when_input_path_is_directory(tmp_path: Path) -> None:
    db_path = tmp_path / "trading_x.db"
    input_path = tmp_path / "replay_dir"
    report_dir = tmp_path / "reports"
    input_path.mkdir()
    init_db(db_path)

    result = run_replay(db_path, "20260630", input_path, report_dir)

    with sqlite3.connect(db_path) as conn:
        row = conn.execute(
            "SELECT status, error_message, input_file, input_sha256 "
            "FROM intraday_replay_runs WHERE trade_date = ?",
            ("20260630",),
        ).fetchone()
    report = (report_dir / "20260630_replay_report.md").read_text(encoding="utf-8")
    assert result.status == "FAILED"
    assert result.error_message == "REPLAY_CSV_UNREADABLE"
    assert row == ("FAILED", "REPLAY_CSV_UNREADABLE", str(input_path), "")
    assert f"- input_file: {input_path}" in report
    assert "- input_sha256: " in report
    assert "REPLAY_CSV_UNREADABLE" in report
