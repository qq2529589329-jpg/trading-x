from dataclasses import dataclass
from pathlib import Path
import sqlite3

from trading_x.types import CandidateGrade, Confidence, StrategyType


@dataclass(frozen=True, slots=True)
class PlanFixture:
    official_pre_close: float
    volume_min_abs_amount: float
    trade_date: str = "20260630"
    stop_price: float = 9.8
    volume_gate_enabled: bool = True
    vwap_above_confirm_seconds: int = 0
    strategy_type: str = StrategyType.B_CAPACITY_LEADER


def seed_b_candidate(db_path: Path, pre_close: float, limit_pre_close: float | None = None) -> None:
    official_limit_pre_close = pre_close if limit_pre_close is None else limit_pre_close
    with sqlite3.connect(db_path) as conn:
        conn.execute(
            "INSERT INTO stock_universe ("
            "ts_code, symbol, name, exchange, market, list_date, "
            "is_st, is_delisting_risk, included, excluded_reason"
            ") VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            ("300001.SZ", "300001", "容量龙", "SZSE", "创业板", "20200101", 0, 0, 1, None),
        )
        conn.execute(
            "INSERT INTO daily_quotes ("
            "trade_date, ts_code, open, high, low, close, pre_close, pct_chg, vol, amount"
            ") VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            ("20260630", "300001.SZ", 10.0, 10.8, 9.8, 10.2, pre_close, 2.0, 1000.0, 100000.0),
        )
        conn.execute(
            "INSERT INTO stk_limit_prices (trade_date, ts_code, pre_close, up_limit, down_limit) "
            "VALUES (?, ?, ?, ?, ?)",
            ("20260630", "300001.SZ", official_limit_pre_close, 11.0, 9.0),
        )
        conn.execute(
            "INSERT INTO candidates ("
            "trade_date, ts_code, strategy_type, candidate_grade, risk_pass, market_status, "
            "theme_name, theme_tags, theme_rank_today, theme_strength_score, theme_position, "
            "theme_confidence, event_confidence, liquidity_rank, leader_rank, breakout_rank, "
            "entry_reason, veto_items, buy_observation, abandon_conditions, max_chase_limit, "
            "structural_stop, suggested_position, max_loss, data_confidence"
            ") VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (
                "20260630",
                "300001.SZ",
                StrategyType.B_CAPACITY_LEADER,
                CandidateGrade.B_CORE,
                1,
                "NORMAL",
                "机器人",
                "机器人",
                1,
                88.0,
                "成交额第 1",
                Confidence.MEDIUM,
                Confidence.UNAVAILABLE,
                1.0,
                1.0,
                1.0,
                "结构突破",
                "无",
                "放量突破",
                "跌破平台",
                "不追高",
                "跌破低点",
                "10000",
                "500",
                Confidence.MEDIUM,
            ),
        )


def insert_plan(db_path: Path, fixture: PlanFixture) -> None:
    with sqlite3.connect(db_path) as conn:
        conn.execute(
            "INSERT INTO intraday_plans ("
            "trade_date, ts_code, name, strategy_type, allow_trade, plan_status, "
            "entry_low, entry_high, breakout_price, stop_price, max_stop_distance, "
            "max_position_cash, max_loss, official_pre_close, pre_close_source, "
            "vwap_active_after, vwap_above_confirm_seconds, volume_gate_enabled, "
            "volume_min_abs_amount, volume_same_window_multiplier, volume_ratio_0935, "
            "volume_ratio_0945, volume_ratio_1000, theme_name, theme_confidence, "
            "theme_strength_score, source_candidate_id, source_report_date, plan_json, "
            "system_version, created_at"
            ") VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (
                fixture.trade_date,
                "300001.SZ",
                "容量龙",
                fixture.strategy_type,
                1,
                "ACTIVE",
                10.0,
                13.0,
                11.0,
                fixture.stop_price,
                0.07,
                10000.0,
                500.0,
                fixture.official_pre_close,
                "fixture",
                "09:35:00",
                fixture.vwap_above_confirm_seconds,
                int(fixture.volume_gate_enabled),
                fixture.volume_min_abs_amount,
                1.3,
                0.03,
                0.05,
                0.08,
                "机器人",
                Confidence.MEDIUM,
                88.0,
                "300001.SZ:B_CAPACITY_LEADER",
                fixture.trade_date,
                "{}",
                "test",
                "2026-06-30T09:00:00",
            ),
        )


def write_replay_csv(path: Path, body: str) -> None:
    write_text(
        path,
        "trade_date,quote_time,ts_code,price,amount_since_open,volume_since_open,bar_high,bar_low\n"
        + body,
    )


def write_text(path: Path, text: str) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(text, encoding="utf-8")


def alert_rows(db_path: Path) -> list[tuple[str, str]]:
    with sqlite3.connect(db_path) as conn:
        rows = conn.execute(
            "SELECT alert_type, reason_code FROM intraday_alerts ORDER BY id"
        ).fetchall()
    return [(row[0], row[1]) for row in rows]
