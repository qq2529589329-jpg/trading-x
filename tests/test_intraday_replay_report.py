from hashlib import sha256
from pathlib import Path
import sqlite3

from intraday_replay_fixtures import PlanFixture, insert_plan, write_replay_csv
from trading_x.db import init_db
from trading_x.intraday import run_replay


def test_successful_replay_records_input_file_and_sha256(tmp_path: Path) -> None:
    db_path = tmp_path / "trading_x.db"
    input_path = tmp_path / "replay.csv"
    report_dir = tmp_path / "reports"
    init_db(db_path)
    write_replay_csv(input_path, "")

    result = run_replay(db_path, "20260630", input_path, report_dir)

    expected_hash = sha256(input_path.read_bytes()).hexdigest()
    with sqlite3.connect(db_path) as conn:
        row = conn.execute(
            "SELECT input_file, input_sha256, plan_count, alert_count, status, "
            "started_at, ended_at, error_message "
            "FROM intraday_replay_runs WHERE trade_date = ?",
            ("20260630",),
        ).fetchone()
    report = (report_dir / "20260630_replay_report.md").read_text(encoding="utf-8")
    assert result.input_sha256 == expected_hash
    assert row == (
        str(input_path),
        expected_hash,
        0,
        0,
        "SUCCESS",
        result.started_at,
        result.ended_at,
        None,
    )
    assert result.started_at <= result.ended_at
    assert f"- input_file: {input_path}" in report
    assert f"- input_sha256: {expected_hash}" in report


def test_replay_keeps_distinct_run_hashes_when_same_date_input_changes(tmp_path: Path) -> None:
    db_path = tmp_path / "trading_x.db"
    input_path = tmp_path / "replay.csv"
    report_dir = tmp_path / "reports"
    init_db(db_path)
    write_replay_csv(input_path, "")
    first_hash = sha256(input_path.read_bytes()).hexdigest()

    first = run_replay(db_path, "20260630", input_path, report_dir)
    write_replay_csv(input_path, "20260630,09:36:00,300001.SZ,12.00,1000,100,12.00,11.80\n")
    second_hash = sha256(input_path.read_bytes()).hexdigest()
    second = run_replay(db_path, "20260630", input_path, report_dir)

    with sqlite3.connect(db_path) as conn:
        rows = conn.execute(
            "SELECT input_sha256, status, alert_count FROM intraday_replay_runs "
            "WHERE trade_date = ? ORDER BY id",
            ("20260630",),
        ).fetchall()
    assert first_hash != second_hash
    assert first.input_sha256 == first_hash
    assert second.input_sha256 == second_hash
    assert rows == [(first_hash, "SUCCESS", 0), (second_hash, "SUCCESS", 0)]


def test_replay_report_lists_alert_reason_codes(tmp_path: Path) -> None:
    db_path = tmp_path / "trading_x.db"
    input_path = tmp_path / "replay.csv"
    report_dir = tmp_path / "reports"
    init_db(db_path)
    insert_plan(db_path, PlanFixture(official_pre_close=10.0, volume_min_abs_amount=1000.0))
    write_replay_csv(input_path, "20260630,09:36:00,300001.SZ,12.00,10000,1000,12.00,11.80\n")

    run_replay(db_path, "20260630", input_path, report_dir)

    report = (report_dir / "20260630_replay_report.md").read_text(encoding="utf-8")
    assert "- 09:36:00 300001.SZ BUY_TRIGGER B_BUY_TRIGGERED" in report


def test_replay_without_plans_skips_missing_input_file(tmp_path: Path) -> None:
    db_path = tmp_path / "trading_x.db"
    input_path = tmp_path / "missing.csv"
    report_dir = tmp_path / "reports"
    init_db(db_path)

    result = run_replay(db_path, "20260630", input_path, report_dir)

    with sqlite3.connect(db_path) as conn:
        row = conn.execute(
            "SELECT status, error_message FROM intraday_replay_runs WHERE trade_date = ?",
            ("20260630",),
        ).fetchone()
    report = (report_dir / "20260630_replay_report.md").read_text(encoding="utf-8")
    assert result.status == "SUCCESS"
    assert result.error_message is None
    assert row == ("SUCCESS", None)
    assert "今日无 intraday_plans，未执行回放" in report
