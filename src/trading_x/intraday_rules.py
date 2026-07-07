from dataclasses import dataclass
from typing import assert_never
import json
import sqlite3

from trading_x.intraday_models import AlertIntent, IntradayAlert, IntradayPlan, ReplayBar, utc_now_text
from trading_x.trading_rules import is_post_close_fixed_price_time
from trading_x.types import StrategyType

@dataclass(frozen=True, slots=True)
class RuleContext:
    plan: IntradayPlan
    bar: ReplayBar
    vwap_confirmed: bool


def alert_for_bar(
    conn: sqlite3.Connection,
    context: RuleContext,
) -> IntradayAlert | None:
    plan = context.plan
    bar = context.bar
    if _is_locked(conn, plan, "ENTRY_CANCELLED"):
        return None
    vwap = bar.continuous_vwap
    if plan.official_pre_close <= 0 and bar.price >= plan.entry_low:
        return _alert(
            plan,
            bar,
            AlertIntent("WATCH", "LOW", "PRE_CLOSE_MISSING", "OPEN_OBSERVING", "OPEN_OBSERVING"),
        )
    if _is_locked(conn, plan, "BUY_TRIGGER"):
        if bar.price <= plan.stop_price:
            return _alert(
                plan,
                bar,
                AlertIntent(
                    "ENTRY_CANCELLED",
                    "HIGH",
                    "ENTRY_CANCELLED_PRICE_OUT_OF_RANGE",
                    "ENTRY_ARMED",
                    "ENTRY_CANCELLED",
                ),
            )
        if vwap is not None and bar.price < vwap:
            return _alert(
                plan,
                bar,
                AlertIntent(
                    "ENTRY_CANCELLED",
                    "HIGH",
                    "ENTRY_CANCELLED_VWAP_BREAK",
                    "ENTRY_ARMED",
                    "ENTRY_CANCELLED",
                ),
            )
        return None
    if bar.price <= plan.stop_price:
        return _alert(
            plan,
            bar,
            AlertIntent(
                "ENTRY_CANCELLED",
                "HIGH",
                "ENTRY_CANCELLED_PRICE_OUT_OF_RANGE",
                "OPEN_OBSERVING",
                "ENTRY_CANCELLED",
            ),
        )
    if is_post_close_fixed_price_time(plan.trade_date, bar.quote_time):
        if plan.entry_low <= bar.price <= plan.entry_high:
            return _alert(
                plan,
                bar,
                AlertIntent(
                    "WATCH",
                    "LOW",
                    "POST_CLOSE_FIXED_PRICE_OBSERVATION",
                    "OPEN_OBSERVING",
                    "OPEN_OBSERVING",
                ),
            )
        return None
    match StrategyType(plan.strategy_type):
        case StrategyType.A_SPACE_LEADER:
            return _a_alert_for_bar(conn, plan, bar)
        case StrategyType.B_CAPACITY_LEADER:
            pass
        case unreachable:
            assert_never(unreachable)
    if bar.quote_time < plan.vwap_active_after:
        return None
    if vwap is None:
        if plan.entry_low <= bar.price <= plan.entry_high:
            return _alert(
                plan,
                bar,
                AlertIntent("WATCH", "LOW", "VOLUME_GATE_FAILED", "OPEN_OBSERVING", "OPEN_OBSERVING"),
            )
        return None
    volume_pass = (not plan.volume_gate_enabled) or bar.amount_since_open >= plan.volume_min_abs_amount
    if bar.price > vwap and not volume_pass and plan.entry_low <= bar.price <= plan.entry_high:
        return _alert(
            plan,
            bar,
            AlertIntent("WATCH", "LOW", "VOLUME_GATE_FAILED", "OPEN_OBSERVING", "OPEN_OBSERVING"),
        )
    if bar.price > vwap and volume_pass and not context.vwap_confirmed and plan.entry_low <= bar.price <= plan.entry_high:
        return _alert(
            plan,
            bar,
            AlertIntent("WATCH", "LOW", "B_VWAP_CONFIRMING", "OPEN_OBSERVING", "OPEN_OBSERVING"),
        )
    if not (bar.price > vwap and volume_pass and context.vwap_confirmed):
        return None
    if bar.price >= plan.breakout_price and plan.entry_low <= bar.price <= plan.entry_high:
        return _alert(
            plan,
            bar,
            AlertIntent("BUY_TRIGGER", "HIGH", "B_BUY_TRIGGERED", "ENTRY_ARMED", "BUY_TRIGGER"),
        )
    if plan.entry_low <= bar.price <= plan.entry_high:
        return _deduped_alert(conn, plan, bar)
    return None


def alert_exists(
    conn: sqlite3.Connection,
    item: IntradayPlan | IntradayAlert,
    alert_type: str,
    reason_code: str,
) -> bool:
    row = conn.execute(
        "SELECT 1 FROM intraday_alerts WHERE trade_date = ? AND ts_code = ? "
        "AND strategy_type = ? AND alert_type = ? AND reason_code = ?",
        (item.trade_date, item.ts_code, item.strategy_type, alert_type, reason_code),
    ).fetchone()
    return row is not None


def _a_alert_for_bar(
    conn: sqlite3.Connection,
    plan: IntradayPlan,
    bar: ReplayBar,
) -> IntradayAlert | None:
    if bar.quote_time < plan.vwap_active_after or not (plan.entry_low <= bar.price <= plan.entry_high):
        return None
    if bar.price >= plan.breakout_price:
        return _alert(
            plan,
            bar,
            AlertIntent("BUY_TRIGGER", "HIGH", "A_BUY_TRIGGERED", "ENTRY_ARMED", "BUY_TRIGGER"),
        )
    if alert_exists(conn, plan, "BUY_READY", "A_LIMIT_READY"):
        return None
    return _alert(
        plan,
        bar,
        AlertIntent("BUY_READY", "MEDIUM", "A_LIMIT_READY", "OPEN_OBSERVING", "BUY_READY"),
    )


def _deduped_alert(
    conn: sqlite3.Connection,
    plan: IntradayPlan,
    bar: ReplayBar,
) -> IntradayAlert | None:
    if alert_exists(conn, plan, "BUY_READY", "B_BREAKOUT_READY"):
        return None
    return _alert(
        plan,
        bar,
    AlertIntent("BUY_READY", "MEDIUM", "B_BREAKOUT_READY", "OPEN_OBSERVING", "BUY_READY"),
    )


def _alert(plan: IntradayPlan, bar: ReplayBar, intent: AlertIntent) -> IntradayAlert:
    snapshot = {
        "price": bar.price,
        "amount_since_open": bar.amount_since_open,
        "volume_since_open": bar.volume_since_open,
        "bar_high": bar.bar_high,
        "bar_low": bar.bar_low,
        "continuous_vwap": bar.continuous_vwap,
    }
    return IntradayAlert(
        trade_date=plan.trade_date,
        ts_code=plan.ts_code,
        strategy_type=plan.strategy_type,
        alert_time=bar.quote_time,
        alert_type=intent.alert_type,
        severity=intent.severity,
        rule_id=intent.reason_code,
        title=f"{plan.name} {intent.alert_type}",
        message=intent.reason_code,
        reason_code=intent.reason_code,
        state_before=intent.state_before,
        state_after=intent.state_after,
        snapshot_json=json.dumps(snapshot, ensure_ascii=False, sort_keys=True),
        plan_json=plan.plan_json,
        created_at=utc_now_text(),
    )


def _is_locked(conn: sqlite3.Connection, plan: IntradayPlan, alert_type: str) -> bool:
    row = conn.execute(
        "SELECT 1 FROM intraday_alert_locks "
        "WHERE trade_date = ? AND ts_code = ? AND strategy_type = ? AND alert_type = ? "
        "AND locked = 1",
        (plan.trade_date, plan.ts_code, plan.strategy_type, alert_type),
    ).fetchone()
    return row is not None
