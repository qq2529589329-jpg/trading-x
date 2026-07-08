from pathlib import Path
import sqlite3

from trading_x.data_status import P0UpdateRows, record_p0_data_status
from trading_x.p0_storage import (
    upsert_daily_basic,
    upsert_daily_quotes,
    upsert_limit_prices,
    upsert_stock_universe,
)
from trading_x.tushare_models import (
    AdjFactorRow,
    DailyBasicRow,
    DailyQuoteRow,
    LimitPriceRow,
    P0DataAdapter,
    P0DataUnavailableError,
    StockBasicRow,
    TushareUnavailableError,
)
from trading_x.themes import refresh_theme_daily_strength


def update_p0_data(db_path: Path, trade_date: str, adapter: P0DataAdapter) -> None:
    stock_rows = adapter.stock_basic()
    daily_rows = adapter.daily(trade_date)
    basic_rows = adapter.daily_basic(trade_date)
    limit_rows = adapter.stk_limit(trade_date)
    status = record_p0_data_status(
        db_path,
        trade_date,
        P0UpdateRows(
            stock_basic=stock_rows,
            daily=daily_rows,
            daily_basic=basic_rows,
            stk_limit=limit_rows,
        ),
    )
    if not status.p0_complete:
        raise P0DataUnavailableError(trade_date, status.missing_tables)
    with sqlite3.connect(db_path) as conn:
        upsert_stock_universe(conn, stock_rows)
        upsert_daily_quotes(conn, daily_rows)
        upsert_daily_basic(conn, basic_rows)
        upsert_limit_prices(conn, limit_rows)
    refresh_theme_daily_strength(db_path, trade_date)


class TushareP0Adapter:
    def __init__(self, token: str) -> None:
        try:
            import tushare as ts
        except ImportError as exc:
            raise TushareUnavailableError("tushare is not installed") from exc
        self._pro = ts.pro_api(token)

    def stock_basic(self) -> list[StockBasicRow]:
        frame = self._pro.stock_basic(
            exchange="",
            list_status="L",
            fields="ts_code,symbol,name,exchange,market,list_date",
        )
        return [
            StockBasicRow(
                ts_code=_text(row.get("ts_code")),
                symbol=_text(row.get("symbol")),
                name=_text(row.get("name")),
                exchange=_text(row.get("exchange")),
                market=_text(row.get("market")),
                list_date=_text(row.get("list_date")),
            )
            for row in frame.to_dict("records")
        ]

    def daily(self, trade_date: str) -> list[DailyQuoteRow]:
        frame = self._pro.daily(trade_date=trade_date)
        return [
            DailyQuoteRow(
                trade_date=trade_date,
                ts_code=_text(row.get("ts_code")),
                open=_number(row.get("open")),
                high=_number(row.get("high")),
                low=_number(row.get("low")),
                close=_number(row.get("close")),
                pre_close=_number(row.get("pre_close")),
                pct_chg=_number(row.get("pct_chg")),
                vol=_number(row.get("vol")),
                amount=_number(row.get("amount")),
            )
            for row in frame.to_dict("records")
        ]

    def daily_basic(self, trade_date: str) -> list[DailyBasicRow]:
        frame = self._pro.daily_basic(trade_date=trade_date)
        return [
            DailyBasicRow(
                trade_date=trade_date,
                ts_code=_text(row.get("ts_code")),
                turnover_rate=_number(row.get("turnover_rate")),
                volume_ratio=_number(row.get("volume_ratio")),
                pe_ttm=_number(row.get("pe_ttm")),
                pb=_number(row.get("pb")),
                total_mv=_number(row.get("total_mv")),
                circ_mv=_number(row.get("circ_mv")),
            )
            for row in frame.to_dict("records")
        ]

    def stk_limit(self, trade_date: str) -> list[LimitPriceRow]:
        frame = self._pro.stk_limit(trade_date=trade_date)
        return [
            LimitPriceRow(
                trade_date=trade_date,
                ts_code=_text(row.get("ts_code")),
                pre_close=_number(row.get("pre_close")),
                up_limit=_number(row.get("up_limit")),
                down_limit=_number(row.get("down_limit")),
            )
            for row in frame.to_dict("records")
        ]

    def adj_factor(self, trade_date: str) -> list[AdjFactorRow]:
        frame = self._pro.adj_factor(trade_date=trade_date)
        return [
            AdjFactorRow(
                trade_date=trade_date,
                ts_code=_text(row.get("ts_code")),
                adj_factor=_number(row.get("adj_factor")),
            )
            for row in frame.to_dict("records")
        ]

def _text(value) -> str:
    if value is None:
        return ""
    return str(value)


def _number(value) -> float:
    if value is None:
        return 0.0
    return float(value)
