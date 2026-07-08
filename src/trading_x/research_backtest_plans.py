import sqlite3
from typing import assert_never

from trading_x.research_models import BacktestDecision, BacktestPlan
from trading_x.types import StrategyType


def resolve_backtest_plan(row: sqlite3.Row, strategy_type: StrategyType) -> BacktestPlan | None:
    plan = _structured_plan(row, "snapshot", "snapshot")
    if plan is not None:
        return plan
    plan = _structured_plan(row, "intraday", "intraday_plans")
    if plan is not None:
        return plan
    match strategy_type:
        case StrategyType.A_SPACE_LEADER:
            return _a_materialized_plan(row)
        case StrategyType.B_CAPACITY_LEADER:
            return _b_materialized_plan(row)
        case unreachable:
            assert_never(unreachable)


def decide_backtest_order(row: sqlite3.Row, plan: BacktestPlan | None) -> BacktestDecision:
    if plan is None:
        return BacktestDecision("PLAN_PRICE_MISSING", 0.0, 0.0, None)
    if _text(row["market_regime"]) == "RISK_OFF":
        return BacktestDecision("RISK_BLOCKED_REGIME", plan.breakout_price, 0.0, plan)
    if row["next_trade_date"] is None:
        return BacktestDecision("NO_NEXT_QUOTE", plan.breakout_price, 0.0, plan)
    if _is_one_word_limit_up(row):
        return BacktestDecision("ONE_WORD_LIMIT_UP", plan.breakout_price, 0.0, plan)
    if _positive(row["next_open"]) > plan.entry_high:
        return BacktestDecision("OPEN_ABOVE_ENTRY_HIGH", plan.breakout_price, 0.0, plan)
    if _positive(row["next_high"]) < plan.breakout_price:
        return BacktestDecision("NO_BREAKOUT_TOUCH", plan.breakout_price, 0.0, plan)
    fill_price = max(plan.breakout_price, _positive(row["next_open"]))
    return BacktestDecision("BUY_FILLED", plan.breakout_price, fill_price, plan)


def _structured_plan(row: sqlite3.Row, prefix: str, source: str) -> BacktestPlan | None:
    entry_low = _positive(row[f"{prefix}_entry_low"])
    entry_high = _positive(row[f"{prefix}_entry_high"])
    breakout = _positive(row[f"{prefix}_breakout_price"])
    if entry_low <= 0 and entry_high <= 0 and breakout <= 0:
        return None
    low = _first_positive((entry_low, breakout, entry_high))
    high = _first_positive((entry_high, breakout, entry_low))
    breakout_price = _first_positive((breakout, high, low))
    stop_price = _first_positive((row[f"{prefix}_stop_price"], low * 0.93))
    return BacktestPlan(
        entry_low=low,
        entry_high=high,
        breakout_price=breakout_price,
        stop_price=stop_price,
        max_position_cash=_max_cash(row[f"{prefix}_max_position_cash"]),
        source=source,
    )


def _a_materialized_plan(row: sqlite3.Row) -> BacktestPlan | None:
    entry = _first_positive((row["signal_up_limit"], row["signal_close"], row["signal_high"]))
    if entry <= 0:
        return None
    return BacktestPlan(
        entry_low=round(entry, 2),
        entry_high=round(entry, 2),
        breakout_price=round(entry, 2),
        stop_price=round(entry * 0.93, 2),
        max_position_cash=10_000.0,
        source="a_materialized_daily_proxy",
    )


def _b_materialized_plan(row: sqlite3.Row) -> BacktestPlan | None:
    close = _positive(row["signal_close"])
    high = _positive(row["signal_high"])
    low = _positive(row["signal_low"])
    if close <= 0 or high <= 0 or low <= 0:
        return None
    return BacktestPlan(
        entry_low=round(close, 2),
        entry_high=round(high * 1.05, 2),
        breakout_price=round(high, 2),
        stop_price=round(low, 2),
        max_position_cash=10_000.0,
        source="b_materialized_daily_proxy",
    )


def _is_one_word_limit_up(row: sqlite3.Row) -> bool:
    up_limit = _positive(row["next_up_limit"])
    if up_limit <= 0:
        return False
    prices = (
        _positive(row["next_open"]),
        _positive(row["next_high"]),
        _positive(row["next_low"]),
        _positive(row["next_close"]),
    )
    return all(price >= up_limit * 0.999 for price in prices)


def _first_positive(values: tuple[float | int | str | None, ...]) -> float:
    for value in values:
        number = _positive(value)
        if number > 0:
            return number
    return 0.0


def _max_cash(value: float | int | str | None) -> float:
    number = _positive(value)
    return number if number > 0 else 10_000.0


def _positive(value: float | int | str | None) -> float:
    if value is None:
        return 0.0
    try:
        number = float(value)
    except (TypeError, ValueError):
        return 0.0
    return number if number > 0 else 0.0


def _text(value: str | None) -> str:
    return "" if value is None else value
