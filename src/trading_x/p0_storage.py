import sqlite3

from trading_x.tushare_models import (
    DailyBasicRow,
    DailyQuoteRow,
    LimitPriceRow,
    StockBasicRow,
)


def upsert_stock_universe(conn: sqlite3.Connection, rows: list[StockBasicRow]) -> None:
    conn.executemany(
        "INSERT INTO stock_universe ("
        "ts_code, symbol, name, exchange, market, list_date, "
        "is_st, is_delisting_risk, included, excluded_reason"
        ") VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?) "
        "ON CONFLICT(ts_code) DO UPDATE SET "
        "symbol = excluded.symbol, name = excluded.name, exchange = excluded.exchange, "
        "market = excluded.market, list_date = excluded.list_date, "
        "is_st = excluded.is_st, is_delisting_risk = excluded.is_delisting_risk, "
        "included = excluded.included, excluded_reason = excluded.excluded_reason",
        [
            (
                row.ts_code,
                row.symbol,
                row.name,
                row.exchange,
                row.market,
                row.list_date,
                int(_is_st(row.name)),
                0,
                int(_is_included(row)),
                None if _is_included(row) else "unsupported_board_or_st",
            )
            for row in rows
        ],
    )


def upsert_daily_quotes(conn: sqlite3.Connection, rows: list[DailyQuoteRow]) -> None:
    conn.executemany(
        "INSERT INTO daily_quotes ("
        "trade_date, ts_code, open, high, low, close, pre_close, pct_chg, vol, amount"
        ") VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?) "
        "ON CONFLICT(trade_date, ts_code) DO UPDATE SET "
        "open = excluded.open, high = excluded.high, low = excluded.low, "
        "close = excluded.close, pre_close = excluded.pre_close, "
        "pct_chg = excluded.pct_chg, vol = excluded.vol, amount = excluded.amount",
        [
            (
                row.trade_date,
                row.ts_code,
                row.open,
                row.high,
                row.low,
                row.close,
                row.pre_close,
                row.pct_chg,
                row.vol,
                row.amount,
            )
            for row in rows
        ],
    )


def upsert_daily_basic(conn: sqlite3.Connection, rows: list[DailyBasicRow]) -> None:
    conn.executemany(
        "INSERT INTO daily_basic ("
        "trade_date, ts_code, turnover_rate, volume_ratio, pe_ttm, pb, total_mv, circ_mv"
        ") VALUES (?, ?, ?, ?, ?, ?, ?, ?) "
        "ON CONFLICT(trade_date, ts_code) DO UPDATE SET "
        "turnover_rate = excluded.turnover_rate, volume_ratio = excluded.volume_ratio, "
        "pe_ttm = excluded.pe_ttm, pb = excluded.pb, "
        "total_mv = excluded.total_mv, circ_mv = excluded.circ_mv",
        [
            (
                row.trade_date,
                row.ts_code,
                row.turnover_rate,
                row.volume_ratio,
                row.pe_ttm,
                row.pb,
                row.total_mv,
                row.circ_mv,
            )
            for row in rows
        ],
    )


def upsert_limit_prices(conn: sqlite3.Connection, rows: list[LimitPriceRow]) -> None:
    conn.executemany(
        "INSERT INTO stk_limit_prices (trade_date, ts_code, pre_close, up_limit, down_limit) "
        "VALUES (?, ?, ?, ?, ?) "
        "ON CONFLICT(trade_date, ts_code) DO UPDATE SET "
        "pre_close = excluded.pre_close, "
        "up_limit = excluded.up_limit, down_limit = excluded.down_limit",
        [
            (row.trade_date, row.ts_code, row.pre_close, row.up_limit, row.down_limit)
            for row in rows
        ],
    )


def _is_st(name: str) -> bool:
    return "ST" in name.upper()


def _is_included(row: StockBasicRow) -> bool:
    return row.market in {"主板", "创业板"} and not _is_st(row.name)
