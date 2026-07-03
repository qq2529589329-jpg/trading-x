from pathlib import Path
import sqlite3

from intraday_replay_fixtures import alert_rows, seed_b_candidate, write_replay_csv
from trading_x.db import init_db
from trading_x.intraday import materialize_intraday_plans, run_replay


def test_materialize_intraday_plans_marks_pre_close_missing_when_sources_missing(tmp_path: Path) -> None:
    db_path = tmp_path / "trading_x.db"
    init_db(db_path)
    seed_b_candidate(db_path, pre_close=0.0, limit_pre_close=0.0)

    count = materialize_intraday_plans(db_path, "20260630")

    with sqlite3.connect(db_path) as conn:
        row = conn.execute(
            "SELECT official_pre_close, pre_close_source FROM intraday_plans "
            "WHERE trade_date = ? AND ts_code = ?",
            ("20260630", "300001.SZ"),
        ).fetchone()

    assert count == 1
    assert row == (0.0, "missing")


def test_materialized_malformed_pre_close_source_disables_plan(tmp_path: Path) -> None:
    db_path = tmp_path / "trading_x.db"
    input_path = tmp_path / "replay.csv"
    report_dir = tmp_path / "reports"
    init_db(db_path)
    seed_b_candidate(db_path, pre_close=0.0, limit_pre_close=0.0)
    with sqlite3.connect(db_path) as conn:
        conn.execute("UPDATE stk_limit_prices SET pre_close = 'bad' WHERE trade_date = ?", ("20260630",))
    materialize_intraday_plans(db_path, "20260630")
    write_replay_csv(input_path, "20260630,09:36:00,300001.SZ,12.00,10000,1000,12.00,11.80\n")

    run_replay(db_path, "20260630", input_path, report_dir)

    with sqlite3.connect(db_path) as conn:
        status = conn.execute("SELECT plan_status FROM intraday_plans WHERE trade_date = ?", ("20260630",)).fetchone()[0]
    report = (report_dir / "20260630_replay_report.md").read_text(encoding="utf-8")
    assert status == "DISABLED"
    assert alert_rows(db_path) == []
    assert "PLAN_INVALID" in report
