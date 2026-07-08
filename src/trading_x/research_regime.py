from datetime import UTC, datetime
from pathlib import Path
import sqlite3

from trading_x.research_models import (
    DATA_SOURCE,
    DailyRegimeStats,
    RegimeClassificationRequest,
    RegimeClassificationResult,
    ResearchDateRange,
)


def classify_market_regimes(
    db_path: Path,
    request: RegimeClassificationRequest,
) -> RegimeClassificationResult:
    with sqlite3.connect(db_path) as conn:
        date_range = ResearchDateRange(request.start_date, _resolve_end_date(conn, request))
        created_at = _utc_now_text()
        proxy_count = _refresh_limit_proxy(conn, date_range, created_at)
        stats = _daily_regime_stats(conn, date_range)
        conn.executemany(
            "INSERT OR REPLACE INTO market_regimes ("
            "trade_date, method_version, market_regime, market_temperature, limit_up_count, "
            "limit_down_count, avg_pct_chg, total_amount, candidate_count, data_source, created_at"
            ") VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            [
                (
                    row.trade_date,
                    request.method_version,
                    _regime_label(row),
                    row.avg_pct_chg + row.limit_up_count * 0.5 - row.limit_down_count * 0.7,
                    row.limit_up_count,
                    row.limit_down_count,
                    row.avg_pct_chg,
                    row.total_amount,
                    row.candidate_count,
                    DATA_SOURCE,
                    created_at,
                )
                for row in stats
            ],
        )
    return RegimeClassificationResult(date_range.start_date, date_range.end_date, len(stats), proxy_count)


def _resolve_end_date(conn: sqlite3.Connection, request: RegimeClassificationRequest) -> str:
    if request.end_date != "latest":
        return request.end_date
    row = conn.execute("SELECT MAX(trade_date) FROM daily_quotes").fetchone()
    return request.start_date if row is None or row[0] is None else str(row[0])


def _refresh_limit_proxy(conn: sqlite3.Connection, date_range: ResearchDateRange, created_at: str) -> int:
    conn.execute(
        "DELETE FROM limit_events_daily_proxy WHERE trade_date BETWEEN ? AND ?",
        (date_range.start_date, date_range.end_date),
    )
    cursor = conn.execute(
        "INSERT INTO limit_events_daily_proxy ("
        "trade_date, ts_code, is_limit_up_close, is_limit_down_close, high_reached_up_limit, "
        "low_reached_down_limit, data_source, created_at"
        ") SELECT dq.trade_date, dq.ts_code, "
        "CASE WHEN COALESCE(lp.up_limit, 0) > 0 AND dq.close >= lp.up_limit * 0.999 THEN 1 "
        "WHEN dq.pct_chg >= 9.8 THEN 1 ELSE 0 END, "
        "CASE WHEN COALESCE(lp.down_limit, 0) > 0 AND dq.close <= lp.down_limit * 1.001 THEN 1 "
        "WHEN dq.pct_chg <= -9.8 THEN 1 ELSE 0 END, "
        "CASE WHEN COALESCE(lp.up_limit, 0) > 0 AND dq.high >= lp.up_limit * 0.999 THEN 1 ELSE 0 END, "
        "CASE WHEN COALESCE(lp.down_limit, 0) > 0 AND dq.low <= lp.down_limit * 1.001 THEN 1 ELSE 0 END, "
        "?, ? "
        "FROM daily_quotes dq LEFT JOIN stk_limit_prices lp "
        "ON dq.trade_date = lp.trade_date AND dq.ts_code = lp.ts_code "
        "WHERE dq.trade_date BETWEEN ? AND ?",
        (DATA_SOURCE, created_at, date_range.start_date, date_range.end_date),
    )
    return cursor.rowcount


def _daily_regime_stats(conn: sqlite3.Connection, date_range: ResearchDateRange) -> list[DailyRegimeStats]:
    rows = conn.execute(
        "SELECT dq.trade_date, AVG(COALESCE(dq.pct_chg, 0)), SUM(COALESCE(dq.amount, 0)), "
        "SUM(CASE WHEN lep.is_limit_up_close = 1 THEN 1 ELSE 0 END), "
        "SUM(CASE WHEN lep.is_limit_down_close = 1 THEN 1 ELSE 0 END), "
        "(SELECT COUNT(*) FROM candidates_latest cs WHERE cs.trade_date = dq.trade_date) "
        "FROM daily_quotes dq JOIN limit_events_daily_proxy lep "
        "ON dq.trade_date = lep.trade_date AND dq.ts_code = lep.ts_code "
        "WHERE dq.trade_date BETWEEN ? AND ? GROUP BY dq.trade_date ORDER BY dq.trade_date",
        (date_range.start_date, date_range.end_date),
    ).fetchall()
    return [
        DailyRegimeStats(str(row[0]), float(row[1]), float(row[2]), int(row[3]), int(row[4]), int(row[5]))
        for row in rows
    ]


def _regime_label(stats: DailyRegimeStats) -> str:
    if stats.limit_down_count > stats.limit_up_count and stats.avg_pct_chg < 0:
        return "RISK_OFF"
    if stats.limit_up_count > stats.limit_down_count or stats.avg_pct_chg >= 1.0:
        return "HOT"
    if stats.avg_pct_chg < 0:
        return "COOL"
    return "NORMAL"


def _utc_now_text() -> str:
    return datetime.now(UTC).isoformat()
