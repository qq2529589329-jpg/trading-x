from pathlib import Path
from typing import assert_never
import json
import math
import sqlite3

from trading_x.intraday_a_plans import a_plan_from_candidate, a_plan_from_snapshot
from trading_x.intraday_models import SYSTEM_VERSION, IntradayPlan, utc_now_text
from trading_x.trading_rules import new_rule_compatibility_for, rule_regime_for
from trading_x.types import StrategyType


def materialize_intraday_plans(
    db_path: Path,
    trade_date: str,
    *,
    strategy_type: StrategyType = StrategyType.B_CAPACITY_LEADER,
) -> int:
    created_at = utc_now_text()
    with sqlite3.connect(db_path) as conn:
        conn.row_factory = sqlite3.Row
        conn.execute(
            "DELETE FROM intraday_plans WHERE trade_date = ? AND strategy_type = ?",
            (trade_date, strategy_type),
        )
        snapshot_run_exists = (
            conn.execute("SELECT 1 FROM candidate_runs WHERE trade_date = ? LIMIT 1", (trade_date,)).fetchone()
            is not None
        )
        snapshot_rows = conn.execute(
            "SELECT cl.run_id, cl.ts_code, cl.name, cl.strategy_type, cl.theme_name, "
            "cl.theme_confidence, cl.theme_strength_score, cl.entry_low, cl.entry_high, "
            "cl.breakout_price, cl.stop_price, cl.max_position_cash, cl.max_loss, "
            "cl.rule_version_at_signal, cl.rule_regime_at_signal, cl.plan_json, "
            "d.high AS daily_high, d.low AS daily_low, d.close AS daily_close, "
            "d.pre_close AS daily_pre_close, l.pre_close AS limit_pre_close, l.up_limit AS limit_up "
            "FROM candidates_latest cl "
            "LEFT JOIN daily_quotes d ON d.ts_code = cl.ts_code AND d.trade_date = cl.trade_date "
            "LEFT JOIN stk_limit_prices l ON l.ts_code = cl.ts_code AND l.trade_date = cl.trade_date "
            "WHERE cl.trade_date = ? AND cl.strategy_type = ?",
            (trade_date, strategy_type),
        ).fetchall()
        if snapshot_run_exists:
            plans = [_plan_from_snapshot(trade_date, row, created_at, strategy_type) for row in snapshot_rows]
            conn.executemany(_INSERT_PLAN_SQL, [_plan_params(plan) for plan in plans])
            return len(plans)
        rows = conn.execute(
            "SELECT c.ts_code, s.name, c.strategy_type, c.theme_name, c.theme_confidence, "
            "c.theme_strength_score, d.high, d.low, d.close, "
            "d.pre_close AS daily_pre_close, l.pre_close AS limit_pre_close, l.up_limit AS limit_up "
            "FROM candidates c "
            "LEFT JOIN stock_universe s ON s.ts_code = c.ts_code "
            "LEFT JOIN daily_quotes d ON d.ts_code = c.ts_code AND d.trade_date = c.trade_date "
            "LEFT JOIN stk_limit_prices l ON l.ts_code = c.ts_code AND l.trade_date = c.trade_date "
            "WHERE c.trade_date = ? AND c.strategy_type = ? AND c.risk_pass = 1",
            (trade_date, strategy_type),
        ).fetchall()
        plans = [_plan_from_candidate(trade_date, row, created_at, strategy_type) for row in rows]
        conn.executemany(_INSERT_PLAN_SQL, [_plan_params(plan) for plan in plans])
    return len(plans)


def _plan_from_snapshot(
    trade_date: str,
    row: sqlite3.Row,
    created_at: str,
    strategy_type: StrategyType,
) -> IntradayPlan:
    match strategy_type:
        case StrategyType.A_SPACE_LEADER:
            return a_plan_from_snapshot(trade_date, row, created_at)
        case StrategyType.B_CAPACITY_LEADER:
            return _b_plan_from_snapshot(trade_date, row, created_at)
        case unreachable:
            assert_never(unreachable)


def _plan_from_candidate(
    trade_date: str,
    row: sqlite3.Row,
    created_at: str,
    strategy_type: StrategyType,
) -> IntradayPlan:
    match strategy_type:
        case StrategyType.A_SPACE_LEADER:
            return a_plan_from_candidate(trade_date, row, created_at)
        case StrategyType.B_CAPACITY_LEADER:
            return _b_plan_from_candidate(trade_date, row, created_at)
        case unreachable:
            assert_never(unreachable)



def _b_plan_from_snapshot(trade_date: str, row: sqlite3.Row, created_at: str) -> IntradayPlan:
    official_pre_close, pre_close_source = _pre_close(row["limit_pre_close"], row["daily_pre_close"])
    return IntradayPlan(
        trade_date=trade_date,
        ts_code=row["ts_code"],
        name=str(row["name"] or row["ts_code"]),
        strategy_type=row["strategy_type"],
        allow_trade=True,
        plan_status="ACTIVE",
        entry_low=_float_or_zero(row["entry_low"]),
        entry_high=_float_or_zero(row["entry_high"]),
        breakout_price=_float_or_zero(row["breakout_price"]),
        stop_price=_float_or_zero(row["stop_price"]),
        max_stop_distance=0.07,
        max_position_cash=_float_or_zero(row["max_position_cash"]),
        max_loss=_float_or_zero(row["max_loss"]),
        official_pre_close=official_pre_close,
        pre_close_source=pre_close_source,
        vwap_active_after="09:35:00",
        vwap_above_confirm_seconds=120,
        volume_gate_enabled=True,
        volume_min_abs_amount=10_000_000.0,
        volume_same_window_multiplier=1.3,
        volume_ratio_0935=0.03,
        volume_ratio_0945=0.05,
        volume_ratio_1000=0.08,
        theme_name=row["theme_name"],
        theme_confidence=row["theme_confidence"],
        theme_strength_score=row["theme_strength_score"],
        source_candidate_id=f"{row['run_id']}:{row['ts_code']}:{row['strategy_type']}",
        source_report_date=trade_date,
        rule_version_at_signal=str(row["rule_version_at_signal"] or _rule_version(trade_date)),
        rule_regime_at_signal=str(row["rule_regime_at_signal"] or rule_regime_for(trade_date)),
        plan_json=str(row["plan_json"] or ""),
        system_version=SYSTEM_VERSION,
        created_at=created_at,
    )


def _b_plan_from_candidate(trade_date: str, row: sqlite3.Row, created_at: str) -> IntradayPlan:
    official_pre_close, pre_close_source = _pre_close(row["limit_pre_close"], row["daily_pre_close"])
    close = _float_or_zero(row["close"])
    high = _float_or_zero(row["high"])
    low = _float_or_zero(row["low"])
    rule_regime = rule_regime_for(trade_date)
    plan_payload = {
        "source": "candidates+daily_quotes",
        "entry_low": close,
        "entry_high": round(high * 1.05, 2),
        "breakout_price": high,
        "stop_price": low,
        "rule_regime_at_signal": rule_regime,
    }
    return IntradayPlan(
        trade_date=trade_date,
        ts_code=row["ts_code"],
        name=str(row["name"] or row["ts_code"]),
        strategy_type=row["strategy_type"],
        allow_trade=True,
        plan_status="ACTIVE",
        entry_low=round(close, 2),
        entry_high=round(high * 1.05, 2),
        breakout_price=round(high, 2),
        stop_price=round(low, 2),
        max_stop_distance=0.07,
        max_position_cash=10000.0,
        max_loss=500.0,
        official_pre_close=official_pre_close,
        pre_close_source=pre_close_source,
        vwap_active_after="09:35:00",
        vwap_above_confirm_seconds=120,
        volume_gate_enabled=True,
        volume_min_abs_amount=10_000_000.0,
        volume_same_window_multiplier=1.3,
        volume_ratio_0935=0.03,
        volume_ratio_0945=0.05,
        volume_ratio_1000=0.08,
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



def _float_or_zero(value: str | int | float | None) -> float:
    try:
        return float(value or 0.0)
    except (TypeError, ValueError):
        return 0.0


def _plan_params(plan: IntradayPlan) -> tuple:
    return (
        plan.trade_date,
        plan.ts_code,
        plan.name,
        plan.strategy_type,
        int(plan.allow_trade),
        plan.plan_status,
        plan.entry_low,
        plan.entry_high,
        plan.breakout_price,
        plan.stop_price,
        plan.max_stop_distance,
        plan.max_position_cash,
        plan.max_loss,
        plan.official_pre_close,
        plan.pre_close_source,
        plan.vwap_active_after,
        plan.vwap_above_confirm_seconds,
        int(plan.volume_gate_enabled),
        plan.volume_min_abs_amount,
        plan.volume_same_window_multiplier,
        plan.volume_ratio_0935,
        plan.volume_ratio_0945,
        plan.volume_ratio_1000,
        plan.theme_name,
        plan.theme_confidence,
        plan.theme_strength_score,
        plan.source_candidate_id,
        plan.source_report_date,
        plan.rule_version_at_signal,
        plan.rule_regime_at_signal,
        plan.plan_json,
        plan.system_version,
        plan.created_at,
    )


_INSERT_PLAN_SQL = (
    "INSERT INTO intraday_plans ("
    "trade_date, ts_code, name, strategy_type, allow_trade, plan_status, entry_low, "
    "entry_high, breakout_price, stop_price, max_stop_distance, max_position_cash, "
    "max_loss, official_pre_close, pre_close_source, vwap_active_after, "
    "vwap_above_confirm_seconds, volume_gate_enabled, volume_min_abs_amount, "
    "volume_same_window_multiplier, volume_ratio_0935, volume_ratio_0945, "
    "volume_ratio_1000, theme_name, theme_confidence, theme_strength_score, "
    "source_candidate_id, source_report_date, rule_version_at_signal, rule_regime_at_signal, "
    "plan_json, system_version, created_at"
    ") VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)"
)
