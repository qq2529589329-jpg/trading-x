from pathlib import Path
import sqlite3

import pytest

from intraday_replay_fixtures import PlanFixture, alert_rows, insert_plan, write_replay_csv, write_text
from trading_x.db import init_db
from trading_x.intraday import run_replay


@pytest.mark.parametrize("quote_time", ["bad", "9:36:00"])
def test_replay_rejects_invalid_quote_time_at_csv_boundary(tmp_path: Path, quote_time: str) -> None:
    db_path = tmp_path / "trading_x.db"
    input_path = tmp_path / "replay.csv"
    report_dir = tmp_path / "reports"
    init_db(db_path)
    insert_plan(db_path, PlanFixture(official_pre_close=10.0, volume_min_abs_amount=1000.0))
    write_replay_csv(input_path, f"20260630,{quote_time},300001.SZ,12.00,11000,1000,12.10,11.90\n")

    try:
        result = run_replay(db_path, "20260630", input_path, report_dir)
    except ValueError as exc:
        pytest.fail(f"quote_time escaped CSV validation: {exc}")

    with sqlite3.connect(db_path) as conn:
        row = conn.execute(
            "SELECT status, error_message FROM intraday_replay_runs WHERE trade_date = ?",
            ("20260630",),
        ).fetchone()
    report = (report_dir / "20260630_replay_report.md").read_text(encoding="utf-8")
    assert result.status == "FAILED"
    assert result.error_message == "REPLAY_CSV_INVALID_ROW"
    assert row == ("FAILED", "REPLAY_CSV_INVALID_ROW")
    assert alert_rows(db_path) == []
    assert "REPLAY_CSV_INVALID_ROW" in report


def test_replay_rejects_malformed_trade_date_at_csv_boundary(tmp_path: Path) -> None:
    db_path = tmp_path / "trading_x.db"
    input_path = tmp_path / "replay.csv"
    report_dir = tmp_path / "reports"
    init_db(db_path)
    write_replay_csv(input_path, "2026-06-30,09:36:00,300001.SZ,12.00,11000,1000,12.10,11.90\n")

    result = run_replay(db_path, "2026-06-30", input_path, report_dir)

    report = (report_dir / "2026-06-30_replay_report.md").read_text(encoding="utf-8")
    assert result.status == "FAILED"
    assert result.error_message == "REPLAY_CSV_INVALID_ROW"
    assert "REPLAY_CSV_INVALID_ROW" in report


@pytest.mark.parametrize(
    "row",
    [
        "20260630,09:36:00,300001.SZ,12.00,-1,1000,12.00,11.80\n",
        "20260630,09:36:00,300001.SZ,12.00,10000,-1,12.00,11.80\n",
    ],
)
def test_replay_rejects_negative_cumulative_amount_or_volume(tmp_path: Path, row: str) -> None:
    db_path = tmp_path / "trading_x.db"
    input_path = tmp_path / "replay.csv"
    report_dir = tmp_path / "reports"
    init_db(db_path)
    insert_plan(db_path, PlanFixture(official_pre_close=10.0, volume_min_abs_amount=1000.0))
    write_replay_csv(input_path, row)

    result = run_replay(db_path, "20260630", input_path, report_dir)

    report = (report_dir / "20260630_replay_report.md").read_text(encoding="utf-8")
    assert result.status == "FAILED"
    assert result.error_message == "REPLAY_CSV_INVALID_ROW"
    assert alert_rows(db_path) == []
    assert "REPLAY_CSV_INVALID_ROW" in report


@pytest.mark.parametrize(
    "row",
    [
        "20260630,09:36:00,300001.SZ,nan,10000,1000,12.00,11.80\n",
        "20260630,09:36:00,300001.SZ,12.00,inf,1000,12.00,11.80\n",
    ],
)
def test_replay_rejects_non_finite_numeric_values(tmp_path: Path, row: str) -> None:
    db_path = tmp_path / "trading_x.db"
    input_path = tmp_path / "replay.csv"
    report_dir = tmp_path / "reports"
    init_db(db_path)
    insert_plan(db_path, PlanFixture(official_pre_close=10.0, volume_min_abs_amount=1000.0))
    write_replay_csv(input_path, row)

    result = run_replay(db_path, "20260630", input_path, report_dir)

    report = (report_dir / "20260630_replay_report.md").read_text(encoding="utf-8")
    assert result.status == "FAILED"
    assert result.error_message == "REPLAY_CSV_INVALID_ROW"
    assert alert_rows(db_path) == []
    assert "REPLAY_CSV_INVALID_ROW" in report


@pytest.mark.parametrize(
    "rows",
    [
        "20260630,09:36:00,300001.SZ,12.00,10000,1000,12.00,11.80\n"
        "20260630,09:37:00,300001.SZ,12.10,9000,1100,12.10,12.00\n",
        "20260630,09:36:00,300001.SZ,12.00,10000,1000,12.00,11.80\n"
        "20260630,09:37:00,300001.SZ,12.10,11000,900,12.10,12.00\n",
    ],
)
def test_replay_rejects_decreasing_cumulative_amount_or_volume(tmp_path: Path, rows: str) -> None:
    db_path = tmp_path / "trading_x.db"
    input_path = tmp_path / "replay.csv"
    report_dir = tmp_path / "reports"
    init_db(db_path)
    insert_plan(db_path, PlanFixture(official_pre_close=10.0, volume_min_abs_amount=1000.0))
    write_replay_csv(input_path, rows)

    result = run_replay(db_path, "20260630", input_path, report_dir)

    report = (report_dir / "20260630_replay_report.md").read_text(encoding="utf-8")
    assert result.status == "FAILED"
    assert result.error_message == "REPLAY_CSV_INVALID_ROW"
    assert alert_rows(db_path) == []
    assert "REPLAY_CSV_INVALID_ROW" in report


def test_replay_rejects_duplicate_symbol_quote_time(tmp_path: Path) -> None:
    db_path = tmp_path / "trading_x.db"
    input_path = tmp_path / "replay.csv"
    report_dir = tmp_path / "reports"
    init_db(db_path)
    insert_plan(db_path, PlanFixture(official_pre_close=10.0, volume_min_abs_amount=1000.0))
    write_replay_csv(
        input_path,
        "20260630,09:36:00,300001.SZ,12.00,10000,1000,12.00,11.80\n"
        "20260630,09:36:00,300001.SZ,12.10,11000,1100,12.10,12.00\n",
    )

    result = run_replay(db_path, "20260630", input_path, report_dir)

    report = (report_dir / "20260630_replay_report.md").read_text(encoding="utf-8")
    assert result.status == "FAILED"
    assert result.error_message == "REPLAY_CSV_INVALID_ROW"
    assert alert_rows(db_path) == []
    assert "REPLAY_CSV_INVALID_ROW" in report


@pytest.mark.parametrize(
    "row",
    [
        "20260630,09:36:00,300001.SZ,0,10000,1000,12.00,11.80\n",
        "20260630,09:36:00,300001.SZ,12.00,10000,1000,11.70,11.80\n",
        "20260630,09:36:00,300001.SZ,12.20,10000,1000,12.00,11.80\n",
        "20260630,09:36:00,300001.SZ,11.70,10000,1000,12.00,11.80\n",
    ],
)
def test_replay_rejects_invalid_price_or_bar_range(tmp_path: Path, row: str) -> None:
    db_path = tmp_path / "trading_x.db"
    input_path = tmp_path / "replay.csv"
    report_dir = tmp_path / "reports"
    init_db(db_path)
    insert_plan(db_path, PlanFixture(official_pre_close=10.0, volume_min_abs_amount=1000.0))
    write_replay_csv(input_path, row)

    result = run_replay(db_path, "20260630", input_path, report_dir)

    report = (report_dir / "20260630_replay_report.md").read_text(encoding="utf-8")
    assert result.status == "FAILED"
    assert result.error_message == "REPLAY_CSV_INVALID_ROW"
    assert alert_rows(db_path) == []
    assert "REPLAY_CSV_INVALID_ROW" in report


def test_replay_accepts_utf8_bom_header(tmp_path: Path) -> None:
    db_path = tmp_path / "trading_x.db"
    input_path = tmp_path / "replay.csv"
    report_dir = tmp_path / "reports"
    init_db(db_path)
    insert_plan(db_path, PlanFixture(official_pre_close=10.0, volume_min_abs_amount=1000.0))
    write_text(
        input_path,
        "\ufefftrade_date,quote_time,ts_code,price,amount_since_open,volume_since_open,bar_high,bar_low\n"
        "20260630,09:36:00,300001.SZ,12.00,11000,1000,12.00,11.80\n",
    )

    result = run_replay(db_path, "20260630", input_path, report_dir)

    assert result.status == "SUCCESS"
    assert alert_rows(db_path) == [("BUY_TRIGGER", "B_BUY_TRIGGERED")]


def test_replay_rejects_duplicate_csv_header_names(tmp_path: Path) -> None:
    db_path = tmp_path / "trading_x.db"
    input_path = tmp_path / "replay.csv"
    report_dir = tmp_path / "reports"
    init_db(db_path)
    insert_plan(db_path, PlanFixture(official_pre_close=10.0, volume_min_abs_amount=1000.0))
    write_text(
        input_path,
        "trade_date,quote_time,ts_code,price,amount_since_open,volume_since_open,bar_high,bar_low,price\n"
        "20260630,09:36:00,300001.SZ,bad,11000,1000,12.00,11.80,12.00\n",
    )

    result = run_replay(db_path, "20260630", input_path, report_dir)

    report = (report_dir / "20260630_replay_report.md").read_text(encoding="utf-8")
    assert result.status == "FAILED"
    assert result.error_message == "REPLAY_CSV_INVALID_HEADER"
    assert "REPLAY_CSV_INVALID_HEADER" in report


def test_failed_replay_clears_stale_alerts_for_same_trade_date(tmp_path: Path) -> None:
    db_path = tmp_path / "trading_x.db"
    input_path = tmp_path / "replay.csv"
    report_dir = tmp_path / "reports"
    init_db(db_path)
    insert_plan(db_path, PlanFixture(official_pre_close=10.0, volume_min_abs_amount=1000.0))
    write_replay_csv(input_path, "20260630,09:36:00,300001.SZ,12.00,10000,1000,12.00,11.80\n")
    run_replay(db_path, "20260630", input_path, report_dir)
    assert alert_rows(db_path) == [("BUY_TRIGGER", "B_BUY_TRIGGERED")]
    write_text(
        input_path,
        "trade_date,quote_time,ts_code,price,amount_since_open,bar_high,bar_low\n"
        "20260630,09:37:00,300001.SZ,12.00,10000,12.00,11.80\n",
    )

    result = run_replay(db_path, "20260630", input_path, report_dir)

    assert result.status == "FAILED"
    assert alert_rows(db_path) == []


def test_failed_replay_records_b_class_plan_count(tmp_path: Path) -> None:
    db_path = tmp_path / "trading_x.db"
    input_path = tmp_path / "replay.csv"
    report_dir = tmp_path / "reports"
    init_db(db_path)
    insert_plan(db_path, PlanFixture(official_pre_close=10.0, volume_min_abs_amount=1000.0))
    write_text(
        input_path,
        "trade_date,quote_time,ts_code,price,amount_since_open,bar_high,bar_low\n"
        "20260630,09:36:00,300001.SZ,12.00,10000,12.00,11.80\n",
    )

    result = run_replay(db_path, "20260630", input_path, report_dir)

    with sqlite3.connect(db_path) as conn:
        row = conn.execute(
            "SELECT plan_count, alert_count, status FROM intraday_replay_runs WHERE trade_date = ?",
            ("20260630",),
        ).fetchone()
    report = (report_dir / "20260630_replay_report.md").read_text(encoding="utf-8")
    assert result.plan_count == 1
    assert row == (1, 0, "FAILED")
    assert "- plan_count: 1" in report
