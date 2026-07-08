from pathlib import Path
import sqlite3

from trading_x.intraday_schema import ensure_intraday_columns


def init_db(db_path: Path) -> None:
    db_path.parent.mkdir(parents=True, exist_ok=True)
    schema_path = Path(__file__).with_name("schema.sql")
    with sqlite3.connect(db_path) as conn:
        conn.executescript(schema_path.read_text(encoding="utf-8"))
        _ensure_candidates_columns(conn)
        _ensure_candidate_snapshot_columns(conn)
        _ensure_daily_quote_amount_columns(conn)
        _ensure_trade_log_rule_columns(conn)
        _ensure_post_close_activity_columns(conn)
        _ensure_backtest_trade_columns(conn)
        ensure_intraday_columns(conn)
        _ensure_theme_columns(conn)


def _ensure_candidates_columns(conn: sqlite3.Connection) -> None:
    rows = conn.execute("PRAGMA table_info(candidates)").fetchall()
    columns = {row[1] for row in rows}
    for name in (
        "theme_name",
        "theme_tags",
        "theme_rank_today",
        "theme_strength_score",
        "theme_position",
        "entry_reason",
        "veto_items",
    ):
        if name not in columns:
            column_type = "REAL" if name == "theme_strength_score" else "TEXT"
            if name == "theme_rank_today":
                column_type = "INTEGER"
            conn.execute(f"ALTER TABLE candidates ADD COLUMN {name} {column_type}")


def _ensure_daily_quote_amount_columns(conn: sqlite3.Connection) -> None:
    _ensure_columns(
        conn,
        "daily_quotes",
        (
            ("regular_amount", "REAL"),
            ("post_close_amount", "REAL"),
            ("total_amount", "REAL"),
            ("post_close_amount_ratio", "REAL"),
            ("post_close_data_available", "INTEGER"),
        ),
    )


def _ensure_trade_log_rule_columns(conn: sqlite3.Connection) -> None:
    _ensure_columns(
        conn,
        "trade_logs",
        (
            ("rule_version_at_entry", "TEXT"),
            ("rule_version_at_exit", "TEXT"),
        ),
    )


def _ensure_post_close_activity_columns(conn: sqlite3.Connection) -> None:
    _ensure_columns(
        conn,
        "post_close_activity",
        (
            ("close_price", "REAL"),
            ("post_close_amount", "REAL"),
            ("post_close_volume", "REAL"),
            ("post_close_amount_ratio", "REAL"),
            ("data_available", "INTEGER"),
            ("source", "TEXT"),
            ("created_at", "TEXT"),
        ),
    )


def _ensure_backtest_trade_columns(conn: sqlite3.Connection) -> None:
    _ensure_columns(
        conn,
        "backtest_trades",
        (
            ("exit_date", "TEXT"),
            ("exit_price", "REAL"),
            ("gross_pnl", "REAL"),
            ("cost_amount", "REAL"),
        ),
    )


def _ensure_theme_columns(conn: sqlite3.Connection) -> None:
    _ensure_columns(
        conn,
        "theme_members",
        (
            ("theme_tier", "TEXT DEFAULT 'IMPORTANT'"),
            ("theme_weight", "REAL DEFAULT 0.7"),
        ),
    )
    _ensure_columns(
        conn,
        "theme_daily_strength",
        (
            ("weighted_limit_up_count", "REAL"),
            ("weighted_avg_pct_chg", "REAL"),
            ("weighted_total_amount", "REAL"),
        ),
    )


def _ensure_candidate_snapshot_columns(conn: sqlite3.Connection) -> None:
    _ensure_columns(
        conn,
        "candidate_snapshots",
        (
            ("rule_version_at_signal", "TEXT"),
            ("rule_regime_at_signal", "TEXT"),
            ("entry_low", "REAL"),
            ("entry_high", "REAL"),
            ("stop_price", "REAL"),
            ("breakout_price", "REAL"),
            ("max_position_cash", "REAL"),
            ("max_loss", "REAL"),
        ),
    )


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
