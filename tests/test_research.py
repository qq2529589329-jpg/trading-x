from dataclasses import dataclass, replace
from pathlib import Path
import sqlite3

from trading_x.candidate_models import CandidateReport
from trading_x.candidate_snapshots import CandidateRunRecord, persist_candidate_run
from trading_x.db import init_db
from trading_x.research import (
    RegimeClassificationRequest,
    ResearchBacktestRequest,
    classify_market_regimes,
    run_research_backtest,
)
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


def test_research_schema_is_created_by_init_db(tmp_path: Path) -> None:
    # Given
    db_path = tmp_path / "trading_x.db"

    # When
    init_db(db_path)

    # Then
    with sqlite3.connect(db_path) as conn:
        tables = {
            row[0]
            for row in conn.execute(
                "SELECT name FROM sqlite_master WHERE type = 'table' AND name LIKE 'backtest_%' "
                "OR name IN ('market_regimes', 'limit_events_daily_proxy', "
                "'stock_universe_history', 'adj_factors', 'agent_proposals', 'parameter_approvals')"
            )
        }
    assert tables == {
        "stock_universe_history",
        "adj_factors",
        "market_regimes",
        "limit_events_daily_proxy",
        "backtest_orders",
        "backtest_trades",
        "backtest_results",
        "agent_proposals",
        "parameter_approvals",
    }


def test_classify_market_regimes_writes_point_in_time_labels(tmp_path: Path) -> None:
    # Given
    db_path = tmp_path / "trading_x.db"
    init_db(db_path)
    _insert_quote(db_path, QuoteFixture("20260701", "300001.SZ", 10.0, 11.0, 11.0, 11.0, 10.0, 100000.0))
    _insert_quote(db_path, QuoteFixture("20260701", "300002.SZ", 10.0, 10.1, 9.9, 10.1, 10.0, 80000.0))
    _insert_quote(db_path, QuoteFixture("20260702", "300001.SZ", 11.0, 11.1, 9.9, 9.9, 11.0, 120000.0))

    # When
    result = classify_market_regimes(
        db_path,
        RegimeClassificationRequest("20260701", "latest", "regime-v1"),
    )

    # Then
    assert result.classified_count == 2
    with sqlite3.connect(db_path) as conn:
        regimes = conn.execute(
            "SELECT trade_date, market_regime, limit_up_count, limit_down_count "
            "FROM market_regimes ORDER BY trade_date"
        ).fetchall()
        proxy_count = conn.execute("SELECT COUNT(*) FROM limit_events_daily_proxy").fetchone()[0]
    assert regimes == [("20260701", "HOT", 1, 0), ("20260702", "RISK_OFF", 0, 1)]
    assert proxy_count == 3


def test_research_backtest_uses_candidate_snapshots_and_writes_summary(tmp_path: Path) -> None:
    # Given
    db_path = tmp_path / "trading_x.db"
    report_dir = tmp_path / "reports" / "research"
    init_db(db_path)
    persist_candidate_run(
        db_path,
        _run("run-1", "2026-07-01T16:00:00+00:00"),
        [
            replace(
                _candidate("300001.SZ"),
                plan_entry_low=10.0,
                plan_entry_high=11.0,
                plan_breakout_price=10.5,
                plan_stop_price=9.5,
                plan_max_position_cash=10500.0,
            )
        ],
    )
    _insert_quote(db_path, QuoteFixture("20260702", "300001.SZ", 10.2, 10.8, 10.0, 10.7, 10.0, 200000.0))

    # When
    result = run_research_backtest(
        db_path,
        ResearchBacktestRequest(
            start_date="20260701",
            end_date="latest",
            strategy_type=StrategyType.B_CAPACITY_LEADER,
            config_version="v1.0",
            report_dir=report_dir,
        ),
    )

    # Then
    assert result.candidate_count == 1
    assert result.order_count == 1
    assert result.trade_count == 1
    with sqlite3.connect(db_path) as conn:
        orders = conn.execute("SELECT ts_code, side, reason_code FROM backtest_orders").fetchall()
        trades = conn.execute("SELECT ts_code, side, price, shares FROM backtest_trades").fetchall()
        summary = conn.execute(
            "SELECT candidate_count, order_count, trade_count, status FROM backtest_results"
        ).fetchone()
    assert orders == [("300001.SZ", "BUY", "BUY_FILLED")]
    assert trades == [("300001.SZ", "BUY", 10.5, 1000)]
    assert summary == (1, 1, 1, "SUCCESS")
    assert (report_dir / "walk_forward_summary.md").read_text(encoding="utf-8").startswith(
        "# Walk Forward Research Summary"
    )


def test_research_backtest_materializes_a_plan_when_snapshot_prices_are_missing(tmp_path: Path) -> None:
    # Given
    db_path = tmp_path / "trading_x.db"
    init_db(db_path)
    _persist_a_candidate(db_path, "300002.SZ")
    _insert_a_signal_and_next_quotes(db_path, "300002.SZ")

    # When
    result = run_research_backtest(
        db_path,
        ResearchBacktestRequest(
            start_date="20260701",
            end_date="latest",
            strategy_type=StrategyType.A_SPACE_LEADER,
            config_version="v1.0",
            report_dir=tmp_path / "reports" / "research",
        ),
    )

    # Then
    assert result.trade_count == 1
    with sqlite3.connect(db_path) as conn:
        reasons = conn.execute("SELECT reason_code FROM backtest_orders").fetchall()
    assert reasons == [("BUY_FILLED",)]


def test_research_backtest_blocks_a_plan_in_risk_off_regime(tmp_path: Path) -> None:
    # Given
    db_path = tmp_path / "trading_x.db"
    init_db(db_path)
    _persist_a_candidate(db_path, "300003.SZ")
    _insert_a_signal_and_next_quotes(db_path, "300003.SZ")

    _insert_market_regime(db_path, "20260701", "RISK_OFF")

    # When
    result = run_research_backtest(
        db_path,
        ResearchBacktestRequest(
            start_date="20260701",
            end_date="latest",
            strategy_type=StrategyType.A_SPACE_LEADER,
            config_version="v1.0",
            report_dir=tmp_path / "reports" / "research",
        ),
    )

    # Then
    assert result.trade_count == 0
    with sqlite3.connect(db_path) as conn:
        reasons = conn.execute("SELECT reason_code FROM backtest_orders").fetchall()
        trade_count = conn.execute("SELECT COUNT(*) FROM backtest_trades").fetchone()[0]
    assert reasons == [("RISK_BLOCKED_REGIME",)]
    assert trade_count == 0


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


def _persist_a_candidate(db_path: Path, ts_code: str) -> None:
    persist_candidate_run(
        db_path,
        _run("run-1", "2026-07-01T16:00:00+00:00"),
        [
            replace(
                _candidate(ts_code),
                strategy_type=StrategyType.A_SPACE_LEADER,
                candidate_grade=CandidateGrade.A_STRONG,
            )
        ],
    )


def _insert_a_signal_and_next_quotes(db_path: Path, ts_code: str) -> None:
    _insert_quote(
        db_path,
        QuoteFixture("20260701", ts_code, 10.5, 11.0, 10.2, 11.0, 10.0, 300000.0),
    )
    _insert_quote(
        db_path,
        QuoteFixture("20260702", ts_code, 10.9, 11.3, 10.8, 11.2, 11.0, 320000.0),
    )


def _insert_market_regime(db_path: Path, trade_date: str, market_regime: str) -> None:
    with sqlite3.connect(db_path) as conn:
        conn.execute(
            "INSERT INTO market_regimes ("
            "trade_date, method_version, market_regime, market_temperature, limit_up_count, "
            "limit_down_count, avg_pct_chg, total_amount, candidate_count, data_source, created_at"
            ") VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (
                trade_date,
                "regime-v1",
                market_regime,
                0.0,
                0,
                0,
                0.0,
                0.0,
                1,
                "DAILY_PROXY",
                "2026-07-01T00:00:00+00:00",
            ),
        )


def _run(run_id: str, generated_at: str) -> CandidateRunRecord:
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
        generated_at=generated_at,
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
