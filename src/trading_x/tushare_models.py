from dataclasses import dataclass
from typing import Protocol


@dataclass(frozen=True, slots=True)
class TushareUnavailableError(Exception):
    reason: str

    def __str__(self) -> str:
        return self.reason


@dataclass(frozen=True, slots=True)
class P0DataUnavailableError(Exception):
    trade_date: str
    missing_tables: tuple[str, ...]

    def __str__(self) -> str:
        return f"P0 数据缺失：{self.trade_date} {', '.join(self.missing_tables)}"


@dataclass(frozen=True, slots=True)
class StockBasicRow:
    ts_code: str
    symbol: str
    name: str
    exchange: str
    market: str
    list_date: str


@dataclass(frozen=True, slots=True)
class DailyQuoteRow:
    trade_date: str
    ts_code: str
    open: float
    high: float
    low: float
    close: float
    pre_close: float
    pct_chg: float
    vol: float
    amount: float
    regular_amount: float | None = None
    post_close_amount: float | None = None
    total_amount: float | None = None
    post_close_amount_ratio: float | None = None
    post_close_data_available: bool = False


@dataclass(frozen=True, slots=True)
class DailyBasicRow:
    trade_date: str
    ts_code: str
    turnover_rate: float
    volume_ratio: float
    pe_ttm: float
    pb: float
    total_mv: float
    circ_mv: float


@dataclass(frozen=True, slots=True)
class LimitPriceRow:
    trade_date: str
    ts_code: str
    pre_close: float
    up_limit: float
    down_limit: float


class P0DataAdapter(Protocol):
    def stock_basic(self) -> list[StockBasicRow]: ...

    def daily(self, trade_date: str) -> list[DailyQuoteRow]: ...

    def daily_basic(self, trade_date: str) -> list[DailyBasicRow]: ...

    def stk_limit(self, trade_date: str) -> list[LimitPriceRow]: ...
