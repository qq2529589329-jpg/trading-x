from dataclasses import dataclass, replace
from pathlib import Path
import sqlite3

from trading_x.candidate_models import CandidateReport
from trading_x.candidate_snapshots import CandidateRunRecord, persist_candidate_run
from trading_x.db import init_db
from trading_x.research import (
    AdjFactorSyncRequest,
    BacktestTrustAuditRequest,
    ResearchBacktestRequest,
    audit_research_backtest,
    run_research_backtest,
    sync_backtest_adj_factors,
)
from trading_x.tushare_models import AdjFactorRow
from trading_x.types import CandidateGrade, Confidence, DataCapabilityLevel, StrategyType


@dataclass(frozen=True, slots=True)
class QuoteFixture:
    trade_date: str
    ts_code: str
    open_price: float
    high: float
    low: float
    close: float
    pre_close: float
    amount: float


@dataclass(frozen=True, slots=True)
class FakeAdjFactorAdapter:
    def adj_factor(self, trade_date: str) -> list[AdjFactorRow]:
        return [
            AdjFactorRow(trade_date, "300004.SZ", 1.2),
            AdjFactorRow(trade_date, "999999.SZ", 1.0),
        ]


def test_research_backtest_uses_t1_exit_and_records_costs(tmp_path: Path) -> None:
    # Given
    db_path = tmp_path / "trading_x.db"
    init_db(db_path)
    _persist_candidate(db_path, "300001.SZ")
    _insert_quote(db_path, QuoteFixture("20260702", "300001.SZ", 10.2, 10.8, 10.0, 10.7, 10.0, 200000.0))
    _insert_quote(db_path, QuoteFixture("20260703", "300001.SZ", 11.0, 11.4, 10.9, 11.2, 10.7, 220000.0))

    # When
    run_research_backtest(
        db_path,
        ResearchBacktestRequest("20260701", "latest", StrategyType.B_CAPACITY_LEADER, "v1.0", tmp_path / "reports"),
    )

    # Then
    with sqlite3.connect(db_path) as conn:
        trade = conn.execute(
            "SELECT trade_date, exit_date, price, exit_price, shares, gross_pnl, cost_amount, pnl "
            "FROM backtest_trades"
        ).fetchone()
    assert trade[0:5] == ("20260702", "20260703", 10.5, 11.2, 1000)
    assert round(trade[5], 4) == 700.0
    assert trade[6] > 0
    assert round(trade[7], 4) == round(trade[5] - trade[6], 4)


def test_backtest_trust_audit_fails_when_adjustment_factors_are_missing(tmp_path: Path) -> None:
    # Given
    db_path = tmp_path / "trading_x.db"
    report_dir = tmp_path / "reports"
    init_db(db_path)
    _persist_candidate(db_path, "300002.SZ")
    _insert_quote(db_path, QuoteFixture("20260702", "300002.SZ", 10.2, 10.8, 10.0, 10.7, 10.0, 200000.0))
    _insert_quote(db_path, QuoteFixture("20260703", "300002.SZ", 11.0, 11.4, 10.9, 11.2, 10.7, 220000.0))
    result = run_research_backtest(
        db_path,
        ResearchBacktestRequest("20260701", "latest", StrategyType.B_CAPACITY_LEADER, "v1.0", report_dir),
    )

    # When
    audit = audit_research_backtest(db_path, BacktestTrustAuditRequest(result.run_id, report_dir))

    # Then
    assert audit.status == "FAIL"
    assert audit.issue_count == 3
    assert "ADJ_FACTOR_MISSING=3" in audit.report_path.read_text(encoding="utf-8")


def test_backtest_trust_audit_passes_for_t1_costed_adjusted_run(tmp_path: Path) -> None:
    # Given
    db_path = tmp_path / "trading_x.db"
    report_dir = tmp_path / "reports"
    init_db(db_path)
    _persist_candidate(db_path, "300003.SZ")
    _insert_quote(db_path, QuoteFixture("20260702", "300003.SZ", 10.2, 10.8, 10.0, 10.7, 10.0, 200000.0))
    _insert_quote(db_path, QuoteFixture("20260703", "300003.SZ", 11.0, 11.4, 10.9, 11.2, 10.7, 220000.0))
    _insert_adj_factors(db_path, "300003.SZ")
    result = run_research_backtest(
        db_path,
        ResearchBacktestRequest("20260701", "latest", StrategyType.B_CAPACITY_LEADER, "v1.0", report_dir),
    )

    # When
    audit = audit_research_backtest(db_path, BacktestTrustAuditRequest(result.run_id, report_dir))

    # Then
    assert audit.status == "PASS"
    assert audit.issue_count == 0
    assert "- status: PASS" in audit.report_path.read_text(encoding="utf-8")


def test_sync_backtest_adj_factors_fills_missing_audit_inputs(tmp_path: Path) -> None:
    # Given
    db_path = tmp_path / "trading_x.db"
    report_dir = tmp_path / "reports"
    init_db(db_path)
    _persist_candidate(db_path, "300004.SZ")
    _insert_quote(db_path, QuoteFixture("20260702", "300004.SZ", 10.2, 10.8, 10.0, 10.7, 10.0, 200000.0))
    _insert_quote(db_path, QuoteFixture("20260703", "300004.SZ", 11.0, 11.4, 10.9, 11.2, 10.7, 220000.0))
    result = run_research_backtest(
        db_path,
        ResearchBacktestRequest("20260701", "latest", StrategyType.B_CAPACITY_LEADER, "v1.0", report_dir),
    )

    # When
    sync = sync_backtest_adj_factors(db_path, AdjFactorSyncRequest(result.run_id), FakeAdjFactorAdapter())
    audit = audit_research_backtest(db_path, BacktestTrustAuditRequest(result.run_id, report_dir))

    # Then
    assert sync.missing_before == 3
    assert sync.inserted_count == 3
    assert sync.missing_after == 0
    assert audit.status == "PASS"


def _persist_candidate(db_path: Path, ts_code: str) -> None:
    persist_candidate_run(
        db_path,
        _run("run-1"),
        [
            replace(
                _candidate(ts_code),
                plan_entry_low=10.0,
                plan_entry_high=11.0,
                plan_breakout_price=10.5,
                plan_stop_price=9.5,
                plan_max_position_cash=10500.0,
            )
        ],
    )


def _insert_quote(db_path: Path, quote: QuoteFixture) -> None:
    with sqlite3.connect(db_path) as conn:
        conn.execute(
            "INSERT INTO daily_quotes (trade_date, ts_code, open, high, low, close, pre_close, pct_chg, vol, amount) "
            "VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (
                quote.trade_date,
                quote.ts_code,
                quote.open_price,
                quote.high,
                quote.low,
                quote.close,
                quote.pre_close,
                (quote.close - quote.pre_close) / quote.pre_close * 100,
                quote.amount / quote.close,
                quote.amount,
            ),
        )
        conn.execute(
            "INSERT INTO stk_limit_prices (trade_date, ts_code, pre_close, up_limit, down_limit) "
            "VALUES (?, ?, ?, ?, ?)",
            (quote.trade_date, quote.ts_code, quote.pre_close, quote.pre_close * 1.1, quote.pre_close * 0.9),
        )


def _insert_adj_factors(db_path: Path, ts_code: str) -> None:
    with sqlite3.connect(db_path) as conn:
        for trade_date in ("20260701", "20260702", "20260703"):
            conn.execute(
                "INSERT INTO adj_factors (trade_date, ts_code, adj_factor, source, created_at) VALUES (?, ?, ?, ?, ?)",
                (trade_date, ts_code, 1.0, "fixture", "2026-07-03T16:00:00+00:00"),
            )


def _run(run_id: str) -> CandidateRunRecord:
    return CandidateRunRecord(
        run_id=run_id,
        trade_date="20260701",
        system_version="v1.0",
        strategy_version="rules-v1",
        threshold_version="threshold-v1",
        config_hash="config-hash",
        data_capability=DataCapabilityLevel.BASIC_WITH_THEME_FALLBACK,
        p0_complete=True,
        theme_coverage_ratio=1.0,
        generated_at="2026-07-01T16:00:00+00:00",
        report_json_path=Path("reports/20260701_report.json"),
        report_md_path=Path("reports/20260701_report.md"),
        notes=None,
    )


def _candidate(ts_code: str) -> CandidateReport:
    return CandidateReport(
        ts_code=ts_code,
        name="容量龙",
        strategy_type=StrategyType.B_CAPACITY_LEADER,
        candidate_grade=CandidateGrade.B_CORE,
        theme_name="机器人",
        theme_tags="机器人;智能制造",
        theme_rank_today=1,
        theme_strength_score=88.0,
        theme_position="成交额第 1，涨幅第 2",
        entry_reason="所属机器人题材今日强度排名第 1。",
        veto_items="P0 风控通过。",
        buy_observation="明日只观察放量突破或回踩承接。",
        abandon_conditions="跌回平台内则放弃。",
        max_chase_limit="不追高超过计划买点 5%。",
        structural_stop="跌破当日低点 19.80。",
        suggested_position="观察仓 10%-20%。",
        max_loss="单笔最大亏损控制在总资金 1% 内。",
        data_confidence=Confidence.MEDIUM,
        theme_confidence=Confidence.MEDIUM,
        event_confidence=Confidence.UNAVAILABLE,
    )
