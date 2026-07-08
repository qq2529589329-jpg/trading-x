from dataclasses import dataclass
from pathlib import Path
import sqlite3

from trading_x.db import init_db
from trading_x.research import ResearchEdgeRequest, analyze_research_edge
from trading_x.types import StrategyType


@dataclass(frozen=True, slots=True)
class QuoteRow:
    trade_date: str
    ts_code: str
    close: float


def test_research_edge_report_compares_buy_filled_to_candidate_benchmark(tmp_path: Path) -> None:
    # Given
    db_path = tmp_path / "trading_x.db"
    report_dir = tmp_path / "reports"
    init_db(db_path)
    with sqlite3.connect(db_path) as conn:
        _insert_backtest_run(conn)
        _insert_order(conn, "300001.SZ", "BUY_FILLED")
        _insert_order(conn, "300002.SZ", "OPEN_ABOVE_ENTRY_HIGH")
        _insert_trade(conn, "300001.SZ")
        conn.execute(
            "INSERT INTO market_regimes (trade_date, method_version, market_regime, market_temperature, "
            "limit_up_count, limit_down_count, avg_pct_chg, total_amount, candidate_count, data_source, created_at) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            ("20260701", "regime-v1", "REPAIR", 0.6, 8, 1, 1.2, 1000000.0, 2, "fixture", "2026-07-01T16:00:00+00:00"),
        )
        for ts_code, start_close in (("300001.SZ", 10.0), ("300002.SZ", 20.0)):
            for index in range(0, 12):
                close = start_close + index
                _insert_quote(conn, QuoteRow(f"202607{index + 2:02d}", ts_code, close))

    # When
    result = analyze_research_edge(db_path, ResearchEdgeRequest("run-edge", report_dir))

    # Then
    report = result.report_path.read_text(encoding="utf-8")
    assert result.buy_filled_count == 1
    assert result.benchmark_count == 2
    assert "| 1 | 1 | 10.0000% | 10.0000% | 2 |" in report
    assert "OPEN_ABOVE_ENTRY_HIGH" in report
    assert "REPAIR" in report
    assert "2026" in report


def _insert_backtest_run(conn: sqlite3.Connection) -> None:
    conn.execute(
        "INSERT INTO backtest_results (run_id, start_date, end_date, strategy_type, config_version, "
        "candidate_count, order_count, trade_count, win_count, loss_count, total_return, max_drawdown, "
        "status, summary_json, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
        (
            "run-edge",
            "20260701",
            "20260720",
            StrategyType.B_CAPACITY_LEADER.value,
            "v1.0",
            2,
            2,
            1,
            1,
            0,
            0.1,
            0.0,
            "SUCCESS",
            "{}",
            "2026-07-20T16:00:00+00:00",
        ),
    )


def _insert_order(conn: sqlite3.Connection, ts_code: str, reason_code: str) -> None:
    conn.execute(
        "INSERT INTO backtest_orders (run_id, signal_date, trade_date, ts_code, strategy_type, side, "
        "planned_price, reason_code, source_run_id, created_at) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
        (
            "run-edge",
            "20260701",
            "20260702",
            ts_code,
            StrategyType.B_CAPACITY_LEADER.value,
            "BUY",
            10.0,
            reason_code,
            "candidate-run",
            "2026-07-02T09:30:00+00:00",
        ),
    )


def _insert_trade(conn: sqlite3.Connection, ts_code: str) -> None:
    conn.execute(
        "INSERT INTO backtest_trades (run_id, signal_date, trade_date, ts_code, strategy_type, side, price, shares, "
        "cash_amount, exit_date, exit_price, gross_pnl, cost_amount, pnl, reason_code, created_at) "
        "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
        (
            "run-edge",
            "20260701",
            "20260702",
            ts_code,
            StrategyType.B_CAPACITY_LEADER.value,
            "BUY",
            10.0,
            1000,
            10000.0,
            "20260703",
            11.0,
            1000.0,
            10.0,
            990.0,
            "BUY_FILLED",
            "2026-07-02T09:30:00+00:00",
        ),
    )


def _insert_quote(conn: sqlite3.Connection, quote: QuoteRow) -> None:
    conn.execute(
        "INSERT INTO daily_quotes (trade_date, ts_code, open, high, low, close, pre_close, pct_chg, vol, amount) "
        "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
        (
            quote.trade_date,
            quote.ts_code,
            quote.close,
            quote.close,
            quote.close,
            quote.close,
            quote.close,
            0.0,
            1000.0,
            quote.close * 1000.0,
        ),
    )