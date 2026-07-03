from dataclasses import dataclass
from pathlib import Path

from trading_x.capabilities import API_DEFINITIONS, ApiCheckResult, persist_capabilities
from trading_x.db import init_db
from trading_x.reports import generate_report
from trading_x.tushare_adapter import (
    DailyBasicRow,
    DailyQuoteRow,
    LimitPriceRow,
    StockBasicRow,
    update_p0_data,
)


@dataclass(frozen=True, slots=True)
class TenDayP0Adapter:
    def stock_basic(self) -> list[StockBasicRow]:
        return [
            StockBasicRow(
                ts_code="000001.SZ",
                symbol="000001",
                name="弱势样本",
                exchange="SZSE",
                market="主板",
                list_date="20200101",
            )
        ]

    def daily(self, trade_date: str) -> list[DailyQuoteRow]:
        return [
            DailyQuoteRow(
                trade_date=trade_date,
                ts_code="000001.SZ",
                open=10.0,
                high=10.2,
                low=9.9,
                close=10.1,
                pre_close=10.0,
                pct_chg=1.0,
                vol=50000.0,
                amount=120000.0,
            )
        ]

    def daily_basic(self, trade_date: str) -> list[DailyBasicRow]:
        return [
            DailyBasicRow(
                trade_date=trade_date,
                ts_code="000001.SZ",
                turnover_rate=1.0,
                volume_ratio=1.1,
                pe_ttm=10.0,
                pb=1.0,
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


def generated_ten_day_reports(db_path: Path, report_dir: Path) -> list[str]:
    dates = [f"202607{day:02d}" for day in range(1, 11)]
    init_db(db_path)
    persist_basic_capabilities(db_path)
    for trade_date in dates:
        update_p0_data(db_path, trade_date, TenDayP0Adapter())
        generate_report(db_path, trade_date, report_dir)
    return dates


def persist_basic_capabilities(db_path: Path) -> None:
    unavailable = {"top_list", "limit_cpt_list", "moneyflow", "margin"}
    persist_capabilities(
        db_path,
        [
            ApiCheckResult(api_name=definition.name, available=definition.name not in unavailable)
            for definition in API_DEFINITIONS
        ],
    )
