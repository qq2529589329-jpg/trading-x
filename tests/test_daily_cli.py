from dataclasses import dataclass
from pathlib import Path
import sqlite3
import sys

from trading_x import cli
from trading_x.capabilities import ApiCheckResult, DoctorSummary
from trading_x.market import MarketEmotion
from trading_x.reports import ReportSnapshot
from trading_x.trading_rules import new_rule_compatibility_for
from trading_x.theme_models import ThemeCoverage
from trading_x.tushare_adapter import (
    DailyBasicRow,
    DailyQuoteRow,
    LimitPriceRow,
    StockBasicRow,
    TushareUnavailableError,
)
from trading_x.types import Confidence, DataCapabilityLevel


@dataclass(frozen=True, slots=True)
class FakeCapabilityAdapter:
    def check_api(self, api_name: str) -> ApiCheckResult:
        return ApiCheckResult(api_name=api_name, available=True)


@dataclass(frozen=True, slots=True)
class FakeP0Adapter:
    def stock_basic(self) -> list[StockBasicRow]:
        return [
            StockBasicRow("000001.SZ", "000001", "平安银行", "SZSE", "主板", "19910403")
        ]

    def daily(self, trade_date: str) -> list[DailyQuoteRow]:
        return [
            DailyQuoteRow(trade_date, "000001.SZ", 10.0, 10.1, 9.9, 10.0, 10.0, 0.0, 1000.0, 1000.0)
        ]

    def daily_basic(self, trade_date: str) -> list[DailyBasicRow]:
        return [
            DailyBasicRow(trade_date, "000001.SZ", 1.0, 1.0, 8.0, 0.8, 100000.0, 80000.0)
        ]

    def stk_limit(self, trade_date: str) -> list[LimitPriceRow]:
        return [LimitPriceRow(trade_date, "000001.SZ", 10.0, 11.0, 9.0)]


def test_daily_calls_doctor_update_report_in_order(
    tmp_path: Path,
    monkeypatch,
    capsys,
) -> None:
    db_path = tmp_path / "trading_x.db"
    report_dir = tmp_path / "reports"
    calls: list[str] = []

    monkeypatch.setenv("TUSHARE_TOKEN", "secret-token")
    monkeypatch.setattr(cli, "DEFAULT_REPORT_DIR", report_dir)
    monkeypatch.setattr(sys, "argv", ["trading_x", "--db", str(db_path), "daily", "--date", "20260701"])
    monkeypatch.setattr(cli, "TushareCapabilityAdapter", lambda token: "doctor-adapter")
    monkeypatch.setattr(cli, "TushareP0Adapter", lambda token: "p0-adapter")
    monkeypatch.setattr(
        cli,
        "run_doctor",
        lambda db, adapter, token: calls.append("doctor") or _summary(DataCapabilityLevel.FULL),
    )
    monkeypatch.setattr(
        cli,
        "update_p0_data",
        lambda db, trade_date, adapter: calls.append("update"),
    )
    monkeypatch.setattr(
        cli,
        "generate_report",
        lambda db, trade_date, path: calls.append("report") or _snapshot(trade_date),
    )
    monkeypatch.setattr(
        cli,
        "theme_coverage",
        lambda db, trade_date: calls.append("coverage")
        or ThemeCoverage(
            stock_total=2,
            mapped_stock_count=1,
            candidate_total=1,
            candidate_mapped_count=1,
            unmapped_candidates=(),
        ),
    )

    assert cli.main() == 0

    assert calls == ["doctor", "update", "report", "coverage"]
    output = capsys.readouterr().out
    assert "题材覆盖率：1/2 (50.0%)" in output
    assert "候选题材覆盖率：1/1 (100.0%)" in output
    assert "报告 Markdown：" in output
    assert "报告 JSON：" in output
    assert "acceptance --last-complete-n 10" in output
    assert "secret-token" not in output


def test_daily_stops_when_doctor_is_degraded(
    tmp_path: Path,
    monkeypatch,
    capsys,
) -> None:
    db_path = tmp_path / "trading_x.db"

    monkeypatch.setenv("TUSHARE_TOKEN", "secret-token")
    monkeypatch.setattr(sys, "argv", ["trading_x", "--db", str(db_path), "daily", "--date", "20260701"])
    monkeypatch.setattr(cli, "TushareCapabilityAdapter", lambda token: FakeCapabilityAdapter())
    monkeypatch.setattr(cli, "run_doctor", lambda db, adapter, token: _summary(DataCapabilityLevel.DEGRADED))
    monkeypatch.setattr(cli, "update_p0_data", _fail_if_called)
    monkeypatch.setattr(cli, "generate_report", _fail_if_called)

    assert cli.main() == 1

    output = capsys.readouterr().out
    assert "数据能力：DEGRADED" in output
    assert "secret-token" not in output


def test_daily_stops_when_update_fails(
    tmp_path: Path,
    monkeypatch,
    capsys,
) -> None:
    db_path = tmp_path / "trading_x.db"

    monkeypatch.setenv("TUSHARE_TOKEN", "secret-token")
    monkeypatch.setattr(sys, "argv", ["trading_x", "--db", str(db_path), "daily", "--date", "20260701"])
    monkeypatch.setattr(cli, "TushareCapabilityAdapter", lambda token: FakeCapabilityAdapter())
    monkeypatch.setattr(cli, "TushareP0Adapter", lambda token: FakeP0Adapter())
    monkeypatch.setattr(cli, "run_doctor", lambda db, adapter, token: _summary(DataCapabilityLevel.FULL))
    monkeypatch.setattr(
        cli,
        "update_p0_data",
        lambda db, trade_date, adapter: _raise_tushare_error(),
    )
    monkeypatch.setattr(cli, "generate_report", _fail_if_called)

    assert cli.main() == 1

    output = capsys.readouterr().out
    assert "update failed" in output
    assert "secret-token" not in output


def test_daily_missing_token_fails_without_leaking_secret(
    tmp_path: Path,
    monkeypatch,
    capsys,
) -> None:
    db_path = tmp_path / "trading_x.db"

    monkeypatch.delenv("TUSHARE_TOKEN", raising=False)
    monkeypatch.setattr(cli, "load_tushare_token", lambda env_value=None: None)
    monkeypatch.setattr(sys, "argv", ["trading_x", "--db", str(db_path), "daily", "--date", "20260701"])
    monkeypatch.setattr(cli, "update_p0_data", _fail_if_called)
    monkeypatch.setattr(cli, "generate_report", _fail_if_called)

    assert cli.main() == 1

    output = capsys.readouterr().out
    assert "TUSHARE_TOKEN is required" in output
    assert "secret-token" not in output


def test_daily_no_candidates_success_and_idempotent(
    tmp_path: Path,
    monkeypatch,
    capsys,
) -> None:
    db_path = tmp_path / "trading_x.db"
    report_dir = tmp_path / "reports"

    monkeypatch.setenv("TUSHARE_TOKEN", "secret-token")
    monkeypatch.setattr(cli, "DEFAULT_REPORT_DIR", report_dir)
    monkeypatch.setattr(cli, "TushareCapabilityAdapter", lambda token: FakeCapabilityAdapter())
    monkeypatch.setattr(cli, "TushareP0Adapter", lambda token: FakeP0Adapter())

    for _ in range(2):
        monkeypatch.setattr(sys, "argv", ["trading_x", "--db", str(db_path), "daily", "--date", "20260701"])
        assert cli.main() == 0

    output = capsys.readouterr().out
    assert "候选数量：0" in output
    assert "今日无符合纪律候选" in output

    with sqlite3.connect(db_path) as conn:
        stock_count = conn.execute("SELECT COUNT(*) FROM stock_universe").fetchone()[0]
        daily_count = conn.execute("SELECT COUNT(*) FROM daily_quotes").fetchone()[0]
        basic_count = conn.execute("SELECT COUNT(*) FROM daily_basic").fetchone()[0]
        limit_count = conn.execute("SELECT COUNT(*) FROM stk_limit_prices").fetchone()[0]
        report_count = conn.execute("SELECT COUNT(*) FROM reports").fetchone()[0]

    assert stock_count == 1
    assert daily_count == 1
    assert basic_count == 1
    assert limit_count == 1
    assert report_count == 1


def _summary(level: DataCapabilityLevel) -> DoctorSummary:
    return DoctorSummary(level, ("daily",), (), ("secret-token must stay hidden",))


def _snapshot(trade_date: str) -> ReportSnapshot:
    return ReportSnapshot(
        trade_date=trade_date,
        system_version="v1.0",
        market_status="退潮",
        allow_new_position=False,
        data_capability=DataCapabilityLevel.BASIC_WITH_THEME_FALLBACK,
        available_apis=("daily",),
        unavailable_apis=(),
        risk_blocks=("MarketEmotionScore 低于阈值，禁止新开仓",),
        candidates=[],
        theme_confidence=Confidence.LOW,
        market_emotion=MarketEmotion(
            core_market_emotion_score=0.0,
            normal_limit_up_count=0,
            normal_limit_down_count=0,
            normal_break_limit_rate=0.0,
            normal_highest_board=None,
            normal_limit_premium=None,
            st_speculation_score=0.0,
            st_limit_up_count=0,
            st_limit_down_count=0,
            st_highest_board=None,
        ),
        new_rule_compatibility=new_rule_compatibility_for(trade_date),
    )


def _raise_tushare_error() -> None:
    raise TushareUnavailableError("update failed")


def _fail_if_called(*args) -> None:
    raise AssertionError("should not be called")
