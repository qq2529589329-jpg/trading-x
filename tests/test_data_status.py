from pathlib import Path
import sqlite3

from trading_x.data_status import P0UpdateRows, record_p0_data_status
from trading_x.db import init_db
from trading_x.tushare_models import DailyBasicRow, DailyQuoteRow, LimitPriceRow, StockBasicRow


def test_record_p0_data_status_marks_partial_rows(tmp_path: Path) -> None:
    db_path = tmp_path / "trading_x.db"
    init_db(db_path)

    result = record_p0_data_status(
        db_path,
        "20260630",
        P0UpdateRows(
            stock_basic=_stock_rows(4),
            daily=_daily_rows("20260630", 1),
            daily_basic=_basic_rows("20260630", 2),
            stk_limit=_limit_rows("20260630", 2),
        ),
    )

    with sqlite3.connect(db_path) as conn:
        status = conn.execute(
            "SELECT status, row_count, expected_min_rows, coverage_ratio "
            "FROM data_status WHERE trade_date = ? AND api_name = ?",
            ("20260630", "daily"),
        ).fetchone()
        summary = conn.execute(
            "SELECT p0_complete, data_capability, partial_reason "
            "FROM data_completeness_summary WHERE trade_date = ?",
            ("20260630",),
        ).fetchone()

    assert result.p0_complete is False
    assert status == ("PARTIAL", 1, 2, 0.5)
    assert summary == (0, "P0_INCOMPLETE", "P0_INCOMPLETE: daily partial")


def test_record_p0_data_status_marks_stale_rows(tmp_path: Path) -> None:
    db_path = tmp_path / "trading_x.db"
    init_db(db_path)

    result = record_p0_data_status(
        db_path,
        "20260630",
        P0UpdateRows(
            stock_basic=_stock_rows(2),
            daily=_daily_rows("20260629", 1),
            daily_basic=_basic_rows("20260630", 1),
            stk_limit=_limit_rows("20260630", 1),
        ),
    )

    with sqlite3.connect(db_path) as conn:
        status = conn.execute(
            "SELECT status, max_trade_date FROM data_status "
            "WHERE trade_date = ? AND api_name = ?",
            ("20260630", "daily"),
        ).fetchone()
        summary = conn.execute(
            "SELECT p0_complete, data_capability, partial_reason "
            "FROM data_completeness_summary WHERE trade_date = ?",
            ("20260630",),
        ).fetchone()

    assert result.p0_complete is False
    assert status == ("STALE", "20260629")
    assert summary == (0, "P0_INCOMPLETE", "P0_INCOMPLETE: daily stale")


def _stock_rows(count: int) -> list[StockBasicRow]:
    return [
        StockBasicRow(f"00000{index}.SZ", f"00000{index}", "样本", "SZSE", "主板", "20200101")
        for index in range(count)
    ]


def _daily_rows(trade_date: str, count: int) -> list[DailyQuoteRow]:
    return [
        DailyQuoteRow(trade_date, row.ts_code, 10.0, 10.1, 9.9, 10.0, 10.0, 0.0, 1000.0, 1000.0)
        for row in _stock_rows(count)
    ]


def _basic_rows(trade_date: str, count: int) -> list[DailyBasicRow]:
    return [
        DailyBasicRow(trade_date, row.ts_code, 1.0, 1.0, 8.0, 0.8, 100000.0, 80000.0)
        for row in _stock_rows(count)
    ]


def _limit_rows(trade_date: str, count: int) -> list[LimitPriceRow]:
    return [LimitPriceRow(trade_date, row.ts_code, 10.0, 11.0, 9.0) for row in _stock_rows(count)]
