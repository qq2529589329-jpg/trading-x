from dataclasses import dataclass
from pathlib import Path
import sqlite3

import pytest

from trading_x.db import init_db
from trading_x.tushare_adapter import (
    DailyBasicRow,
    DailyQuoteRow,
    LimitPriceRow,
    P0DataUnavailableError,
    StockBasicRow,
    update_p0_data,
)


@dataclass(frozen=True, slots=True)
class FakeP0Adapter:
    def stock_basic(self) -> list[StockBasicRow]:
        return [
            StockBasicRow(
                ts_code="000001.SZ",
                symbol="000001",
                name="平安银行",
                exchange="SZSE",
                market="主板",
                list_date="19910403",
            )
        ]

    def daily(self, trade_date: str) -> list[DailyQuoteRow]:
        return [
            DailyQuoteRow(
                trade_date=trade_date,
                ts_code="000001.SZ",
                open=10.0,
                high=10.5,
                low=9.9,
                close=10.2,
                pre_close=10.0,
                pct_chg=2.0,
                vol=1000.0,
                amount=10200.0,
            )
        ]

    def daily_basic(self, trade_date: str) -> list[DailyBasicRow]:
        return [
            DailyBasicRow(
                trade_date=trade_date,
                ts_code="000001.SZ",
                turnover_rate=1.2,
                volume_ratio=1.5,
                pe_ttm=8.0,
                pb=0.7,
                total_mv=100000.0,
                circ_mv=80000.0,
            )
        ]

    def stk_limit(self, trade_date: str) -> list[LimitPriceRow]:
        return [
            LimitPriceRow(
                trade_date=trade_date,
                ts_code="000001.SZ",
                pre_close=10.0,
                up_limit=11.0,
                down_limit=9.0,
            )
        ]


@dataclass(frozen=True, slots=True)
class MissingDailyP0Adapter(FakeP0Adapter):
    def daily(self, trade_date: str) -> list[DailyQuoteRow]:
        return []


@dataclass(frozen=True, slots=True)
class MissingDailyAndBasicP0Adapter(FakeP0Adapter):
    def daily(self, trade_date: str) -> list[DailyQuoteRow]:
        return []

    def daily_basic(self, trade_date: str) -> list[DailyBasicRow]:
        return []


def test_update_p0_data_is_idempotent_for_same_trade_date(tmp_path: Path) -> None:
    db_path = tmp_path / "trading_x.db"
    init_db(db_path)

    update_p0_data(db_path, "20260701", FakeP0Adapter())
    update_p0_data(db_path, "20260701", FakeP0Adapter())

    with sqlite3.connect(db_path) as conn:
        stock_count = conn.execute("SELECT COUNT(*) FROM stock_universe").fetchone()[0]
        daily_count = conn.execute("SELECT COUNT(*) FROM daily_quotes").fetchone()[0]
        basic_count = conn.execute("SELECT COUNT(*) FROM daily_basic").fetchone()[0]
        limit_count = conn.execute("SELECT COUNT(*) FROM stk_limit_prices").fetchone()[0]
        amount_row = conn.execute(
            "SELECT amount, regular_amount, post_close_amount, total_amount, "
            "post_close_amount_ratio, post_close_data_available FROM daily_quotes "
            "WHERE trade_date = ? AND ts_code = ?",
            ("20260701", "000001.SZ"),
        ).fetchone()

    assert stock_count == 1
    assert daily_count == 1
    assert basic_count == 1
    assert limit_count == 1
    assert amount_row == (10200.0, 10200.0, 0.0, 10200.0, 0.0, 0)


def test_update_p0_data_rejects_empty_p0_table(tmp_path: Path) -> None:
    db_path = tmp_path / "trading_x.db"
    init_db(db_path)

    with pytest.raises(P0DataUnavailableError) as exc_info:
        update_p0_data(db_path, "20260701", MissingDailyP0Adapter())

    assert exc_info.value.missing_tables == ("daily_quotes",)
    with sqlite3.connect(db_path) as conn:
        assert conn.execute("SELECT COUNT(*) FROM stock_universe").fetchone()[0] == 0
        assert conn.execute("SELECT COUNT(*) FROM stk_limit_prices").fetchone()[0] == 0


def test_update_p0_data_records_half_updated_status(tmp_path: Path) -> None:
    db_path = tmp_path / "trading_x.db"
    init_db(db_path)
    update_p0_data(db_path, "20260629", FakeP0Adapter())

    with pytest.raises(P0DataUnavailableError):
        update_p0_data(db_path, "20260630", MissingDailyAndBasicP0Adapter())

    with sqlite3.connect(db_path) as conn:
        status_rows = conn.execute(
            "SELECT api_name, status, row_count, expected_min_rows, coverage_ratio "
            "FROM data_status WHERE trade_date = ? ORDER BY api_name",
            ("20260630",),
        ).fetchall()
        summary = conn.execute(
            "SELECT p0_complete, data_capability, latest_complete_date, partial_reason "
            "FROM data_completeness_summary WHERE trade_date = ?",
            ("20260630",),
        ).fetchone()

    assert status_rows == [
        ("daily", "EMPTY", 0, 1, 0.0),
        ("daily_basic", "EMPTY", 0, 1, 0.0),
        ("stk_limit", "READY", 1, 1, 1.0),
        ("stock_basic", "READY", 1, 1, 1.0),
    ]
    assert summary == (0, "P0_INCOMPLETE", "20260629", "HALF_UPDATED: daily,daily_basic missing")
