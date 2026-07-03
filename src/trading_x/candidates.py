from pathlib import Path
import sqlite3

from trading_x.candidate_explanations import (
    a_space_leader_explanation,
    b_capacity_leader_explanation,
)
from trading_x.candidate_filters import is_capacity_breakout, is_limit_close
from trading_x.candidate_models import CandidateReport, CandidateTheme
from trading_x.candidate_sorting import sort_candidates
from trading_x.candidate_storage import persist_candidates
from trading_x.types import CandidateGrade, Confidence, DataCapabilityLevel, StrategyType


MIN_AMOUNT = 100000.0


def select_candidates(
    db_path: Path,
    trade_date: str,
    level: DataCapabilityLevel,
    unavailable_apis: set[str],
) -> list[CandidateReport]:
    with sqlite3.connect(db_path) as conn:
        conn.execute("DELETE FROM candidates WHERE trade_date = ?", (trade_date,))
        if level == DataCapabilityLevel.DEGRADED:
            return []
        themes = _load_themes(conn, trade_date)
        rows = conn.execute(
            "SELECT s.ts_code, s.name, d.open, d.high, d.low, d.close, d.pct_chg, "
            "d.amount, b.turnover_rate, b.volume_ratio, b.circ_mv, l.up_limit, "
            "e.first_limit_time, e.limit_break_count, e.event_confidence "
            "FROM stock_universe s "
            "JOIN daily_quotes d ON d.ts_code = s.ts_code AND d.trade_date = ? "
            "JOIN daily_basic b ON b.ts_code = s.ts_code AND b.trade_date = ? "
            "JOIN stk_limit_prices l ON l.ts_code = s.ts_code AND l.trade_date = ? "
            "LEFT JOIN limit_events e ON e.ts_code = s.ts_code "
            "AND e.trade_date = ? AND e.limit_type IN ('UP', 'LIMIT_UP', '涨停') "
            "WHERE s.included = 1 AND s.is_st = 0 AND s.is_delisting_risk = 0 "
            "AND d.amount >= ?",
            (trade_date, trade_date, trade_date, trade_date, MIN_AMOUNT),
        ).fetchall()
        candidates = _build_candidates(rows, themes, unavailable_apis, level)
        candidates = candidates[:5]
        persist_candidates(conn, trade_date, candidates)
        return candidates


def _load_themes(conn: sqlite3.Connection, trade_date: str) -> dict[str, CandidateTheme]:
    rows = conn.execute(
        "WITH ranked_themes AS ("
        "SELECT theme_name, theme_confidence, theme_strength_score, "
        "RANK() OVER (ORDER BY theme_strength_score DESC, theme_name) AS theme_rank "
        "FROM theme_daily_strength WHERE trade_date = ?"
        ") "
        "SELECT m.ts_code, rt.theme_name, m.theme_tags, rt.theme_confidence, "
        "rt.theme_strength_score, rt.theme_rank, "
        "RANK() OVER (PARTITION BY m.theme_primary ORDER BY d.amount DESC) AS amount_rank, "
        "RANK() OVER (PARTITION BY m.theme_primary ORDER BY d.pct_chg DESC) AS pct_rank "
        "FROM theme_members m "
        "JOIN ranked_themes rt ON rt.theme_name = m.theme_primary "
        "LEFT JOIN daily_quotes d ON d.ts_code = m.ts_code AND d.trade_date = ?",
        (trade_date, trade_date),
    ).fetchall()
    if rows:
        return {
            row[0]: CandidateTheme(
                name=row[1],
                tags=row[2],
                confidence=row[3] or Confidence.LOW,
                strength_score=row[4],
                rank_today=row[5],
                position=f"成交额第 {row[6]}，涨幅第 {row[7]}",
            )
            for row in rows
        }
    rows = conn.execute(
        "SELECT theme_name, strength_level, theme_confidence, leading_stock, reason "
        "FROM theme_strength WHERE trade_date = ? "
        "ORDER BY limit_count DESC, candidate_count DESC, theme_name",
        (trade_date,),
    ).fetchall()
    return {
        row[3]: CandidateTheme(
            name=row[0],
            tags=None,
            confidence=row[2] or Confidence.LOW,
            strength_score=None,
            rank_today=None,
            position=None,
        )
        for row in rows
        if row[3]
    }


def _build_candidates(
    rows: list[sqlite3.Row],
    themes: dict[str, CandidateTheme],
    unavailable_apis: set[str],
    level: DataCapabilityLevel,
) -> list[CandidateReport]:
    candidates: list[CandidateReport] = []
    for row in rows:
        if is_limit_close(close=row[5], up_limit=row[11]):
            candidates.append(_a_candidate(row, themes, unavailable_apis, level))
        elif is_capacity_breakout(row):
            candidates.append(_b_candidate(row, themes, unavailable_apis, level))
    return sort_candidates(candidates, rows)


def _a_candidate(
    row: sqlite3.Row,
    themes: dict[str, CandidateTheme],
    unavailable_apis: set[str],
    level: DataCapabilityLevel,
) -> CandidateReport:
    event_confidence = row[14] or Confidence.LOW
    is_strong_event = event_confidence == Confidence.HIGH and bool(row[12]) and row[13] is not None
    theme = _theme_for(row[0], themes)
    explanation = a_space_leader_explanation(low=row[4], is_strong_event=is_strong_event)
    return CandidateReport(
        ts_code=row[0],
        name=row[1],
        strategy_type=StrategyType.A_SPACE_LEADER,
        candidate_grade=CandidateGrade.A_STRONG if is_strong_event else CandidateGrade.A_LITE,
        theme_name=theme.name if theme is not None else None,
        theme_tags=theme.tags if theme is not None else None,
        theme_rank_today=theme.rank_today if theme is not None else None,
        theme_strength_score=theme.strength_score if theme is not None else None,
        theme_position=theme.position if theme is not None else None,
        entry_reason=explanation.entry_reason,
        veto_items=explanation.veto_items,
        buy_observation=explanation.buy_observation,
        abandon_conditions=explanation.abandon_conditions,
        max_chase_limit=explanation.max_chase_limit,
        structural_stop=explanation.structural_stop,
        suggested_position=explanation.suggested_position,
        max_loss=explanation.max_loss,
        data_confidence=_data_confidence(level),
        theme_confidence=_theme_confidence(theme, unavailable_apis),
        event_confidence=event_confidence,
    )


def _b_candidate(
    row: sqlite3.Row,
    themes: dict[str, CandidateTheme],
    unavailable_apis: set[str],
    level: DataCapabilityLevel,
) -> CandidateReport:
    theme = _theme_for(row[0], themes)
    explanation = b_capacity_leader_explanation(low=row[4])
    return CandidateReport(
        ts_code=row[0],
        name=row[1],
        strategy_type=StrategyType.B_CAPACITY_LEADER,
        candidate_grade=CandidateGrade.B_CORE,
        theme_name=theme.name if theme is not None else None,
        theme_tags=theme.tags if theme is not None else None,
        theme_rank_today=theme.rank_today if theme is not None else None,
        theme_strength_score=theme.strength_score if theme is not None else None,
        theme_position=theme.position if theme is not None else None,
        entry_reason=explanation.entry_reason,
        veto_items=explanation.veto_items,
        buy_observation=explanation.buy_observation,
        abandon_conditions=explanation.abandon_conditions,
        max_chase_limit=explanation.max_chase_limit,
        structural_stop=explanation.structural_stop,
        suggested_position=explanation.suggested_position,
        max_loss=explanation.max_loss,
        data_confidence=_data_confidence(level),
        theme_confidence=_theme_confidence(theme, unavailable_apis),
        event_confidence=Confidence.UNAVAILABLE,
        plan_entry_low=round(float(row[5]), 2),
        plan_entry_high=round(float(row[3]) * 1.05, 2),
        plan_breakout_price=round(float(row[3]), 2),
        plan_stop_price=round(float(row[4]), 2),
        plan_max_position_cash=10000.0,
        plan_max_loss=500.0,
    )


def _theme_for(ts_code: str, themes: dict[str, CandidateTheme]) -> CandidateTheme | None:
    return themes.get(ts_code)


def _theme_confidence(theme: CandidateTheme | None, unavailable_apis: set[str]) -> str:
    if theme is not None:
        return theme.confidence
    return Confidence.LOW if "limit_cpt_list" in unavailable_apis else Confidence.MEDIUM


def _data_confidence(level: DataCapabilityLevel) -> str:
    return Confidence.HIGH if level == DataCapabilityLevel.FULL else Confidence.MEDIUM
