import sqlite3

from trading_x.research_backtest_plans import decide_backtest_order
from trading_x.research_models import BacktestPlan
from trading_x.types import StrategyType


def test_decide_backtest_order_marks_a_gap_continuation_candidate() -> None:
    # Given
    plan = BacktestPlan(10.0, 10.0, 10.0, 9.3, 10_000.0, "a_materialized_daily_proxy")

    # When
    decision = decide_backtest_order(_row(next_open=10.5, next_low=10.1, rank=2), plan)

    # Then
    assert decision.reason_code == "A_GAP_CONTINUATION_CANDIDATE"
    assert not decision.is_filled


def test_decide_backtest_order_keeps_failed_gap_as_open_above_entry_high() -> None:
    # Given
    plan = BacktestPlan(10.0, 10.0, 10.0, 9.3, 10_000.0, "a_materialized_daily_proxy")

    # When
    decision = decide_backtest_order(_row(next_open=10.5, next_low=9.9, rank=2), plan)

    # Then
    assert decision.reason_code == "OPEN_ABOVE_ENTRY_HIGH"


def _row(next_open: float, next_low: float, rank: int) -> sqlite3.Row:
    with sqlite3.connect(":memory:") as conn:
        conn.row_factory = sqlite3.Row
        row = conn.execute(
            "SELECT ? AS market_regime, ? AS next_trade_date, ? AS next_open, "
            "? AS next_high, ? AS next_low, ? AS next_close, ? AS next_up_limit, "
            "? AS exit_trade_date, ? AS rank, ? AS strategy_type",
            (
                "HOT",
                "20260702",
                next_open,
                10.8,
                next_low,
                10.6,
                11.0,
                "20260703",
                rank,
                StrategyType.A_SPACE_LEADER.value,
            ),
        ).fetchone()
    assert row is not None
    return row
