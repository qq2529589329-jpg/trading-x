from pathlib import Path
import sqlite3

from intraday_replay_fixtures import PlanFixture, alert_rows, insert_plan, write_replay_csv
from trading_x.db import init_db
from trading_x.intraday import run_replay


def test_replay_disables_plan_when_allow_trade_is_text_false(tmp_path: Path) -> None:
    db_path = tmp_path / "trading_x.db"
    input_path = tmp_path / "replay.csv"
    report_dir = tmp_path / "reports"
    init_db(db_path)
    insert_plan(db_path, PlanFixture(official_pre_close=10.0, volume_min_abs_amount=1000.0))
    with sqlite3.connect(db_path) as conn:
        conn.execute("UPDATE intraday_plans SET allow_trade = 'false' WHERE trade_date = ?", ("20260630",))
    write_replay_csv(input_path, "20260630,09:36:00,300001.SZ,12.00,1000,1000,12.00,11.80\n")

    run_replay(db_path, "20260630", input_path, report_dir)

    with sqlite3.connect(db_path) as conn:
        status = conn.execute(
            "SELECT plan_status FROM intraday_plans WHERE trade_date = ? AND ts_code = ?",
            ("20260630", "300001.SZ"),
        ).fetchone()[0]
    report = (report_dir / "20260630_replay_report.md").read_text(encoding="utf-8")
    assert status == "DISABLED"
    assert alert_rows(db_path) == []
    assert "PLAN_INVALID" in report


def test_replay_treats_text_false_volume_gate_as_disabled(tmp_path: Path) -> None:
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
    with sqlite3.connect(db_path) as conn:
        conn.execute(
            "UPDATE intraday_plans SET volume_gate_enabled = 'false' WHERE trade_date = ?",
            ("20260630",),
        )
    write_replay_csv(input_path, "20260630,09:36:00,300001.SZ,12.00,1000,1000,12.00,11.80\n")

    run_replay(db_path, "20260630", input_path, tmp_path / "reports")

    assert alert_rows(db_path) == [("BUY_TRIGGER", "B_BUY_TRIGGERED")]
