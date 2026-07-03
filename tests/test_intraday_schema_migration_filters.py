from pathlib import Path
import sqlite3

from trading_x.db import init_db


def test_init_db_drops_legacy_alerts_missing_required_reason_code(
    tmp_path: Path,
) -> None:
    db_path = tmp_path / "trading_x.db"
    with sqlite3.connect(db_path) as conn:
        conn.execute(
            "CREATE TABLE intraday_alerts ("
            "id INTEGER, trade_date TEXT, ts_code TEXT, strategy_type TEXT, alert_time TEXT, "
            "alert_type TEXT, severity TEXT, rule_id TEXT, title TEXT, message TEXT, "
            "reason_code TEXT, state_before TEXT, state_after TEXT, snapshot_json TEXT, "
            "plan_json TEXT, created_at TEXT"
            ")"
        )
        conn.execute(
            "INSERT INTO intraday_alerts VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (
                1,
                "20260630",
                "300001.SZ",
                "B_CAPACITY_LEADER",
                "09:36:00",
                "BUY_TRIGGER",
                "HIGH",
                "B_BUY_TRIGGERED",
                "容量龙 BUY_TRIGGER",
                "B_BUY_TRIGGERED",
                "B_BUY_TRIGGERED",
                "ENTRY_ARMED",
                "BUY_TRIGGER",
                "{}",
                "{}",
                "2026-06-30T09:36:01+00:00",
            ),
        )
        conn.execute(
            "INSERT INTO intraday_alerts VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (
                2,
                "20260630",
                "300001.SZ",
                "B_CAPACITY_LEADER",
                "09:37:00",
                "WATCH",
                "LOW",
                None,
                "容量龙 WATCH",
                None,
                None,
                "OPEN_OBSERVING",
                "OPEN_OBSERVING",
                "{}",
                "{}",
                "2026-06-30T09:37:01+00:00",
            ),
        )
        conn.execute(
            "INSERT INTO intraday_alerts VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (
                3,
                "20260630",
                "300001.SZ",
                "B_CAPACITY_LEADER",
                "09:38:00",
                "WATCH",
                "LOW",
                "B_VWAP_CONFIRMING",
                "WATCH",
                "B_VWAP_CONFIRMING",
                "   ",
                "OPEN_OBSERVING",
                "OPEN_OBSERVING",
                "{}",
                "{}",
                "2026-06-30T09:38:01+00:00",
            ),
        )
        conn.execute(
            "INSERT INTO intraday_alerts VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (
                4,
                "20260630",
                "300001.SZ",
                "B_CAPACITY_LEADER",
                "09:39:00",
                "   ",
                "LOW",
                "B_VWAP_CONFIRMING",
                "WATCH",
                "B_VWAP_CONFIRMING",
                "B_VWAP_CONFIRMING",
                "OPEN_OBSERVING",
                "OPEN_OBSERVING",
                "{}",
                "{}",
                "2026-06-30T09:39:01+00:00",
            ),
        )

    init_db(db_path)

    with sqlite3.connect(db_path) as conn:
        rows = conn.execute(
            "SELECT alert_time, alert_type, reason_code FROM intraday_alerts"
        ).fetchall()
    assert rows == [("09:36:00", "BUY_TRIGGER", "B_BUY_TRIGGERED")]


def test_init_db_drops_legacy_alert_locks_missing_required_key_fields(
    tmp_path: Path,
) -> None:
    db_path = tmp_path / "trading_x.db"
    with sqlite3.connect(db_path) as conn:
        conn.execute(
            "CREATE TABLE intraday_alert_locks ("
            "trade_date TEXT, ts_code TEXT, strategy_type TEXT, alert_type TEXT, locked INTEGER, "
            "locked_at TEXT, rule_id TEXT, reset_count INTEGER DEFAULT 0, reset_reason TEXT"
            ")"
        )
        conn.execute(
            "INSERT INTO intraday_alert_locks VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (
                "20260630",
                "300001.SZ",
                "B_CAPACITY_LEADER",
                "BUY_TRIGGER",
                1,
                "2026-06-30T09:36:01+00:00",
                "B_BUY_TRIGGERED",
                0,
                None,
            ),
        )
        conn.execute(
            "INSERT INTO intraday_alert_locks VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (
                "20260630",
                "300001.SZ",
                "B_CAPACITY_LEADER",
                None,
                1,
                "2026-06-30T09:37:01+00:00",
                "ENTRY_CANCELLED_PRICE_OUT_OF_RANGE",
                0,
                None,
            ),
        )
        conn.execute(
            "INSERT INTO intraday_alert_locks VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (
                "20260630",
                "300001.SZ",
                "B_CAPACITY_LEADER",
                "   ",
                1,
                "2026-06-30T09:38:01+00:00",
                "ENTRY_CANCELLED_PRICE_OUT_OF_RANGE",
                0,
                None,
            ),
        )

    init_db(db_path)

    with sqlite3.connect(db_path) as conn:
        rows = conn.execute(
            "SELECT trade_date, ts_code, strategy_type, alert_type FROM intraday_alert_locks"
        ).fetchall()
    assert rows == [("20260630", "300001.SZ", "B_CAPACITY_LEADER", "BUY_TRIGGER")]


def test_init_db_drops_legacy_plans_missing_required_key_fields(
    tmp_path: Path,
) -> None:
    db_path = tmp_path / "trading_x.db"
    with sqlite3.connect(db_path) as conn:
        conn.execute(
            "CREATE TABLE intraday_plans ("
            "trade_date TEXT, ts_code TEXT, strategy_type TEXT, name TEXT"
            ")"
        )
        conn.execute(
            "INSERT INTO intraday_plans VALUES (?, ?, ?, ?)",
            ("20260630", "300001.SZ", "B_CAPACITY_LEADER", "容量龙"),
        )
        conn.execute(
            "INSERT INTO intraday_plans VALUES (?, ?, ?, ?)",
            ("20260630", "300002.SZ", None, "坏计划"),
        )
        conn.execute(
            "INSERT INTO intraday_plans VALUES (?, ?, ?, ?)",
            ("20260630", "300003.SZ", "   ", "空白策略"),
        )

    init_db(db_path)

    with sqlite3.connect(db_path) as conn:
        rows = conn.execute(
            "SELECT trade_date, ts_code, strategy_type, name FROM intraday_plans"
        ).fetchall()
    assert rows == [("20260630", "300001.SZ", "B_CAPACITY_LEADER", "容量龙")]
