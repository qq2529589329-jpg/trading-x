from pathlib import Path

import pytest

from intraday_replay_fixtures import PlanFixture, alert_rows, insert_plan, write_replay_csv, write_text
from trading_x.db import init_db
from trading_x.intraday import run_replay


@pytest.mark.parametrize("ts_code", ["", "   "])
def test_replay_rejects_blank_ts_code_at_csv_boundary(tmp_path: Path, ts_code: str) -> None:
    db_path = tmp_path / "trading_x.db"
    input_path = tmp_path / "replay.csv"
    report_dir = tmp_path / "reports"
    init_db(db_path)
    insert_plan(db_path, PlanFixture(official_pre_close=10.0, volume_min_abs_amount=1000.0))
    write_replay_csv(input_path, f"20260630,09:36:00,{ts_code},12.00,11000,1000,12.10,11.90\n")

    result = run_replay(db_path, "20260630", input_path, report_dir)

    report = (report_dir / "20260630_replay_report.md").read_text(encoding="utf-8")
    assert result.status == "FAILED"
    assert result.error_message == "REPLAY_CSV_INVALID_ROW"
    assert alert_rows(db_path) == []
    assert "REPLAY_CSV_INVALID_ROW" in report


def test_replay_rejects_short_row_missing_ts_code_cell(tmp_path: Path) -> None:
    db_path = tmp_path / "trading_x.db"
    input_path = tmp_path / "replay.csv"
    report_dir = tmp_path / "reports"
    init_db(db_path)
    insert_plan(db_path, PlanFixture(official_pre_close=10.0, volume_min_abs_amount=1000.0))
    write_replay_csv(input_path, "20260630,09:36:00\n")

    try:
        result = run_replay(db_path, "20260630", input_path, report_dir)
    except AttributeError as exc:
        pytest.fail(f"short replay row escaped CSV validation: {exc}")

    report = (report_dir / "20260630_replay_report.md").read_text(encoding="utf-8")
    assert result.status == "FAILED"
    assert result.error_message == "REPLAY_CSV_INVALID_ROW"
    assert alert_rows(db_path) == []
    assert "REPLAY_CSV_INVALID_ROW" in report


def test_replay_rejects_short_row_missing_quote_time_cell(tmp_path: Path) -> None:
    db_path = tmp_path / "trading_x.db"
    input_path = tmp_path / "replay.csv"
    report_dir = tmp_path / "reports"
    init_db(db_path)
    insert_plan(db_path, PlanFixture(official_pre_close=10.0, volume_min_abs_amount=1000.0))
    write_replay_csv(input_path, "20260630\n")

    try:
        result = run_replay(db_path, "20260630", input_path, report_dir)
    except AttributeError as exc:
        pytest.fail(f"short replay row escaped CSV validation: {exc}")

    report = (report_dir / "20260630_replay_report.md").read_text(encoding="utf-8")
    assert result.status == "FAILED"
    assert result.error_message == "REPLAY_CSV_INVALID_ROW"
    assert alert_rows(db_path) == []
    assert "REPLAY_CSV_INVALID_ROW" in report


def test_replay_rejects_long_row_with_unnamed_extra_cell(tmp_path: Path) -> None:
    db_path = tmp_path / "trading_x.db"
    input_path = tmp_path / "replay.csv"
    report_dir = tmp_path / "reports"
    init_db(db_path)
    insert_plan(db_path, PlanFixture(official_pre_close=10.0, volume_min_abs_amount=1000.0))
    write_replay_csv(input_path, "20260630,09:36:00,300001.SZ,12.00,11000,1000,12.10,11.90,extra\n")

    result = run_replay(db_path, "20260630", input_path, report_dir)

    report = (report_dir / "20260630_replay_report.md").read_text(encoding="utf-8")
    assert result.status == "FAILED"
    assert result.error_message == "REPLAY_CSV_INVALID_ROW"
    assert alert_rows(db_path) == []
    assert "REPLAY_CSV_INVALID_ROW" in report


def test_replay_accepts_named_extra_columns(tmp_path: Path) -> None:
    db_path = tmp_path / "trading_x.db"
    input_path = tmp_path / "replay.csv"
    report_dir = tmp_path / "reports"
    init_db(db_path)
    insert_plan(db_path, PlanFixture(official_pre_close=10.0, volume_min_abs_amount=1000.0))
    write_text(
        input_path,
        "trade_date,quote_time,ts_code,price,amount_since_open,volume_since_open,bar_high,bar_low,extra_note\n"
        "20260630,09:36:00,300001.SZ,12.00,11000,1000,12.10,11.90,ignored\n",
    )

    result = run_replay(db_path, "20260630", input_path, report_dir)

    assert result.status == "SUCCESS"
    assert result.error_message is None
    assert alert_rows(db_path) == [("BUY_TRIGGER", "B_BUY_TRIGGERED")]
