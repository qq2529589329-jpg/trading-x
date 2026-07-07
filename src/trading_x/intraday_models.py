from dataclasses import dataclass
from datetime import UTC, datetime
from typing import Final
import json
import math


SYSTEM_VERSION: Final = "intraday-replay-mvp-v1"
REQUIRED_REPLAY_COLUMNS: Final = frozenset(
    {
        "trade_date",
        "quote_time",
        "ts_code",
        "price",
        "amount_since_open",
        "volume_since_open",
        "bar_high",
        "bar_low",
    }
)


@dataclass(frozen=True, slots=True)
class IntradayPlan:
    trade_date: str
    ts_code: str
    name: str
    strategy_type: str
    allow_trade: bool
    plan_status: str
    entry_low: float
    entry_high: float
    breakout_price: float
    stop_price: float
    max_stop_distance: float
    max_position_cash: float
    max_loss: float
    official_pre_close: float
    pre_close_source: str
    vwap_active_after: str
    vwap_above_confirm_seconds: int
    volume_gate_enabled: bool
    volume_min_abs_amount: float
    volume_same_window_multiplier: float
    volume_ratio_0935: float
    volume_ratio_0945: float
    volume_ratio_1000: float
    theme_name: str | None
    theme_confidence: str | None
    theme_strength_score: float | None
    source_candidate_id: str
    source_report_date: str
    rule_version_at_signal: str
    rule_regime_at_signal: str
    plan_json: str
    system_version: str
    created_at: str

    @property
    def is_valid(self) -> bool:
        return (
            self.allow_trade
            and self.plan_status == "ACTIVE"
            and all(
                math.isfinite(value)
                for value in (
                    self.entry_low,
                    self.entry_high,
                    self.breakout_price,
                    self.stop_price,
                    self.max_stop_distance,
                    self.max_position_cash,
                    self.max_loss,
                    self.official_pre_close,
                    self.volume_min_abs_amount,
                    self.volume_same_window_multiplier,
                    self.volume_ratio_0935,
                    self.volume_ratio_0945,
                    self.volume_ratio_1000,
                )
            )
            and self.entry_low > 0
            and self.entry_high > 0
            and self.breakout_price > 0
            and self.stop_price > 0
            and self.max_stop_distance > 0
            and self.max_position_cash > 0
            and self.max_loss > 0
            and self.official_pre_close >= 0
            and self.vwap_above_confirm_seconds >= 0
            and bool(self.ts_code.strip())
            and bool(self.name.strip())
            and bool(self.pre_close_source.strip())
            and bool(self.source_candidate_id.strip())
            and self.source_report_date == self.trade_date
            and bool(self.rule_version_at_signal.strip())
            and bool(self.rule_regime_at_signal.strip())
            and bool(self.system_version.strip())
            and bool(self.created_at.strip())
            and (not self.volume_gate_enabled or self.volume_min_abs_amount > 0)
            and self.volume_same_window_multiplier > 0
            and 0 <= self.volume_ratio_0935 <= self.volume_ratio_0945 <= self.volume_ratio_1000
            and self.stop_price < self.entry_low <= self.breakout_price <= self.entry_high
            and (self.entry_low - self.stop_price) / self.entry_low <= self.max_stop_distance
            and (
                self.max_position_cash * ((self.entry_low - self.stop_price) / self.entry_low)
                <= self.max_loss
            )
            and _is_json_object(self.plan_json)
            and is_clock_time(self.vwap_active_after)
        )


@dataclass(frozen=True, slots=True)
class ReplayBar:
    trade_date: str
    quote_time: str
    ts_code: str
    price: float
    amount_since_open: float
    volume_since_open: float
    bar_high: float
    bar_low: float

    @property
    def continuous_vwap(self) -> float | None:
        if self.volume_since_open <= 0:
            return None
        return self.amount_since_open / self.volume_since_open


@dataclass(frozen=True, slots=True)
class IntradayAlert:
    trade_date: str
    ts_code: str
    strategy_type: str
    alert_time: str
    alert_type: str
    severity: str
    rule_id: str
    title: str
    message: str
    reason_code: str
    state_before: str
    state_after: str
    snapshot_json: str
    plan_json: str
    created_at: str


@dataclass(frozen=True, slots=True)
class AlertIntent:
    alert_type: str
    severity: str
    reason_code: str
    state_before: str
    state_after: str


@dataclass(frozen=True, slots=True)
class ReplayResult:
    trade_date: str
    input_file: str
    input_sha256: str
    plan_count: int
    alert_count: int
    status: str
    error_message: str | None
    started_at: str
    ended_at: str


def utc_now_text() -> str:
    return datetime.now(UTC).isoformat()


def is_clock_time(text: str) -> bool:
    parts = text.split(":")
    if len(parts) != 3 or any(len(part) != 2 or not part.isdigit() for part in parts):
        return False
    hour, minute, second = (int(part) for part in parts)
    return 0 <= hour <= 23 and 0 <= minute <= 59 and 0 <= second <= 59


def _is_json_object(text: str) -> bool:
    if not text.lstrip().startswith("{"):
        return False
    try:
        json.loads(text)
    except json.JSONDecodeError:
        return False
    return True
