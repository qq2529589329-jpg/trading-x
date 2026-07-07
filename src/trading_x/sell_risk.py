from dataclasses import dataclass
import json
import sqlite3

from trading_x.intraday_models import IntradayAlert, IntradayPlan, ReplayBar, utc_now_text


def is_terminal_sell_alert(alert_type: str) -> bool:
    return alert_type == "SELL_TRIGGER"


@dataclass(frozen=True, slots=True)
class PositionSnapshot:
    total_shares: float
    available_shares: float
    avg_cost: float
    market_value: float


def load_position_snapshots(conn: sqlite3.Connection, trade_date: str) -> dict[str, PositionSnapshot]:
    rows = conn.execute(
        "SELECT ts_code, total_shares, available_shares, avg_cost, market_value "
        "FROM positions WHERE trade_date = ?",
        (trade_date,),
    ).fetchall()
    return {
        str(row[0]): PositionSnapshot(
            total_shares=float(row[1]),
            available_shares=float(row[2]),
            avg_cost=float(row[3]),
            market_value=float(row[4]),
        )
        for row in rows
    }


def held_position_stop_alert(
    plan: IntradayPlan,
    bar: ReplayBar,
    position: PositionSnapshot | None,
) -> IntradayAlert | None:
    if position is None or position.total_shares <= 0:
        return None
    if position.available_shares > 0:
        alert_type = "SELL_TRIGGER"
        reason_code = "SELL_TRIGGER_STOP_BREAK"
        state_after = "SELL_TRIGGER"
    else:
        alert_type = "RISK_ALERT"
        reason_code = "SELL_BLOCKED_T1_NO_AVAILABLE_SHARES"
        state_after = "SELL_BLOCKED_T1"
    snapshot = {
        "price": bar.price,
        "amount_since_open": bar.amount_since_open,
        "volume_since_open": bar.volume_since_open,
        "bar_high": bar.bar_high,
        "bar_low": bar.bar_low,
        "continuous_vwap": bar.continuous_vwap,
        "total_shares": position.total_shares,
        "available_shares": position.available_shares,
        "avg_cost": position.avg_cost,
        "market_value": position.market_value,
    }
    return IntradayAlert(
        trade_date=plan.trade_date,
        ts_code=plan.ts_code,
        strategy_type=plan.strategy_type,
        alert_time=bar.quote_time,
        alert_type=alert_type,
        severity="HIGH",
        rule_id=reason_code,
        title=f"{plan.name} {alert_type}",
        message=reason_code,
        reason_code=reason_code,
        state_before="HELD_POSITION",
        state_after=state_after,
        snapshot_json=json.dumps(snapshot, ensure_ascii=False, sort_keys=True),
        plan_json=plan.plan_json,
        created_at=utc_now_text(),
    )
