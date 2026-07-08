from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
import sqlite3

from trading_x.p0_storage import upsert_adj_factors
from trading_x.research_backtest_audit import BacktestAuditUnavailableError
from trading_x.research_models import AdjFactorSyncRequest, AdjFactorSyncResult
from trading_x.tushare_models import AdjFactorAdapter, AdjFactorRow


@dataclass(frozen=True, slots=True)
class _AdjFactorKey:
    trade_date: str
    ts_code: str


def sync_backtest_adj_factors(
    db_path: Path,
    request: AdjFactorSyncRequest,
    adapter: AdjFactorAdapter,
) -> AdjFactorSyncResult:
    with sqlite3.connect(db_path) as conn:
        run_id = request.run_id if request.run_id is not None else _latest_run_id(conn)
        missing = _missing_adj_factor_keys(conn, run_id)
    created_at = datetime.now(UTC).isoformat()
    rows = _fetch_needed_rows(adapter, missing, created_at)
    if rows:
        with sqlite3.connect(db_path) as conn:
            upsert_adj_factors(conn, rows)
    with sqlite3.connect(db_path) as conn:
        missing_after = len(_missing_adj_factor_keys(conn, run_id))
    return AdjFactorSyncResult(run_id, len(missing), len(rows), missing_after)


def _latest_run_id(conn: sqlite3.Connection) -> str:
    row = conn.execute("SELECT run_id FROM backtest_results ORDER BY created_at DESC LIMIT 1").fetchone()
    if row is None:
        raise BacktestAuditUnavailableError("no backtest_results run found")
    return str(row[0])


def _missing_adj_factor_keys(conn: sqlite3.Connection, run_id: str) -> tuple[_AdjFactorKey, ...]:
    rows = conn.execute(
        "SELECT DISTINCT d.trade_date, d.ts_code FROM ("
        "SELECT signal_date AS trade_date, ts_code FROM backtest_trades WHERE run_id = ? "
        "UNION ALL SELECT trade_date, ts_code FROM backtest_trades WHERE run_id = ? "
        "UNION ALL SELECT exit_date, ts_code FROM backtest_trades WHERE run_id = ?"
        ") d LEFT JOIN adj_factors a ON a.trade_date = d.trade_date AND a.ts_code = d.ts_code "
        "WHERE d.trade_date IS NOT NULL AND a.ts_code IS NULL "
        "ORDER BY d.trade_date, d.ts_code",
        (run_id, run_id, run_id),
    ).fetchall()
    return tuple(_AdjFactorKey(str(row[0]), str(row[1])) for row in rows)


def _fetch_needed_rows(
    adapter: AdjFactorAdapter,
    missing: tuple[_AdjFactorKey, ...],
    created_at: str,
) -> list[AdjFactorRow]:
    symbols_by_date: dict[str, set[str]] = {}
    for key in missing:
        symbols_by_date.setdefault(key.trade_date, set()).add(key.ts_code)
    rows: list[AdjFactorRow] = []
    for trade_date, symbols in symbols_by_date.items():
        rows.extend(
            AdjFactorRow(row.trade_date, row.ts_code, row.adj_factor, row.source, created_at)
            for row in adapter.adj_factor(trade_date)
            if row.ts_code in symbols and row.adj_factor > 0
        )
    return rows
