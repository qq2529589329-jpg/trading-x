from collections.abc import Mapping, Sequence
import math
import sqlite3

from trading_x.intraday_models import IntradayAlert, IntradayPlan, ReplayBar
from trading_x.intraday_rules import RuleContext, alert_exists, alert_for_bar
from trading_x.types import StrategyType


def load_plans(
    conn: sqlite3.Connection,
    trade_date: str,
    strategy_type: StrategyType = StrategyType.B_CAPACITY_LEADER,
) -> list[IntradayPlan]:
    rows = conn.execute(
        "SELECT * FROM intraday_plans WHERE trade_date = ? AND strategy_type = ? ORDER BY ts_code",
        (trade_date, strategy_type),
    ).fetchall()
    return [_plan_from_row(row) for row in rows]


def disable_invalid_plans(conn: sqlite3.Connection, plans: Sequence[IntradayPlan]) -> list[str]:
    invalid = [plan for plan in plans if not plan.is_valid]
    for plan in invalid:
        conn.execute(
            "UPDATE intraday_plans SET plan_status = 'DISABLED' "
            "WHERE trade_date = ? AND ts_code = ? AND strategy_type = ?",
            (plan.trade_date, plan.ts_code, plan.strategy_type),
        )
    return [f"{plan.ts_code}:{plan.strategy_type}:PLAN_INVALID" for plan in invalid]


def evaluate_replay(
    conn: sqlite3.Connection,
    plans: Sequence[IntradayPlan],
    bars: Sequence[ReplayBar],
) -> list[IntradayAlert]:
    alerts: list[IntradayAlert] = []
    bars_by_symbol = _bars_by_symbol(bars)
    for plan in plans:
        above_vwap_since: int | None = None
        for bar in bars_by_symbol.get(plan.ts_code, []):
            if _is_above_active_vwap(plan, bar):
                bar_seconds = _time_seconds(bar.quote_time)
                if above_vwap_since is None:
                    above_vwap_since = bar_seconds
                vwap_confirmed = bar_seconds - above_vwap_since >= plan.vwap_above_confirm_seconds
            else:
                above_vwap_since = None
                vwap_confirmed = plan.vwap_above_confirm_seconds <= 0
            alert = alert_for_bar(conn, RuleContext(plan, bar, vwap_confirmed))
            if alert is not None and insert_alert(conn, alert):
                alerts.append(alert)
    return alerts


def insert_alert(conn: sqlite3.Connection, alert: IntradayAlert) -> bool:
    if alert_exists(conn, alert, alert.alert_type, alert.reason_code):
        return False
    conn.execute(_INSERT_ALERT_SQL, _alert_params(alert))
    if alert.alert_type in {"BUY_TRIGGER", "ENTRY_CANCELLED"}:
        conn.execute(
            "INSERT OR IGNORE INTO intraday_alert_locks ("
            "trade_date, ts_code, strategy_type, alert_type, locked, locked_at, rule_id"
            ") VALUES (?, ?, ?, ?, ?, ?, ?)",
            (
                alert.trade_date,
                alert.ts_code,
                alert.strategy_type,
                alert.alert_type,
                1,
                alert.created_at,
                alert.rule_id,
            ),
        )
    return True


def _plan_from_row(row: sqlite3.Row) -> IntradayPlan:
    return IntradayPlan(
        trade_date=row["trade_date"],
        ts_code=str(row["ts_code"] or ""),
        name=str(row["name"] or ""),
        strategy_type=row["strategy_type"],
        allow_trade=row["allow_trade"] in (1, "1"),
        plan_status=row["plan_status"],
        entry_low=_float_or_nan(row["entry_low"]),
        entry_high=_float_or_nan(row["entry_high"]),
        breakout_price=_float_or_nan(row["breakout_price"]),
        stop_price=_float_or_nan(row["stop_price"]),
        max_stop_distance=_float_or_nan(row["max_stop_distance"]),
        max_position_cash=_float_or_nan(row["max_position_cash"]),
        max_loss=_float_or_nan(row["max_loss"]),
        official_pre_close=_float_or_nan(row["official_pre_close"]),
        pre_close_source=str(row["pre_close_source"] or ""),
        vwap_active_after=str(row["vwap_active_after"] or ""),
        vwap_above_confirm_seconds=_int_or_minus_one(row["vwap_above_confirm_seconds"]),
        volume_gate_enabled=row["volume_gate_enabled"] in (1, "1"),
        volume_min_abs_amount=_float_or_nan(row["volume_min_abs_amount"]),
        volume_same_window_multiplier=_float_or_nan(row["volume_same_window_multiplier"]),
        volume_ratio_0935=_float_or_nan(row["volume_ratio_0935"]),
        volume_ratio_0945=_float_or_nan(row["volume_ratio_0945"]),
        volume_ratio_1000=_float_or_nan(row["volume_ratio_1000"]),
        theme_name=row["theme_name"],
        theme_confidence=row["theme_confidence"],
        theme_strength_score=row["theme_strength_score"],
        source_candidate_id=str(row["source_candidate_id"] or ""),
        source_report_date=str(row["source_report_date"] or ""),
        rule_version_at_signal=str(row["rule_version_at_signal"] or ""),
        rule_regime_at_signal=str(row["rule_regime_at_signal"] or ""),
        plan_json=str(row["plan_json"] or ""),
        system_version=str(row["system_version"] or ""),
        created_at=str(row["created_at"] or ""),
    )


def _float_or_nan(value: str | int | float | None) -> float:
    if value is None:
        return math.nan
    try:
        return float(value)
    except (TypeError, ValueError):
        return math.nan


def _int_or_minus_one(value: str | int | float | None) -> int:
    match value:
        case int() as number:
            return number
        case str() as text:
            stripped = text.strip()
            return int(stripped) if stripped.isdigit() else -1
        case _:
            return -1


def _bars_by_symbol(bars: Sequence[ReplayBar]) -> Mapping[str, list[ReplayBar]]:
    grouped: dict[str, list[ReplayBar]] = {}
    for bar in bars:
        grouped.setdefault(bar.ts_code, []).append(bar)
    for symbol_bars in grouped.values():
        symbol_bars.sort(key=lambda bar: bar.quote_time)
    return grouped


def _is_above_active_vwap(plan: IntradayPlan, bar: ReplayBar) -> bool:
    vwap = bar.continuous_vwap
    volume_pass = (not plan.volume_gate_enabled) or bar.amount_since_open >= plan.volume_min_abs_amount
    return (
        bar.quote_time >= plan.vwap_active_after
        and vwap is not None
        and bar.price > vwap
        and volume_pass
        and plan.entry_low <= bar.price <= plan.entry_high
    )


def _time_seconds(text: str) -> int:
    hour, minute, second = text.split(":")
    return int(hour) * 3600 + int(minute) * 60 + int(second)


def _alert_params(alert: IntradayAlert) -> tuple:
    return (
        alert.trade_date,
        alert.ts_code,
        alert.strategy_type,
        alert.alert_time,
        alert.alert_type,
        alert.severity,
        alert.rule_id,
        alert.title,
        alert.message,
        alert.reason_code,
        alert.state_before,
        alert.state_after,
        alert.snapshot_json,
        alert.plan_json,
        alert.created_at,
    )


_INSERT_ALERT_SQL = (
    "INSERT INTO intraday_alerts ("
    "trade_date, ts_code, strategy_type, alert_time, alert_type, severity, rule_id, "
    "title, message, reason_code, state_before, state_after, snapshot_json, "
    "plan_json, created_at"
    ") VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)"
)
