from datetime import UTC, datetime
from pathlib import Path
import hashlib
import json
import sqlite3

from trading_x.research_backtest_plans import decide_backtest_order, resolve_backtest_plan
from trading_x.research_models import (
    DATA_SOURCE,
    BacktestSummary,
    ResearchBacktestRequest,
    ResearchBacktestResult,
    ResearchDateRange,
)


def run_research_backtest(
    db_path: Path,
    request: ResearchBacktestRequest,
) -> ResearchBacktestResult:
    with sqlite3.connect(db_path) as conn:
        conn.row_factory = sqlite3.Row
        date_range = ResearchDateRange(request.start_date, _resolve_end_date(conn, request))
        run_id = _run_id(request, date_range)
        _clear_backtest_run(conn, run_id)
        candidates = conn.execute(
            "SELECT cl.run_id, cl.trade_date, cl.rank, cl.ts_code, cl.name, cl.strategy_type, "
            "cl.entry_low AS snapshot_entry_low, cl.entry_high AS snapshot_entry_high, "
            "cl.breakout_price AS snapshot_breakout_price, cl.stop_price AS snapshot_stop_price, "
            "cl.max_position_cash AS snapshot_max_position_cash, "
            "ip.entry_low AS intraday_entry_low, ip.entry_high AS intraday_entry_high, "
            "ip.breakout_price AS intraday_breakout_price, ip.stop_price AS intraday_stop_price, "
            "ip.max_position_cash AS intraday_max_position_cash, "
            "d.close AS signal_close, d.high AS signal_high, d.low AS signal_low, "
            "lp.up_limit AS signal_up_limit, mr.market_regime, "
            "nq.trade_date AS next_trade_date, nq.open AS next_open, nq.high AS next_high, "
            "nq.low AS next_low, nq.close AS next_close, nlp.up_limit AS next_up_limit "
            "FROM candidates_latest cl "
            "LEFT JOIN intraday_plans ip ON ip.trade_date = cl.trade_date "
            "AND ip.ts_code = cl.ts_code AND ip.strategy_type = cl.strategy_type "
            "LEFT JOIN daily_quotes d ON d.trade_date = cl.trade_date AND d.ts_code = cl.ts_code "
            "LEFT JOIN stk_limit_prices lp ON lp.trade_date = cl.trade_date AND lp.ts_code = cl.ts_code "
            "LEFT JOIN market_regimes mr ON mr.trade_date = cl.trade_date "
            "LEFT JOIN daily_quotes nq ON nq.ts_code = cl.ts_code AND nq.trade_date = ("
            "SELECT MIN(q.trade_date) FROM daily_quotes q WHERE q.ts_code = cl.ts_code "
            "AND q.trade_date > cl.trade_date) "
            "LEFT JOIN stk_limit_prices nlp ON nlp.trade_date = nq.trade_date AND nlp.ts_code = nq.ts_code "
            "WHERE cl.trade_date BETWEEN ? AND ? AND cl.strategy_type = ? "
            "ORDER BY cl.trade_date, cl.rank, cl.ts_code",
            (date_range.start_date, date_range.end_date, request.strategy_type.value),
        ).fetchall()
        created_at = _utc_now_text()
        trade_count = 0
        win_count = 0
        loss_count = 0
        total_cost = 0.0
        total_pnl = 0.0
        reason_counts: dict[str, int] = {}
        for candidate in candidates:
            plan = resolve_backtest_plan(candidate, request.strategy_type)
            decision = decide_backtest_order(candidate, plan)
            reason_counts[decision.reason_code] = reason_counts.get(decision.reason_code, 0) + 1
            conn.execute(
                "INSERT INTO backtest_orders ("
                "run_id, signal_date, trade_date, ts_code, strategy_type, side, planned_price, "
                "reason_code, source_run_id, created_at"
                ") VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (
                    run_id,
                    candidate["trade_date"],
                    candidate["next_trade_date"],
                    candidate["ts_code"],
                    request.strategy_type.value,
                    "BUY",
                    decision.planned_price,
                    decision.reason_code,
                    candidate["run_id"],
                    created_at,
                ),
            )
            if not decision.is_filled or plan is None:
                continue
            shares = _board_lot_shares(plan.max_position_cash, decision.fill_price)
            if shares == 0:
                continue
            pnl = (float(candidate["next_close"]) - decision.fill_price) * shares
            total_cost += decision.fill_price * shares
            total_pnl += pnl
            trade_count += 1
            win_count += 1 if pnl > 0 else 0
            loss_count += 1 if pnl < 0 else 0
            conn.execute(
                "INSERT INTO backtest_trades ("
                "run_id, signal_date, trade_date, ts_code, strategy_type, side, price, shares, "
                "cash_amount, pnl, reason_code, created_at"
                ") VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
                (
                    run_id,
                    candidate["trade_date"],
                    candidate["next_trade_date"],
                    candidate["ts_code"],
                    request.strategy_type.value,
                    "BUY",
                    decision.fill_price,
                    shares,
                    decision.fill_price * shares,
                    pnl,
                    decision.reason_code,
                    created_at,
                ),
            )
        total_return = 0.0 if total_cost == 0 else total_pnl / total_cost
        summary = BacktestSummary(
            run_id=run_id,
            date_range=date_range,
            strategy_type=request.strategy_type,
            config_version=request.config_version,
            report_dir=request.report_dir,
            candidate_count=len(candidates),
            order_count=len(candidates),
            trade_count=trade_count,
            win_count=win_count,
            loss_count=loss_count,
            total_return=total_return,
            reason_counts=tuple(sorted(reason_counts.items())),
        )
        _record_backtest_result(conn, summary, created_at)
    _write_walk_forward_summary(summary)
    return ResearchBacktestResult(
        summary.run_id,
        summary.date_range.start_date,
        summary.date_range.end_date,
        summary.candidate_count,
        summary.order_count,
        summary.trade_count,
        summary.total_return,
        summary.status,
        summary.report_path,
    )


def _resolve_end_date(conn: sqlite3.Connection, request: ResearchBacktestRequest) -> str:
    if request.end_date != "latest":
        return request.end_date
    row = conn.execute("SELECT MAX(trade_date) FROM candidate_snapshots").fetchone()
    return request.start_date if row is None or row[0] is None else str(row[0])


def _run_id(request: ResearchBacktestRequest, date_range: ResearchDateRange) -> str:
    text = f"{date_range.start_date}|{date_range.end_date}|{request.strategy_type.value}|{request.config_version}"
    digest = hashlib.sha256(text.encode()).hexdigest()
    return f"research-{digest[:16]}"


def _clear_backtest_run(conn: sqlite3.Connection, run_id: str) -> None:
    conn.execute("DELETE FROM backtest_orders WHERE run_id = ?", (run_id,))
    conn.execute("DELETE FROM backtest_trades WHERE run_id = ?", (run_id,))
    conn.execute("DELETE FROM backtest_results WHERE run_id = ?", (run_id,))




def _board_lot_shares(max_position_cash: float | None, entry_price: float) -> int:
    cash = 10000.0 if max_position_cash is None or max_position_cash <= 0 else float(max_position_cash)
    return int(cash // entry_price // 100 * 100)


def _record_backtest_result(conn: sqlite3.Connection, summary: BacktestSummary, created_at: str) -> None:
    summary_json = json.dumps(
        {
            "data_source": DATA_SOURCE,
            "run_id": summary.run_id,
            "total_return": summary.total_return,
            "reason_counts": list(summary.reason_counts),
        },
        sort_keys=True,
    )
    conn.execute(
        "INSERT INTO backtest_results ("
        "run_id, start_date, end_date, strategy_type, config_version, candidate_count, order_count, "
        "trade_count, win_count, loss_count, total_return, max_drawdown, status, summary_json, created_at"
        ") VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
        (
            summary.run_id,
            summary.date_range.start_date,
            summary.date_range.end_date,
            summary.strategy_type.value,
            summary.config_version,
            summary.candidate_count,
            summary.order_count,
            summary.trade_count,
            summary.win_count,
            summary.loss_count,
            summary.total_return,
            min(0.0, summary.total_return),
            summary.status,
            summary_json,
            created_at,
        ),
    )


def _write_walk_forward_summary(summary: BacktestSummary) -> None:
    summary.report_dir.mkdir(parents=True, exist_ok=True)
    lines = [
        "# Walk Forward Research Summary",
        "",
        f"- run_id: {summary.run_id}",
        f"- start_date: {summary.date_range.start_date}",
        f"- end_date: {summary.date_range.end_date}",
        f"- strategy_type: {summary.strategy_type.value}",
        f"- config_version: {summary.config_version}",
        f"- data_source: {DATA_SOURCE}",
        f"- candidate_count: {summary.candidate_count}",
        f"- order_count: {summary.order_count}",
        f"- trade_count: {summary.trade_count}",
        f"- total_return: {summary.total_return:.6f}",
        "- reason_counts: " + ", ".join(f"{reason}={count}" for reason, count in summary.reason_counts),
    ]
    summary.report_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _utc_now_text() -> str:
    return datetime.now(UTC).isoformat()
