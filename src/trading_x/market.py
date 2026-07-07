from dataclasses import dataclass
from pathlib import Path
import sqlite3

from trading_x.candidate_models import CandidateReport
from trading_x.types import Confidence, DataCapabilityLevel


@dataclass(frozen=True, slots=True)
class MarketEmotion:
    core_market_emotion_score: float
    normal_limit_up_count: int
    normal_limit_down_count: int
    normal_break_limit_rate: float
    normal_highest_board: int | None
    normal_limit_premium: float | None
    st_speculation_score: float
    st_limit_up_count: int
    st_limit_down_count: int
    st_highest_board: int | None


def market_emotion_for(db_path: Path, trade_date: str) -> MarketEmotion:
    with sqlite3.connect(db_path) as conn:
        row = conn.execute(
            "SELECT "
            "SUM(CASE WHEN s.included = 1 AND s.is_st = 0 AND s.is_delisting_risk = 0 "
            "AND e.limit_type IN ('UP', 'LIMIT_UP', '涨停') AND e.is_limit_close = 1 THEN 1 ELSE 0 END), "
            "SUM(CASE WHEN s.included = 1 AND s.is_st = 0 AND s.is_delisting_risk = 0 "
            "AND e.limit_type IN ('DOWN', 'LIMIT_DOWN', '跌停') AND e.is_limit_close = 1 THEN 1 ELSE 0 END), "
            "SUM(CASE WHEN s.included = 1 AND s.is_st = 0 AND s.is_delisting_risk = 0 "
            "AND e.limit_type IN ('UP', 'LIMIT_UP', '涨停') AND e.limit_break_count > 0 THEN 1 ELSE 0 END), "
            "AVG(CASE WHEN s.included = 1 AND s.is_st = 0 AND s.is_delisting_risk = 0 "
            "AND e.limit_type IN ('UP', 'LIMIT_UP', '涨停') AND e.is_limit_close = 1 THEN d.pct_chg END), "
            "SUM(CASE WHEN s.included = 1 AND s.is_st = 1 "
            "AND e.limit_type IN ('UP', 'LIMIT_UP', '涨停') AND e.is_limit_close = 1 THEN 1 ELSE 0 END), "
            "SUM(CASE WHEN s.included = 1 AND s.is_st = 1 "
            "AND e.limit_type IN ('DOWN', 'LIMIT_DOWN', '跌停') AND e.is_limit_close = 1 THEN 1 ELSE 0 END) "
            "FROM limit_events e "
            "JOIN stock_universe s ON s.ts_code = e.ts_code "
            "LEFT JOIN daily_quotes d ON d.ts_code = e.ts_code AND d.trade_date = e.trade_date "
            "WHERE e.trade_date = ?",
            (trade_date,),
        ).fetchone()
    normal_up = _int_value(row[0])
    normal_down = _int_value(row[1])
    normal_breaks = _int_value(row[2])
    st_up = _int_value(row[4])
    st_down = _int_value(row[5])
    break_rate = round(normal_breaks / normal_up, 4) if normal_up else 0.0
    return MarketEmotion(
        core_market_emotion_score=round((normal_up * 10.0) - (normal_down * 15.0) - (break_rate * 20.0), 2),
        normal_limit_up_count=normal_up,
        normal_limit_down_count=normal_down,
        normal_break_limit_rate=break_rate,
        normal_highest_board=None,
        normal_limit_premium=_float_or_none(row[3]),
        st_speculation_score=round((st_up * 10.0) - (st_down * 10.0), 2),
        st_limit_up_count=st_up,
        st_limit_down_count=st_down,
        st_highest_board=None,
    )


def market_status(
    level: DataCapabilityLevel,
    candidates: list[CandidateReport],
) -> str:
    if level == DataCapabilityLevel.DEGRADED:
        return "数据不足"
    if candidates:
        return "观察"
    return "弱"


def report_theme_confidence(
    candidates: list[CandidateReport],
    unavailable_apis: set[str],
) -> Confidence:
    if candidates:
        return Confidence(candidates[0].theme_confidence)
    return Confidence.LOW if "limit_cpt_list" in unavailable_apis else Confidence.MEDIUM


def _int_value(value: int | float | str | None) -> int:
    return int(value or 0)


def _float_or_none(value: int | float | str | None) -> float | None:
    if value is None:
        return None
    return round(float(value), 2)
