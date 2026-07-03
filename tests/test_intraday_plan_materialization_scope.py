from pathlib import Path
import sqlite3

from trading_x.db import init_db
from trading_x.intraday import materialize_intraday_plans
from trading_x.types import StrategyType


def test_materialize_intraday_plans_preserves_non_b_intraday_plans(tmp_path: Path) -> None:
    db_path = tmp_path / "trading_x.db"
    init_db(db_path)
    with sqlite3.connect(db_path) as conn:
        conn.execute(
            "INSERT INTO daily_quotes ("
            "trade_date, ts_code, open, high, low, close, pre_close, pct_chg, vol, amount"
            ") VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            ("20260701", "300001.SZ", 10.0, 10.8, 9.8, 10.2, 9.9, 2.0, 1000.0, 100000.0),
        )
        conn.execute(
            "INSERT INTO stk_limit_prices (trade_date, ts_code, pre_close, up_limit, down_limit) "
            "VALUES (?, ?, ?, ?, ?)",
            ("20260701", "300001.SZ", 10.0, 11.0, 9.0),
        )
        conn.execute(
            "INSERT INTO candidate_runs ("
            "run_id, trade_date, system_version, strategy_version, threshold_version, config_hash, "
            "data_capability, p0_complete, theme_coverage_ratio, generated_at, report_json_path, "
            "report_md_path, notes"
            ") VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (
                "run-b",
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
                "reports/20260701_report.md",
                None,
            ),
        )
        conn.execute(
            "INSERT INTO candidate_snapshots ("
            "run_id, trade_date, rank, ts_code, name, strategy_type, theme_name, "
            "theme_confidence, theme_strength_score, entry_low, entry_high, stop_price, "
            "breakout_price, max_position_cash, max_loss, plan_json, created_at"
            ") VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (
                "run-b",
                "20260701",
                1,
                "300001.SZ",
                "capacity leader",
                StrategyType.B_CAPACITY_LEADER,
                "robotics",
                "MEDIUM",
                88.0,
                20.1,
                21.2,
                19.5,
                21.0,
                12000.0,
                600.0,
                "{}",
                "2026-07-01T16:00:00+00:00",
            ),
        )
        conn.execute(
            "INSERT INTO intraday_plans ("
            "trade_date, ts_code, name, strategy_type, allow_trade, plan_status, "
            "entry_low, entry_high, breakout_price, stop_price, max_stop_distance, "
            "max_position_cash, max_loss, official_pre_close, pre_close_source, "
            "vwap_active_after, vwap_above_confirm_seconds, volume_gate_enabled, "
            "volume_min_abs_amount, volume_same_window_multiplier, volume_ratio_0935, "
            "volume_ratio_0945, volume_ratio_1000, source_candidate_id, source_report_date, "
            "plan_json, system_version, created_at"
            ") VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (
                "20260701",
                "600001.SH",
                "non-b plan",
                StrategyType.A_SPACE_LEADER,
                1,
                "ACTIVE",
                10.0,
                11.0,
                10.8,
                9.5,
                0.07,
                10000.0,
                500.0,
                9.8,
                "daily_quotes.pre_close",
                "09:35:00",
                120,
                1,
                10000000.0,
                1.3,
                0.03,
                0.05,
                0.08,
                "manual-a",
                "20260701",
                "{}",
                "test",
                "2026-07-01T16:00:00+00:00",
            ),
        )

    materialize_intraday_plans(db_path, "20260701")

    with sqlite3.connect(db_path) as conn:
        strategies = conn.execute(
            "SELECT strategy_type FROM intraday_plans WHERE trade_date = ? ORDER BY strategy_type",
            ("20260701",),
        ).fetchall()

    assert strategies == [("A_SPACE_LEADER",), ("B_CAPACITY_LEADER",)]
