from dataclasses import dataclass
from pathlib import Path
import sqlite3

from trading_x.research_models import BacktestTrustAuditRequest, BacktestTrustAuditResult


@dataclass(frozen=True, slots=True)
class BacktestAuditUnavailableError(Exception):
    reason: str

    def __str__(self) -> str:
        return self.reason


@dataclass(frozen=True, slots=True)
class _Issue:
    code: str
    count: int


def audit_research_backtest(db_path: Path, request: BacktestTrustAuditRequest) -> BacktestTrustAuditResult:
    with sqlite3.connect(db_path) as conn:
        run_id = request.run_id if request.run_id is not None else _latest_run_id(conn)
        issues = tuple(issue for issue in _audit_issues(conn, run_id) if issue.count > 0)
    issue_count = sum(issue.count for issue in issues)
    status = "PASS" if issue_count == 0 else "FAIL"
    report_path = request.report_dir / "backtest_trust_audit.md"
    result = BacktestTrustAuditResult(run_id, status, issue_count, report_path)
    _write_report(result, issues)
    return result


def _latest_run_id(conn: sqlite3.Connection) -> str:
    row = conn.execute("SELECT run_id FROM backtest_results ORDER BY created_at DESC LIMIT 1").fetchone()
    if row is None:
        raise BacktestAuditUnavailableError("no backtest_results run found")
    return str(row[0])


def _audit_issues(conn: sqlite3.Connection, run_id: str) -> tuple[_Issue, ...]:
    return (
        _Issue("ORDER_COUNT_MISMATCH", _order_count_mismatch(conn, run_id)),
        _Issue("TRADE_COUNT_MISMATCH", _trade_count_mismatch(conn, run_id)),
        _Issue(
            "LOOKAHEAD_ORDER",
            _count(conn, "SELECT COUNT(*) FROM backtest_orders WHERE run_id = ? AND trade_date <= signal_date", (run_id,)),
        ),
        _Issue(
            "T1_EXIT_VIOLATION",
            _count(
                conn,
                "SELECT COUNT(*) FROM backtest_trades WHERE run_id = ? AND (exit_date IS NULL OR exit_date <= trade_date)",
                (run_id,),
            ),
        ),
        _Issue(
            "BUY_QUOTE_MISSING",
            _count(
                conn,
                "SELECT COUNT(*) FROM backtest_trades t LEFT JOIN daily_quotes q "
                "ON q.trade_date = t.trade_date AND q.ts_code = t.ts_code "
                "WHERE t.run_id = ? AND q.ts_code IS NULL",
                (run_id,),
            ),
        ),
        _Issue(
            "BUY_PRICE_OUT_OF_RANGE",
            _count(
                conn,
                "SELECT COUNT(*) FROM backtest_trades t JOIN daily_quotes q "
                "ON q.trade_date = t.trade_date AND q.ts_code = t.ts_code "
                "WHERE t.run_id = ? AND (t.price < q.low OR t.price > q.high)",
                (run_id,),
            ),
        ),
        _Issue(
            "EXIT_PRICE_MISMATCH",
            _count(
                conn,
                "SELECT COUNT(*) FROM backtest_trades t LEFT JOIN daily_quotes q "
                "ON q.trade_date = t.exit_date AND q.ts_code = t.ts_code "
                "WHERE t.run_id = ? AND (q.ts_code IS NULL OR ABS(t.exit_price - q.close) > 0.0001)",
                (run_id,),
            ),
        ),
        _Issue(
            "ONE_WORD_LIMIT_UP_FILLED",
            _count(
                conn,
                "SELECT COUNT(*) FROM backtest_trades t JOIN daily_quotes q "
                "ON q.trade_date = t.trade_date AND q.ts_code = t.ts_code "
                "JOIN stk_limit_prices lp ON lp.trade_date = t.trade_date AND lp.ts_code = t.ts_code "
                "WHERE t.run_id = ? AND q.open >= lp.up_limit * 0.999 AND q.high >= lp.up_limit * 0.999 "
                "AND q.low >= lp.up_limit * 0.999 AND q.close >= lp.up_limit * 0.999",
                (run_id,),
            ),
        ),
        _Issue(
            "CASH_AMOUNT_MISMATCH",
            _count(
                conn,
                "SELECT COUNT(*) FROM backtest_trades WHERE run_id = ? AND ABS(cash_amount - price * shares) > 0.0001",
                (run_id,),
            ),
        ),
        _Issue(
            "PNL_MISMATCH",
            _count(
                conn,
                "SELECT COUNT(*) FROM backtest_trades WHERE run_id = ? "
                "AND ABS(pnl - (gross_pnl - cost_amount)) > 0.0001",
                (run_id,),
            ),
        ),
        _Issue(
            "COST_MISSING",
            _count(conn, "SELECT COUNT(*) FROM backtest_trades WHERE run_id = ? AND cost_amount <= 0", (run_id,)),
        ),
        _Issue("ADJ_FACTOR_MISSING", _missing_adj_factor_count(conn, run_id)),
    )


def _order_count_mismatch(conn: sqlite3.Connection, run_id: str) -> int:
    expected = conn.execute("SELECT order_count FROM backtest_results WHERE run_id = ?", (run_id,)).fetchone()
    actual = _count(conn, "SELECT COUNT(*) FROM backtest_orders WHERE run_id = ?", (run_id,))
    if expected is None:
        return 1
    return 0 if int(expected[0]) == actual else 1


def _trade_count_mismatch(conn: sqlite3.Connection, run_id: str) -> int:
    expected = conn.execute("SELECT trade_count FROM backtest_results WHERE run_id = ?", (run_id,)).fetchone()
    actual = _count(conn, "SELECT COUNT(*) FROM backtest_trades WHERE run_id = ?", (run_id,))
    if expected is None:
        return 1
    return 0 if int(expected[0]) == actual else 1


def _missing_adj_factor_count(conn: sqlite3.Connection, run_id: str) -> int:
    return _count(
        conn,
        "SELECT COUNT(*) FROM ("
        "SELECT signal_date AS trade_date, ts_code FROM backtest_trades WHERE run_id = ? "
        "UNION ALL SELECT trade_date, ts_code FROM backtest_trades WHERE run_id = ? "
        "UNION ALL SELECT exit_date, ts_code FROM backtest_trades WHERE run_id = ?"
        ") d LEFT JOIN adj_factors a ON a.trade_date = d.trade_date AND a.ts_code = d.ts_code "
        "WHERE a.ts_code IS NULL",
        (run_id, run_id, run_id),
    )


def _count(conn: sqlite3.Connection, sql: str, params: tuple[str, ...]) -> int:
    return int(conn.execute(sql, params).fetchone()[0])


def _write_report(result: BacktestTrustAuditResult, issues: tuple[_Issue, ...]) -> None:
    result.report_path.parent.mkdir(parents=True, exist_ok=True)
    issue_text = ", ".join(f"{issue.code}={issue.count}" for issue in issues) if issues else "none"
    lines = [
        "# Backtest Trust Audit",
        "",
        f"- run_id: {result.run_id}",
        f"- status: {result.status}",
        f"- issue_count: {result.issue_count}",
        f"- issues: {issue_text}",
    ]
    result.report_path.write_text("\n".join(lines) + "\n", encoding="utf-8")
