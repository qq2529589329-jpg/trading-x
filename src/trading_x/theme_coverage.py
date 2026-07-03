from pathlib import Path
from dataclasses import dataclass
import csv
import sqlite3

from trading_x.theme_models import (
    THEME_MEMBER_EXPORT_COLUMNS,
    ThemeCoverage,
    ThemeMissingCandidate,
    ThemeMissingExportRequest,
)


DEFAULT_TOP_AMOUNT = 200
DEFAULT_TOP_LIMIT_ACTIVE = 100


@dataclass(frozen=True, slots=True)
class _MissingSelection:
    trade_date: str
    top_amount: int
    top_limit_active: int


def theme_coverage(db_path: Path, trade_date: str) -> ThemeCoverage:
    with sqlite3.connect(db_path) as conn:
        stock_total = conn.execute("SELECT COUNT(*) FROM stock_universe WHERE included = 1").fetchone()[0]
        mapped = conn.execute(
            "SELECT COUNT(*) FROM stock_universe s "
            "JOIN theme_members m ON m.ts_code = s.ts_code "
            "WHERE s.included = 1"
        ).fetchone()[0]
        candidate_total = conn.execute(
            "SELECT COUNT(DISTINCT ts_code) FROM candidates WHERE trade_date = ?",
            (trade_date,),
        ).fetchone()[0]
        candidate_mapped = conn.execute(
            "SELECT COUNT(DISTINCT c.ts_code) FROM candidates c "
            "JOIN theme_members m ON m.ts_code = c.ts_code "
            "WHERE c.trade_date = ?",
            (trade_date,),
        ).fetchone()[0]
        unmapped = conn.execute(
            "SELECT DISTINCT c.ts_code FROM candidates c "
            "LEFT JOIN theme_members m ON m.ts_code = c.ts_code "
            "WHERE c.trade_date = ? AND m.ts_code IS NULL "
            "ORDER BY c.ts_code",
            (trade_date,),
        ).fetchall()
        limit_total, limit_mapped = _limit_up_coverage(conn, trade_date)
        top_total, top_mapped = _top_amount_coverage(conn, trade_date, DEFAULT_TOP_AMOUNT)
        active_total, active_mapped = _limit_active_coverage(conn, trade_date, DEFAULT_TOP_LIMIT_ACTIVE)
        missing = _missing_candidates(
            conn,
            _MissingSelection(
                trade_date=trade_date,
                top_amount=DEFAULT_TOP_AMOUNT,
                top_limit_active=DEFAULT_TOP_LIMIT_ACTIVE,
            ),
        )
    return ThemeCoverage(
        stock_total=stock_total,
        mapped_stock_count=mapped,
        candidate_total=candidate_total,
        candidate_mapped_count=candidate_mapped,
        limit_up_total=limit_total,
        limit_up_mapped_count=limit_mapped,
        top_amount_total=top_total,
        top_amount_mapped_count=top_mapped,
        limit_active_total=active_total,
        limit_active_mapped_count=active_mapped,
        unmapped_candidates=tuple(row[0] for row in unmapped),
        missing_suggestions=tuple(item.ts_code for item in missing),
    )


def export_missing_theme_candidates(db_path: Path, request: ThemeMissingExportRequest) -> int:
    with sqlite3.connect(db_path) as conn:
        rows = _missing_candidates(
            conn,
            _MissingSelection(
                trade_date=request.trade_date,
                top_amount=request.top_amount,
                top_limit_active=request.top_limit_active,
            ),
        )
    request.output_path.parent.mkdir(parents=True, exist_ok=True)
    with request.output_path.open("w", encoding="utf-8", newline="") as file:
        writer = csv.DictWriter(file, fieldnames=THEME_MEMBER_EXPORT_COLUMNS)
        writer.writeheader()
        for row in rows:
            writer.writerow(
                {
                    "ts_code": row.ts_code,
                    "name": row.name,
                    "industry": row.industry,
                    "theme_primary": "",
                    "theme_tags": "",
                    "theme_tier": "RELATED",
                    "theme_weight": "0.4",
                    "theme_source": "manual",
                    "confidence": "LOW",
                    "updated_at": request.trade_date,
                    "notes": row.reason,
                    "reason": row.reason,
                }
            )
    return len(rows)


def _limit_up_coverage(conn: sqlite3.Connection, trade_date: str) -> tuple[int, int]:
    row = conn.execute(
        "SELECT COUNT(*), SUM(CASE WHEN m.ts_code IS NULL THEN 0 ELSE 1 END) "
        "FROM stock_universe s "
        "JOIN daily_quotes d ON d.ts_code = s.ts_code AND d.trade_date = ? "
        "JOIN stk_limit_prices l ON l.ts_code = s.ts_code AND l.trade_date = ? "
        "LEFT JOIN theme_members m ON m.ts_code = s.ts_code "
        "WHERE s.included = 1 AND l.up_limit > 0 AND d.close >= l.up_limit - 0.001",
        (trade_date, trade_date),
    ).fetchone()
    return row[0] or 0, row[1] or 0


def _top_amount_coverage(conn: sqlite3.Connection, trade_date: str, limit: int) -> tuple[int, int]:
    row = conn.execute(
        "WITH top_amount AS ("
        "SELECT s.ts_code FROM stock_universe s "
        "JOIN daily_quotes d ON d.ts_code = s.ts_code AND d.trade_date = ? "
        "WHERE s.included = 1 ORDER BY d.amount DESC LIMIT ?"
        ") "
        "SELECT COUNT(*), SUM(CASE WHEN m.ts_code IS NULL THEN 0 ELSE 1 END) "
        "FROM top_amount t LEFT JOIN theme_members m ON m.ts_code = t.ts_code",
        (trade_date, limit),
    ).fetchone()
    return row[0] or 0, row[1] or 0


def _limit_active_coverage(conn: sqlite3.Connection, trade_date: str, limit: int) -> tuple[int, int]:
    row = conn.execute(
        "WITH recent_dates AS ("
        "SELECT DISTINCT trade_date FROM daily_quotes WHERE trade_date <= ? ORDER BY trade_date DESC LIMIT 20"
        "), ranked AS ("
        "SELECT s.ts_code, "
        "SUM(CASE WHEN l.up_limit > 0 AND d.close >= l.up_limit - 0.001 THEN 1 ELSE 0 END) AS limit_count, "
        "SUM(d.amount) AS amount_sum "
        "FROM stock_universe s "
        "JOIN daily_quotes d ON d.ts_code = s.ts_code "
        "JOIN recent_dates rd ON rd.trade_date = d.trade_date "
        "LEFT JOIN stk_limit_prices l ON l.ts_code = s.ts_code AND l.trade_date = d.trade_date "
        "WHERE s.included = 1 GROUP BY s.ts_code"
        "), active AS ("
        "SELECT ts_code FROM ranked WHERE limit_count > 0 ORDER BY limit_count DESC, amount_sum DESC LIMIT ?"
        ") "
        "SELECT COUNT(*), SUM(CASE WHEN m.ts_code IS NULL THEN 0 ELSE 1 END) "
        "FROM active a LEFT JOIN theme_members m ON m.ts_code = a.ts_code",
        (trade_date, limit),
    ).fetchone()
    return row[0] or 0, row[1] or 0


def _missing_candidates(
    conn: sqlite3.Connection,
    selection: _MissingSelection,
) -> list[ThemeMissingCandidate]:
    rows = [
        *_candidate_missing(conn, selection.trade_date),
        *_history_missing(conn, selection.trade_date),
        *_top_amount_missing(conn, selection.trade_date, selection.top_amount),
        *_limit_active_missing(conn, selection.trade_date, selection.top_limit_active),
    ]
    by_code: dict[str, ThemeMissingCandidate] = {}
    for row in rows:
        by_code.setdefault(row.ts_code, row)
    return list(by_code.values())


def _candidate_missing(conn: sqlite3.Connection, trade_date: str) -> list[ThemeMissingCandidate]:
    rows = conn.execute(
        "SELECT DISTINCT c.ts_code, COALESCE(s.name, ''), COALESCE(s.market, ''), 'candidate' "
        "FROM candidates c "
        "LEFT JOIN theme_members m ON m.ts_code = c.ts_code "
        "LEFT JOIN stock_universe s ON s.ts_code = c.ts_code "
        "WHERE c.trade_date = ? AND m.ts_code IS NULL ORDER BY c.ts_code",
        (trade_date,),
    ).fetchall()
    return [ThemeMissingCandidate(*row) for row in rows]


def _history_missing(conn: sqlite3.Connection, trade_date: str) -> list[ThemeMissingCandidate]:
    rows = conn.execute(
        "SELECT DISTINCT cs.ts_code, COALESCE(s.name, cs.name), COALESCE(s.market, ''), 'history_candidate' "
        "FROM candidate_snapshots cs "
        "LEFT JOIN theme_members m ON m.ts_code = cs.ts_code "
        "LEFT JOIN stock_universe s ON s.ts_code = cs.ts_code "
        "WHERE cs.trade_date <= ? AND m.ts_code IS NULL ORDER BY cs.ts_code",
        (trade_date,),
    ).fetchall()
    return [ThemeMissingCandidate(*row) for row in rows]


def _top_amount_missing(conn: sqlite3.Connection, trade_date: str, limit: int) -> list[ThemeMissingCandidate]:
    rows = conn.execute(
        "WITH top_amount AS ("
        "SELECT s.ts_code, s.name, s.market FROM stock_universe s "
        "JOIN daily_quotes d ON d.ts_code = s.ts_code AND d.trade_date = ? "
        "WHERE s.included = 1 ORDER BY d.amount DESC LIMIT ?"
        ") "
        "SELECT t.ts_code, t.name, COALESCE(t.market, ''), 'top_amount' "
        "FROM top_amount t LEFT JOIN theme_members m ON m.ts_code = t.ts_code "
        "WHERE m.ts_code IS NULL ORDER BY t.ts_code",
        (trade_date, limit),
    ).fetchall()
    return [ThemeMissingCandidate(*row) for row in rows]


def _limit_active_missing(conn: sqlite3.Connection, trade_date: str, limit: int) -> list[ThemeMissingCandidate]:
    rows = conn.execute(
        "WITH recent_dates AS ("
        "SELECT DISTINCT trade_date FROM daily_quotes WHERE trade_date <= ? ORDER BY trade_date DESC LIMIT 20"
        "), ranked AS ("
        "SELECT s.ts_code, s.name, s.market, "
        "SUM(CASE WHEN l.up_limit > 0 AND d.close >= l.up_limit - 0.001 THEN 1 ELSE 0 END) AS limit_count, "
        "SUM(d.amount) AS amount_sum "
        "FROM stock_universe s "
        "JOIN daily_quotes d ON d.ts_code = s.ts_code "
        "JOIN recent_dates rd ON rd.trade_date = d.trade_date "
        "LEFT JOIN stk_limit_prices l ON l.ts_code = s.ts_code AND l.trade_date = d.trade_date "
        "WHERE s.included = 1 GROUP BY s.ts_code, s.name, s.market"
        "), active AS ("
        "SELECT ts_code, name, market FROM ranked "
        "WHERE limit_count > 0 ORDER BY limit_count DESC, amount_sum DESC LIMIT ?"
        ") "
        "SELECT a.ts_code, a.name, COALESCE(a.market, ''), 'limit_active' "
        "FROM active a LEFT JOIN theme_members m ON m.ts_code = a.ts_code "
        "WHERE m.ts_code IS NULL ORDER BY a.ts_code",
        (trade_date, limit),
    ).fetchall()
    return [ThemeMissingCandidate(*row) for row in rows]
