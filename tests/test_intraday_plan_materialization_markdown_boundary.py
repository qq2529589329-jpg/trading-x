from pathlib import Path
import json
import sqlite3

from trading_x.db import init_db
from trading_x.intraday import materialize_intraday_plans
from trading_x.types import StrategyType


def test_materialize_intraday_plans_ignores_report_markdown_prices(tmp_path: Path) -> None:
    db_path = tmp_path / "trading_x.db"
    report_md_path = tmp_path / "reports" / "20260701_report.md"
    report_md_path.parent.mkdir(parents=True)
    report_md_path.write_text(
        "Markdown says buy at 99.99, breakout at 88.88, stop at 1.11.",
        encoding="utf-8",
    )
    init_db(db_path)
    with sqlite3.connect(db_path) as conn:
        conn.execute(
            "INSERT INTO candidate_runs ("
            "run_id, trade_date, system_version, strategy_version, threshold_version, "
            "config_hash, data_capability, p0_complete, theme_coverage_ratio, generated_at, "
            "report_json_path, report_md_path, notes"
            ") VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (
                "run-md-conflict",
                "20260701",
                "v1.0",
                "rules-v1",
                "threshold-v1",
                "config-hash",
                "BASIC",
                1,
                1.0,
                "2026-07-01T16:00:00+00:00",
                "reports/20260701_report.json",
                str(report_md_path),
                None,
            ),
        )
        conn.execute(
            "INSERT INTO candidate_snapshots ("
            "run_id, trade_date, rank, ts_code, name, strategy_type, leader_status, "
            "theme_name, theme_confidence, theme_strength_score, data_capability, "
            "entry_low, entry_high, stop_price, breakout_price, max_position_cash, max_loss, "
            "include_reasons_json, reject_reasons_json, plan_json, created_at"
            ") VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (
                "run-md-conflict",
                "20260701",
                1,
                "300001.SZ",
                "Capacity Leader",
                StrategyType.B_CAPACITY_LEADER,
                "leader",
                "robotics",
                "MEDIUM",
                88.0,
                "BASIC",
                20.1,
                21.2,
                19.5,
                21.0,
                12000.0,
                600.0,
                "[]",
                "[]",
                json.dumps({"source": "structured-snapshot"}, sort_keys=True),
                "2026-07-01T16:00:00+00:00",
            ),
        )

    count = materialize_intraday_plans(db_path, "20260701")

    with sqlite3.connect(db_path) as conn:
        row = conn.execute(
            "SELECT entry_low, entry_high, breakout_price, stop_price "
            "FROM intraday_plans WHERE trade_date = ? AND ts_code = ?",
            ("20260701", "300001.SZ"),
        ).fetchone()

    assert count == 1
    assert row == (20.1, 21.2, 21.0, 19.5)
