from pathlib import Path
import sqlite3
import sys

import pytest

from intraday_replay_fixtures import PlanFixture, insert_plan, seed_b_candidate, write_replay_csv, write_text
from trading_x import cli
from trading_x.db import init_db


def test_cli_replay_returns_failure_and_prints_csv_error(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
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
    monkeypatch.setattr(cli, "DEFAULT_REPORT_DIR", report_dir)
    monkeypatch.setattr(
        sys,
        "argv",
        ["trading_x", "--db", str(db_path), "replay", "--date", "20260630", "--input", str(input_path)],
    )

    exit_code = cli.main()

    with sqlite3.connect(db_path) as conn:
        row = conn.execute(
            "SELECT status, error_message FROM intraday_replay_runs WHERE trade_date = ?",
            ("20260630",),
        ).fetchone()
    output = capsys.readouterr().out
    assert exit_code == 1
    assert "replay=FAILED 20260630 alerts=0" in output
    assert "REPLAY_CSV_MISSING_REQUIRED_COLUMNS: volume_since_open" in output
    assert row == ("FAILED", "REPLAY_CSV_MISSING_REQUIRED_COLUMNS: volume_since_open")


def test_cli_replay_defaults_input_to_date_csv(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    db_path = tmp_path / "trading_x.db"
    input_path = tmp_path / "data" / "replay" / "20260630.csv"
    report_dir = tmp_path / "reports"
    init_db(db_path)
    insert_plan(db_path, PlanFixture(official_pre_close=10.0, volume_min_abs_amount=1000.0))
    write_replay_csv(
        input_path,
        "20260630,09:36:00,300001.SZ,12.00,10000,1000,12.00,11.80\n",
    )
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(cli, "DEFAULT_REPORT_DIR", report_dir)
    monkeypatch.setattr(sys, "argv", ["trading_x", "--db", str(db_path), "replay", "--date", "20260630"])

    exit_code = cli.main()

    with sqlite3.connect(db_path) as conn:
        row = conn.execute(
            "SELECT input_file, status, alert_count FROM intraday_replay_runs WHERE trade_date = ?",
            ("20260630",),
        ).fetchone()
    output = capsys.readouterr().out
    assert exit_code == 0
    assert "replay=SUCCESS 20260630 alerts=1" in output
    assert Path(row[0]) == Path("data") / "replay" / "20260630.csv"
    assert row[1:] == ("SUCCESS", 1)


def test_cli_plans_materialize_writes_intraday_plans(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    db_path = tmp_path / "trading_x.db"
    init_db(db_path)
    seed_b_candidate(db_path, pre_close=10.0)
    monkeypatch.setattr(sys, "argv", ["trading_x", "--db", str(db_path), "plans", "materialize", "--date", "20260630"])

    exit_code = cli.main()

    with sqlite3.connect(db_path) as conn:
        plan_count = conn.execute("SELECT COUNT(*) FROM intraday_plans WHERE trade_date = ?", ("20260630",)).fetchone()[0]
    output = capsys.readouterr().out
    assert exit_code == 0
    assert "intraday_plans=1 20260630" in output
    assert plan_count == 1
