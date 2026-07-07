import json
import math
import sqlite3

from trading_x.intraday_models import SYSTEM_VERSION, IntradayPlan
from trading_x.trading_rules import new_rule_compatibility_for, rule_regime_for
from trading_x.types import StrategyType


def a_plan_from_snapshot(trade_date: str, row: sqlite3.Row, created_at: str) -> IntradayPlan:
    official_pre_close, pre_close_source = _pre_close(row["limit_pre_close"], row["daily_pre_close"])
    entry_price = round(_first_positive((row["limit_up"], row["daily_close"], row["daily_high"])), 2)
    stop_price = round(entry_price * 0.93, 2)
    rule_regime = str(row["rule_regime_at_signal"] or rule_regime_for(trade_date))
    plan_payload = _plan_payload("candidates_latest+daily_quotes", entry_price, stop_price, rule_regime)
    return IntradayPlan(
        trade_date=trade_date,
        ts_code=row["ts_code"],
        name=str(row["name"] or row["ts_code"]),
        strategy_type=row["strategy_type"],
        allow_trade=True,
        plan_status="ACTIVE",
        entry_low=entry_price,
        entry_high=entry_price,
        breakout_price=entry_price,
        stop_price=stop_price,
        max_stop_distance=0.10,
        max_position_cash=10000.0,
        max_loss=1000.0,
        official_pre_close=official_pre_close,
        pre_close_source=pre_close_source,
        vwap_active_after="09:30:00",
        vwap_above_confirm_seconds=0,
        volume_gate_enabled=False,
        volume_min_abs_amount=1.0,
        volume_same_window_multiplier=1.0,
        volume_ratio_0935=0.0,
        volume_ratio_0945=0.0,
        volume_ratio_1000=0.0,
        theme_name=row["theme_name"],
        theme_confidence=row["theme_confidence"],
        theme_strength_score=row["theme_strength_score"],
        source_candidate_id=f"{row['run_id']}:{row['ts_code']}:{row['strategy_type']}",
        source_report_date=trade_date,
        rule_version_at_signal=str(row["rule_version_at_signal"] or _rule_version(trade_date)),
        rule_regime_at_signal=rule_regime,
        plan_json=json.dumps(plan_payload, ensure_ascii=False, sort_keys=True),
        system_version=SYSTEM_VERSION,
        created_at=created_at,
    )


def a_plan_from_candidate(trade_date: str, row: sqlite3.Row, created_at: str) -> IntradayPlan:
    official_pre_close, pre_close_source = _pre_close(row["limit_pre_close"], row["daily_pre_close"])
    entry_price = round(_first_positive((row["limit_up"], row["close"], row["high"])), 2)
    stop_price = round(entry_price * 0.93, 2)
    rule_regime = rule_regime_for(trade_date)
    plan_payload = _plan_payload("candidates+daily_quotes", entry_price, stop_price, rule_regime)
    return IntradayPlan(
        trade_date=trade_date,
        ts_code=row["ts_code"],
        name=str(row["name"] or row["ts_code"]),
        strategy_type=row["strategy_type"],
        allow_trade=True,
        plan_status="ACTIVE",
        entry_low=entry_price,
        entry_high=entry_price,
        breakout_price=entry_price,
        stop_price=stop_price,
        max_stop_distance=0.10,
        max_position_cash=10000.0,
        max_loss=1000.0,
        official_pre_close=official_pre_close,
        pre_close_source=pre_close_source,
        vwap_active_after="09:30:00",
        vwap_above_confirm_seconds=0,
        volume_gate_enabled=False,
        volume_min_abs_amount=1.0,
        volume_same_window_multiplier=1.0,
        volume_ratio_0935=0.0,
        volume_ratio_0945=0.0,
        volume_ratio_1000=0.0,
        theme_name=row["theme_name"],
        theme_confidence=row["theme_confidence"],
        theme_strength_score=row["theme_strength_score"],
        source_candidate_id=f"{row['ts_code']}:{row['strategy_type']}",
        source_report_date=trade_date,
        rule_version_at_signal=_rule_version(trade_date),
        rule_regime_at_signal=rule_regime,
        plan_json=json.dumps(plan_payload, ensure_ascii=False, sort_keys=True),
        system_version=SYSTEM_VERSION,
        created_at=created_at,
    )


def _plan_payload(source: str, entry_price: float, stop_price: float, rule_regime: str) -> dict[str, float | str]:
    return {
        "source": source,
        "strategy_type": StrategyType.A_SPACE_LEADER,
        "entry_low": entry_price,
        "entry_high": entry_price,
        "breakout_price": entry_price,
        "stop_price": stop_price,
        "rule_regime_at_signal": rule_regime,
    }


def _rule_version(trade_date: str) -> str:
    return new_rule_compatibility_for(trade_date).trading_rule_version


def _pre_close(limit_pre_close: str | int | float | None, daily_pre_close: str | int | float | None) -> tuple[float, str]:
    limit_value = _pre_close_value(limit_pre_close)
    if limit_value is not None:
        return limit_value, "stk_limit_prices.pre_close"
    daily_value = _pre_close_value(daily_pre_close)
    if daily_value is not None:
        return daily_value, "daily_quotes.pre_close"
    return 0.0, "missing"


def _pre_close_value(value: str | int | float | None) -> float | None:
    if value is None:
        return None
    try:
        number = float(value)
    except (TypeError, ValueError):
        return math.nan
    if not math.isfinite(number) or number < 0:
        return math.nan
    return number if number > 0 else None


def _first_positive(values: tuple[str | int | float | None, ...]) -> float:
    for value in values:
        try:
            number = float(value or 0.0)
        except (TypeError, ValueError):
            number = 0.0
        if number > 0:
            return number
    return 0.0
