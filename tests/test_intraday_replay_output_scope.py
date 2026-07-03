from pathlib import Path
import sqlite3

from trading_x.db import init_db
from trading_x.intraday import run_replay
from trading_x.types import StrategyType


def test_replay_clears_only_b_class_alert_outputs(tmp_path: Path) -> None:
    db_path = tmp_path / "trading_x.db"
    init_db(db_path)
    with sqlite3.connect(db_path) as conn:
        conn.execute(
            "INSERT INTO intraday_alerts ("
            "trade_date, ts_code, strategy_type, alert_time, alert_type, reason_code"
            ") VALUES (?, ?, ?, ?, ?, ?)",
            ("20260630", "300001.SZ", StrategyType.B_CAPACITY_LEADER, "09:36:00", "WATCH", "STALE_B"),
        )
        conn.execute(
            "INSERT INTO intraday_alerts ("
            "trade_date, ts_code, strategy_type, alert_time, alert_type, reason_code"
            ") VALUES (?, ?, ?, ?, ?, ?)",
            ("20260630", "600001.SH", StrategyType.A_SPACE_LEADER, "09:36:00", "WATCH", "KEEP_A"),
        )
        conn.execute(
            "INSERT INTO intraday_alert_locks ("
            "trade_date, ts_code, strategy_type, alert_type, locked"
            ") VALUES (?, ?, ?, ?, ?)",
            ("20260630", "300001.SZ", StrategyType.B_CAPACITY_LEADER, "BUY_TRIGGER", 1),
        )
        conn.execute(
            "INSERT INTO intraday_alert_locks ("
            "trade_date, ts_code, strategy_type, alert_type, locked"
            ") VALUES (?, ?, ?, ?, ?)",
            ("20260630", "600001.SH", StrategyType.A_SPACE_LEADER, "BUY_TRIGGER", 1),
        )

    result = run_replay(db_path, "20260630", tmp_path / "missing.csv", tmp_path / "reports")

    with sqlite3.connect(db_path) as conn:
        alerts = conn.execute(
            "SELECT strategy_type, reason_code FROM intraday_alerts ORDER BY strategy_type"
        ).fetchall()
        locks = conn.execute(
            "SELECT strategy_type, alert_type FROM intraday_alert_locks ORDER BY strategy_type"
        ).fetchall()

    assert result.status == "SUCCESS"
    assert alerts == [(StrategyType.A_SPACE_LEADER, "KEEP_A")]
    assert locks == [(StrategyType.A_SPACE_LEADER, "BUY_TRIGGER")]
