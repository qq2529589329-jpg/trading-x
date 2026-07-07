from pathlib import Path
import sqlite3
import sys

from intraday_replay_fixtures import (
    PlanFixture,
    alert_rows,
    insert_plan,
    seed_b_candidate,
    write_replay_csv,
    write_text,
)
from trading_x import cli
from trading_x.db import init_db
from trading_x.intraday import materialize_intraday_plans, run_replay
from trading_x.types import StrategyType


def test_materialize_intraday_plans_writes_b_class_plan(tmp_path: Path) -> None:
    db_path = tmp_path / "trading_x.db"
    init_db(db_path)
    seed_b_candidate(db_path, pre_close=10.0)

    count = materialize_intraday_plans(db_path, "20260630")

    with sqlite3.connect(db_path) as conn:
        row = conn.execute(
            "SELECT strategy_type, allow_trade, entry_low, entry_high, "
            "breakout_price, stop_price, official_pre_close "
            "FROM intraday_plans WHERE trade_date = ? AND ts_code = ?",
            ("20260630", "300001.SZ"),
        ).fetchone()

    assert count == 1
    assert row == (StrategyType.B_CAPACITY_LEADER, 1, 10.2, 11.34, 10.8, 9.8, 10.0)


def test_materialize_intraday_plans_prefers_limit_pre_close(tmp_path: Path) -> None:
    db_path = tmp_path / "trading_x.db"
    init_db(db_path)
    seed_b_candidate(db_path, pre_close=9.5, limit_pre_close=10.0)

    materialize_intraday_plans(db_path, "20260630")

    with sqlite3.connect(db_path) as conn:
        row = conn.execute(
            "SELECT official_pre_close, pre_close_source FROM intraday_plans "
            "WHERE trade_date = ? AND ts_code = ?",
            ("20260630", "300001.SZ"),
        ).fetchone()

    assert row == (10.0, "stk_limit_prices.pre_close")


def test_materialize_intraday_plans_uses_daily_pre_close_when_limit_missing(tmp_path: Path) -> None:
    db_path = tmp_path / "trading_x.db"
    init_db(db_path)
    seed_b_candidate(db_path, pre_close=9.5, limit_pre_close=0.0)

    materialize_intraday_plans(db_path, "20260630")

    with sqlite3.connect(db_path) as conn:
        row = conn.execute(
            "SELECT official_pre_close, pre_close_source FROM intraday_plans "
            "WHERE trade_date = ? AND ts_code = ?",
            ("20260630", "300001.SZ"),
        ).fetchone()

    assert row == (9.5, "daily_quotes.pre_close")


def test_replay_writes_watch_when_volume_gate_fails(tmp_path: Path) -> None:
    db_path = tmp_path / "trading_x.db"
    input_path = tmp_path / "replay.csv"
    init_db(db_path)
    insert_plan(db_path, PlanFixture(official_pre_close=10.0, volume_min_abs_amount=10_000_000.0))
    write_replay_csv(
        input_path,
        "20260630,09:36:00,300001.SZ,12.00,1000,90,12.00,11.80\n",
    )

    result = run_replay(db_path, "20260630", input_path, tmp_path / "reports")

    alert_types = alert_rows(db_path)
    assert result.status == "SUCCESS"
    assert alert_types == [("WATCH", "VOLUME_GATE_FAILED")]


def test_replay_allows_watch_but_blocks_buy_when_pre_close_missing(tmp_path: Path) -> None:
    db_path = tmp_path / "trading_x.db"
    input_path = tmp_path / "replay.csv"
    init_db(db_path)
    insert_plan(db_path, PlanFixture(official_pre_close=0.0, volume_min_abs_amount=1000.0))
    write_replay_csv(
        input_path,
        "20260630,09:36:00,300001.SZ,12.00,10000,1000,12.00,11.80\n",
    )

    run_replay(db_path, "20260630", input_path, tmp_path / "reports")

    assert alert_rows(db_path) == [("WATCH", "PRE_CLOSE_MISSING")]


def test_buy_trigger_lock_does_not_block_entry_cancelled(tmp_path: Path) -> None:
    db_path = tmp_path / "trading_x.db"
    input_path = tmp_path / "replay.csv"
    init_db(db_path)
    insert_plan(db_path, PlanFixture(official_pre_close=10.0, volume_min_abs_amount=1000.0))
    write_replay_csv(
        input_path,
        "20260630,09:36:00,300001.SZ,12.00,10000,1000,12.00,11.80\n"
        "20260630,09:37:00,300001.SZ,12.50,11000,1000,12.50,12.00\n"
        "20260630,09:40:00,300001.SZ,9.90,15000,1000,10.00,9.90\n",
    )

    run_replay(db_path, "20260630", input_path, tmp_path / "reports")

    assert alert_rows(db_path) == [
        ("BUY_TRIGGER", "B_BUY_TRIGGERED"),
        ("ENTRY_CANCELLED", "ENTRY_CANCELLED_VWAP_BREAK"),
    ]


def test_entry_cancelled_before_buy_when_price_breaks_stop(tmp_path: Path) -> None:
    db_path = tmp_path / "trading_x.db"
    input_path = tmp_path / "replay.csv"
    init_db(db_path)
    insert_plan(db_path, PlanFixture(official_pre_close=10.0, volume_min_abs_amount=1000.0))
    write_replay_csv(
        input_path,
        "20260630,09:36:00,300001.SZ,9.70,10000,1000,9.80,9.70\n",
    )

    run_replay(db_path, "20260630", input_path, tmp_path / "reports")

    assert alert_rows(db_path) == [("ENTRY_CANCELLED", "ENTRY_CANCELLED_PRICE_OUT_OF_RANGE")]


def test_volume_gate_disabled_allows_buy_trigger(tmp_path: Path) -> None:
    db_path = tmp_path / "trading_x.db"
    input_path = tmp_path / "replay.csv"
    init_db(db_path)
    insert_plan(
        db_path,
        PlanFixture(
            official_pre_close=10.0,
            volume_min_abs_amount=10_000_000.0,
            volume_gate_enabled=False,
        ),
    )
    write_replay_csv(
        input_path,
        "20260630,09:36:00,300001.SZ,12.00,1000,1000,12.00,11.80\n",
    )

    run_replay(db_path, "20260630", input_path, tmp_path / "reports")

    assert alert_rows(db_path) == [("BUY_TRIGGER", "B_BUY_TRIGGERED")]


def test_post_close_fixed_price_phase_blocks_buy_trigger(tmp_path: Path) -> None:
    db_path = tmp_path / "trading_x.db"
    input_path = tmp_path / "replay.csv"
    init_db(db_path)
    insert_plan(
        db_path,
        PlanFixture(
            trade_date="20260706",
            official_pre_close=10.0,
            volume_min_abs_amount=1000.0,
        ),
    )
    write_replay_csv(
        input_path,
        "20260706,15:10:00,300001.SZ,12.00,10000,1000,12.00,11.80\n",
    )

    run_replay(db_path, "20260706", input_path, tmp_path / "reports")

    assert alert_rows(db_path) == [("WATCH", "POST_CLOSE_FIXED_PRICE_OBSERVATION")]

def test_invalid_plan_is_disabled_during_replay(tmp_path: Path) -> None:
    db_path = tmp_path / "trading_x.db"
    input_path = tmp_path / "replay.csv"
    report_dir = tmp_path / "reports"
    init_db(db_path)
    insert_plan(db_path, PlanFixture(official_pre_close=10.0, volume_min_abs_amount=1000.0, stop_price=0.0))
    write_replay_csv(
        input_path,
        "20260630,09:36:00,300001.SZ,12.00,10000,1000,12.00,11.80\n",
    )

    run_replay(db_path, "20260630", input_path, report_dir)

    with sqlite3.connect(db_path) as conn:
        status = conn.execute(
            "SELECT plan_status FROM intraday_plans WHERE trade_date = ? AND ts_code = ?",
            ("20260630", "300001.SZ"),
        ).fetchone()[0]

    assert status == "DISABLED"
    assert "PLAN_INVALID" in (report_dir / "20260630_replay_report.md").read_text(encoding="utf-8")


def test_replay_without_plans_generates_report(tmp_path: Path) -> None:
    db_path = tmp_path / "trading_x.db"
    input_path = tmp_path / "replay.csv"
    report_dir = tmp_path / "reports"
    init_db(db_path)
    write_replay_csv(input_path, "20260630,09:36:00,300001.SZ,12.00,10000,1000,12.00,11.80\n")

    result = run_replay(db_path, "20260630", input_path, report_dir)

    report = (report_dir / "20260630_replay_report.md").read_text(encoding="utf-8")
    assert result.status == "SUCCESS"
    assert "今日无 intraday_plans，未执行回放" in report


def test_replay_rejects_malformed_command_date_even_without_plans(tmp_path: Path) -> None:
    db_path = tmp_path / "trading_x.db"
    input_path = tmp_path / "replay.csv"
    report_dir = tmp_path / "reports"
    init_db(db_path)
    write_text(input_path, "trade_date,quote_time,ts_code,price,amount_since_open,volume_since_open,bar_high,bar_low\n")

    result = run_replay(db_path, "2026-06-30", input_path, report_dir)

    assert result.status == "FAILED"
    assert result.error_message == "REPLAY_DATE_INVALID"


def test_cli_replay_uses_default_input_path(
    tmp_path: Path,
    monkeypatch,
    capsys,
) -> None:
    db_path = tmp_path / "trading_x.db"
    input_dir = tmp_path / "data" / "replay"
    report_dir = tmp_path / "reports"
    input_path = input_dir / "20260630.csv"
    init_db(db_path)
    input_dir.mkdir(parents=True)
    write_replay_csv(input_path, "20260630,09:36:00,300001.SZ,12.00,10000,1000,12.00,11.80\n")
    monkeypatch.chdir(tmp_path)
    monkeypatch.setattr(cli, "DEFAULT_REPORT_DIR", report_dir)
    monkeypatch.setattr(
        sys,
        "argv",
        ["trading_x", "--db", str(db_path), "replay", "--date", "20260630"],
    )

    assert cli.main() == 0

    output = capsys.readouterr().out
    assert "replay=SUCCESS 20260630 alerts=0" in output
    assert (report_dir / "20260630_replay_report.md").exists()


def test_cli_materializes_intraday_plans(tmp_path: Path, monkeypatch, capsys) -> None:
    db_path = tmp_path / "trading_x.db"
    init_db(db_path)
    seed_b_candidate(db_path, pre_close=10.0)
    monkeypatch.setattr(
        sys,
        "argv",
        ["trading_x", "--db", str(db_path), "plans", "materialize", "--date", "20260630"],
    )

    assert cli.main() == 0

    with sqlite3.connect(db_path) as conn:
        count = conn.execute("SELECT COUNT(*) FROM intraday_plans WHERE trade_date = ?", ("20260630",)).fetchone()[0]

    assert count == 1
    assert "intraday_plans=1 20260630" in capsys.readouterr().out
