from collections.abc import Sequence
from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
import sqlite3

from trading_x.tushare_models import DailyBasicRow, DailyQuoteRow, LimitPriceRow, StockBasicRow


@dataclass(frozen=True, slots=True)
class P0UpdateRows:
    stock_basic: Sequence[StockBasicRow]
    daily: Sequence[DailyQuoteRow]
    daily_basic: Sequence[DailyBasicRow]
    stk_limit: Sequence[LimitPriceRow]


@dataclass(frozen=True, slots=True)
class P0StatusResult:
    p0_complete: bool
    missing_tables: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class DataStatusRecord:
    api_name: str
    status: str
    row_count: int
    expected_min_rows: int
    coverage_ratio: float
    max_trade_date: str | None


def record_p0_data_status(db_path: Path, trade_date: str, rows: P0UpdateRows) -> P0StatusResult:
    records = _records(trade_date, rows)
    missing_tables = _missing_tables(records)
    p0_complete = not missing_tables
    now = datetime.now(UTC).isoformat()
    partial_reason = None if p0_complete else _partial_reason(records)
    with sqlite3.connect(db_path) as conn:
        conn.executemany(
            "INSERT OR REPLACE INTO data_status ("
            "trade_date, api_name, status, row_count, expected_min_rows, coverage_ratio, "
            "max_trade_date, checked_at, error_message, source"
            ") VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            [
                (
                    trade_date,
                    record.api_name,
                    record.status,
                    record.row_count,
                    record.expected_min_rows,
                    record.coverage_ratio,
                    record.max_trade_date,
                    now,
                    None,
                    "tushare",
                )
                for record in records
            ],
        )
        conn.execute(
            "INSERT OR REPLACE INTO data_completeness_summary ("
            "trade_date, p0_complete, p1_complete, data_capability, latest_complete_date, "
            "partial_reason, checked_at"
            ") VALUES (?, ?, ?, ?, ?, ?, ?)",
            (
                trade_date,
                int(p0_complete),
                0,
                "FULL" if p0_complete else "P0_INCOMPLETE",
                latest_complete_trade_date(db_path, trade_date),
                partial_reason,
                now,
            ),
        )
    return P0StatusResult(p0_complete=p0_complete, missing_tables=missing_tables)


def latest_complete_trade_date(db_path: Path, before_date: str) -> str | None:
    with sqlite3.connect(db_path) as conn:
        row = conn.execute(
            "SELECT trade_date FROM ("
            "SELECT trade_date FROM daily_quotes WHERE trade_date < ? "
            "INTERSECT SELECT trade_date FROM daily_basic WHERE trade_date < ? "
            "INTERSECT SELECT trade_date FROM stk_limit_prices WHERE trade_date < ?"
            ") ORDER BY trade_date DESC LIMIT 1",
            (before_date, before_date, before_date),
        ).fetchone()
    if row is None:
        return None
    return str(row[0])


def p0_incomplete_reason(db_path: Path, trade_date: str) -> str | None:
    with sqlite3.connect(db_path) as conn:
        row = conn.execute(
            "SELECT p0_complete, partial_reason FROM data_completeness_summary "
            "WHERE trade_date = ?",
            (trade_date,),
        ).fetchone()
        if row is not None:
            if row[0] == 0:
                return str(row[1])
            return None
        missing = _missing_p0_apis(conn, trade_date)
    if missing:
        return "P0_INCOMPLETE: " + ",".join(missing) + " missing"
    return None


def _records(trade_date: str, rows: P0UpdateRows) -> tuple[DataStatusRecord, ...]:
    expected_rows = max(1, len(rows.stock_basic) // 2)
    return (
        _stock_record(len(rows.stock_basic)),
        _dated_record("daily", trade_date, rows.daily, expected_rows),
        _dated_record("daily_basic", trade_date, rows.daily_basic, expected_rows),
        _dated_record("stk_limit", trade_date, rows.stk_limit, expected_rows),
    )


def _stock_record(row_count: int) -> DataStatusRecord:
    expected_rows = 1
    return DataStatusRecord(
        api_name="stock_basic",
        status=_row_status(row_count, expected_rows),
        row_count=row_count,
        expected_min_rows=expected_rows,
        coverage_ratio=_coverage_ratio(row_count, expected_rows),
        max_trade_date=None,
    )


def _dated_record(
    api_name: str,
    trade_date: str,
    rows: Sequence[DailyQuoteRow] | Sequence[DailyBasicRow] | Sequence[LimitPriceRow],
    expected_rows: int,
) -> DataStatusRecord:
    row_count = len(rows)
    max_trade_date = max((row.trade_date for row in rows), default=None)
    status = _row_status(row_count, expected_rows)
    if max_trade_date is not None and max_trade_date != trade_date:
        status = "STALE"
    return DataStatusRecord(
        api_name=api_name,
        status=status,
        row_count=row_count,
        expected_min_rows=expected_rows,
        coverage_ratio=_coverage_ratio(row_count, expected_rows),
        max_trade_date=max_trade_date,
    )


def _row_status(row_count: int, expected_rows: int) -> str:
    if row_count == 0:
        return "EMPTY"
    if row_count < expected_rows:
        return "PARTIAL"
    return "READY"


def _coverage_ratio(row_count: int, expected_rows: int) -> float:
    return round(min(row_count / expected_rows, 1.0), 4)


def _missing_tables(records: tuple[DataStatusRecord, ...]) -> tuple[str, ...]:
    table_by_api = {
        "stock_basic": "stock_universe",
        "daily": "daily_quotes",
        "daily_basic": "daily_basic",
        "stk_limit": "stk_limit_prices",
    }
    return tuple(table_by_api[record.api_name] for record in records if record.status != "READY")


def _missing_p0_apis(conn: sqlite3.Connection, trade_date: str) -> tuple[str, ...]:
    missing: list[str] = []
    if _table_count(conn, "stock_universe") == 0:
        missing.append("stock_basic")
    if _date_count(conn, "daily_quotes", trade_date) == 0:
        missing.append("daily")
    if _date_count(conn, "daily_basic", trade_date) == 0:
        missing.append("daily_basic")
    if _date_count(conn, "stk_limit_prices", trade_date) == 0:
        missing.append("stk_limit")
    return tuple(missing)


def _table_count(conn: sqlite3.Connection, table: str) -> int:
    return int(conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0])


def _date_count(conn: sqlite3.Connection, table: str, trade_date: str) -> int:
    return int(
        conn.execute(
            f"SELECT COUNT(*) FROM {table} WHERE trade_date = ?",
            (trade_date,),
        ).fetchone()[0]
    )


def _partial_reason(records: tuple[DataStatusRecord, ...]) -> str:
    problem_records = [record for record in records if record.status != "READY"]
    statuses = {record.api_name: record.status for record in records}
    half_updated = [
        record.api_name
        for record in problem_records
        if record.api_name in {"daily", "daily_basic"} and record.status == "EMPTY"
    ]
    if statuses.get("stk_limit") == "READY" and half_updated:
        return f"HALF_UPDATED: {','.join(half_updated)} missing"
    return "P0_INCOMPLETE: " + ",".join(_reason_item(record) for record in problem_records)


def _reason_item(record: DataStatusRecord) -> str:
    if record.status == "EMPTY":
        return f"{record.api_name} missing"
    return f"{record.api_name} {record.status.lower()}"
