from dataclasses import dataclass
from pathlib import Path
import sys

from trading_x import cli
from trading_x.capabilities import ApiCheckResult, DoctorSummary
from trading_x.db import init_db
from trading_x.reports import ReportSnapshot
from trading_x.tushare_adapter import (
    DailyBasicRow,
    DailyQuoteRow,
    LimitPriceRow,
    StockBasicRow,
    update_p0_data as store_p0_data,
)
from trading_x.types import DataCapabilityLevel


@dataclass(frozen=True, slots=True)
class FakeCapabilityAdapter:
    def check_api(self, api_name: str) -> ApiCheckResult:
        return ApiCheckResult(api_name=api_name, available=True)


@dataclass(frozen=True, slots=True)
class FakeP0Adapter:
    def stock_basic(self) -> list[StockBasicRow]:
        return [StockBasicRow("000001.SZ", "000001", "平安银行", "SZSE", "主板", "19910403")]

    def daily(self, trade_date: str) -> list[DailyQuoteRow]:
        return [
            DailyQuoteRow(
                trade_date,
                "000001.SZ",
                10.0,
                10.1,
                9.9,
                10.0,
                10.0,
                0.0,
                1000.0,
                1000.0,
            )
        ]

    def daily_basic(self, trade_date: str) -> list[DailyBasicRow]:
        return [DailyBasicRow(trade_date, "000001.SZ", 1.0, 1.0, 8.0, 0.8, 100000.0, 80000.0)]

    def stk_limit(self, trade_date: str) -> list[LimitPriceRow]:
        return [LimitPriceRow(trade_date, "000001.SZ", 10.0, 11.0, 9.0)]


@dataclass(frozen=True, slots=True)
class MissingDailyAndBasicP0Adapter(FakeP0Adapter):
    def daily(self, trade_date: str) -> list[DailyQuoteRow]:
        return []

    def daily_basic(self, trade_date: str) -> list[DailyBasicRow]:
        return []


def test_daily_p0_failure_suggests_latest_complete_date(
    tmp_path: Path,
    monkeypatch,
    capsys,
) -> None:
    db_path = tmp_path / "trading_x.db"
    init_db(db_path)
    store_p0_data(db_path, "20260629", FakeP0Adapter())

    monkeypatch.setenv("TUSHARE_TOKEN", "secret-token")
    monkeypatch.setattr(sys, "argv", ["trading_x", "--db", str(db_path), "daily", "--date", "20260630"])
    monkeypatch.setattr(cli, "TushareCapabilityAdapter", lambda token: FakeCapabilityAdapter())
    monkeypatch.setattr(cli, "TushareP0Adapter", lambda token: MissingDailyAndBasicP0Adapter())
    monkeypatch.setattr(cli, "run_doctor", lambda db, adapter, token: _summary(DataCapabilityLevel.FULL))
    monkeypatch.setattr(cli, "generate_report", _fail_if_called)

    assert cli.main() == 1

    output = capsys.readouterr().out
    assert "HALF_UPDATED: daily,daily_basic missing" in output
    assert "最近完整交易日：20260629" in output
    assert "建议命令：uv run python -m trading_x daily --date 20260629" in output
    assert "secret-token" not in output


def _summary(level: DataCapabilityLevel) -> DoctorSummary:
    return DoctorSummary(level, ("daily",), (), ("secret-token must stay hidden",))


def _fail_if_called(db_path: Path, trade_date: str, report_dir: Path) -> ReportSnapshot:
    raise AssertionError("should not be called")
