import sqlite3

from trading_x.intraday_schema_sql import (
    COPY_INTRADAY_ALERT_LOCKS_SQL,
    COPY_INTRADAY_ALERTS_SQL,
    COPY_INTRADAY_PLANS_SQL,
    COPY_INTRADAY_REPLAY_RUNS_SQL,
    CREATE_INTRADAY_ALERT_LOCKS_SQL,
    CREATE_INTRADAY_ALERTS_SQL,
    CREATE_INTRADAY_PLANS_SQL,
    CREATE_INTRADAY_REPLAY_RUNS_SQL,
)


def ensure_intraday_columns(conn: sqlite3.Connection) -> None:
    _ensure_columns(
        conn,
        "intraday_plans",
        (
            ("name", "TEXT"),
            ("allow_trade", "INTEGER"),
            ("plan_status", "TEXT"),
            ("entry_low", "REAL"),
            ("entry_high", "REAL"),
            ("breakout_price", "REAL"),
            ("stop_price", "REAL"),
            ("max_stop_distance", "REAL"),
            ("max_position_cash", "REAL"),
            ("max_loss", "REAL"),
            ("official_pre_close", "REAL"),
            ("pre_close_source", "TEXT"),
            ("vwap_active_after", "TEXT"),
            ("vwap_above_confirm_seconds", "INTEGER"),
            ("volume_gate_enabled", "INTEGER"),
            ("volume_min_abs_amount", "REAL"),
            ("volume_same_window_multiplier", "REAL"),
            ("volume_ratio_0935", "REAL"),
            ("volume_ratio_0945", "REAL"),
            ("volume_ratio_1000", "REAL"),
            ("theme_name", "TEXT"),
            ("theme_confidence", "TEXT"),
            ("theme_strength_score", "REAL"),
            ("source_candidate_id", "TEXT"),
            ("source_report_date", "TEXT"),
            ("plan_json", "TEXT"),
            ("system_version", "TEXT"),
            ("created_at", "TEXT"),
        ),
    )
    plan_key = ("trade_date", "ts_code", "strategy_type")
    if _primary_key_columns(conn, "intraday_plans") != plan_key or not set(plan_key) <= _required_columns(
        conn, "intraday_plans"
    ):
        _rebuild_intraday_plans(conn)
    _ensure_columns(
        conn,
        "intraday_alerts",
        (
            ("id", "INTEGER"),
            ("trade_date", "TEXT"),
            ("ts_code", "TEXT"),
            ("strategy_type", "TEXT"),
            ("alert_time", "TEXT"),
            ("alert_type", "TEXT"),
            ("severity", "TEXT"),
            ("rule_id", "TEXT"),
            ("title", "TEXT"),
            ("message", "TEXT"),
            ("reason_code", "TEXT"),
            ("state_before", "TEXT"),
            ("state_after", "TEXT"),
            ("snapshot_json", "TEXT"),
            ("plan_json", "TEXT"),
            ("created_at", "TEXT"),
        ),
    )
    _ensure_columns(
        conn,
        "intraday_alert_locks",
        (
            ("trade_date", "TEXT"),
            ("ts_code", "TEXT"),
            ("strategy_type", "TEXT"),
            ("alert_type", "TEXT"),
            ("locked", "INTEGER"),
            ("locked_at", "TEXT"),
            ("rule_id", "TEXT"),
            ("reset_count", "INTEGER DEFAULT 0"),
            ("reset_reason", "TEXT"),
        ),
    )
    _ensure_columns(
        conn,
        "intraday_replay_runs",
        (
            ("id", "INTEGER"),
            ("trade_date", "TEXT"),
            ("input_file", "TEXT"),
            ("input_sha256", "TEXT"),
            ("plan_count", "INTEGER"),
            ("alert_count", "INTEGER"),
            ("status", "TEXT"),
            ("started_at", "TEXT"),
            ("ended_at", "TEXT"),
            ("error_message", "TEXT"),
        ),
    )
    _ensure_intraday_output_constraints(conn)


def _ensure_intraday_output_constraints(conn: sqlite3.Connection) -> None:
    alert_required = (
        "trade_date",
        "ts_code",
        "strategy_type",
        "alert_time",
        "alert_type",
        "reason_code",
    )
    if _primary_key_columns(conn, "intraday_alerts") != ("id",) or not set(alert_required) <= _required_columns(
        conn, "intraday_alerts"
    ):
        _rebuild_intraday_alerts(conn)
    lock_key = (
        "trade_date",
        "ts_code",
        "strategy_type",
        "alert_type",
    )
    if _primary_key_columns(conn, "intraday_alert_locks") != lock_key or not set(lock_key) <= _required_columns(
        conn, "intraday_alert_locks"
    ):
        _rebuild_intraday_alert_locks(conn)
    replay_run_required = (
        "trade_date",
        "input_file",
        "input_sha256",
        "plan_count",
        "alert_count",
        "status",
        "started_at",
        "ended_at",
    )
    if _primary_key_columns(conn, "intraday_replay_runs") != ("id",) or not set(
        replay_run_required
    ) <= _required_columns(conn, "intraday_replay_runs"):
        _rebuild_intraday_replay_runs(conn)


def _primary_key_columns(conn: sqlite3.Connection, table_name: str) -> tuple[str, ...]:
    rows = conn.execute(f"PRAGMA table_info({table_name})").fetchall()
    return tuple(row[1] for row in sorted(rows, key=lambda row: row[5]) if row[5] > 0)


def _required_columns(conn: sqlite3.Connection, table_name: str) -> set[str]:
    rows = conn.execute(f"PRAGMA table_info({table_name})").fetchall()
    return {row[1] for row in rows if row[3] > 0}


def _rebuild_intraday_plans(conn: sqlite3.Connection) -> None:
    conn.execute("ALTER TABLE intraday_plans RENAME TO intraday_plans_old")
    conn.execute(CREATE_INTRADAY_PLANS_SQL)
    conn.execute(COPY_INTRADAY_PLANS_SQL)
    conn.execute("DROP TABLE intraday_plans_old")


def _rebuild_intraday_alerts(conn: sqlite3.Connection) -> None:
    conn.execute("ALTER TABLE intraday_alerts RENAME TO intraday_alerts_old")
    conn.execute(CREATE_INTRADAY_ALERTS_SQL)
    conn.execute(COPY_INTRADAY_ALERTS_SQL)
    conn.execute("DROP TABLE intraday_alerts_old")


def _rebuild_intraday_alert_locks(conn: sqlite3.Connection) -> None:
    conn.execute("ALTER TABLE intraday_alert_locks RENAME TO intraday_alert_locks_old")
    conn.execute(CREATE_INTRADAY_ALERT_LOCKS_SQL)
    conn.execute(COPY_INTRADAY_ALERT_LOCKS_SQL)
    conn.execute("DROP TABLE intraday_alert_locks_old")


def _rebuild_intraday_replay_runs(conn: sqlite3.Connection) -> None:
    conn.execute("ALTER TABLE intraday_replay_runs RENAME TO intraday_replay_runs_old")
    conn.execute(CREATE_INTRADAY_REPLAY_RUNS_SQL)
    conn.execute(COPY_INTRADAY_REPLAY_RUNS_SQL)
    conn.execute("DROP TABLE intraday_replay_runs_old")


def _ensure_columns(
    conn: sqlite3.Connection,
    table_name: str,
    column_specs: tuple[tuple[str, str], ...],
) -> None:
    rows = conn.execute(f"PRAGMA table_info({table_name})").fetchall()
    columns = {row[1] for row in rows}
    for name, column_type in column_specs:
        if name not in columns:
            conn.execute(f"ALTER TABLE {table_name} ADD COLUMN {name} {column_type}")
