import sqlite3

from trading_x.candidate_models import CandidateReport


def persist_candidates(
    conn: sqlite3.Connection,
    trade_date: str,
    candidates: list[CandidateReport],
) -> None:
    conn.executemany(
        "INSERT INTO candidates ("
        "trade_date, ts_code, strategy_type, candidate_grade, risk_pass, market_status, "
        "theme_name, theme_tags, theme_rank_today, theme_strength_score, "
        "theme_position, theme_confidence, event_confidence, liquidity_rank, leader_rank, "
        "breakout_rank, entry_reason, veto_items, buy_observation, abandon_conditions, "
        "max_chase_limit, structural_stop, suggested_position, max_loss, data_confidence"
        ") VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?) "
        "ON CONFLICT(trade_date, ts_code, strategy_type) DO UPDATE SET "
        "candidate_grade = excluded.candidate_grade, risk_pass = excluded.risk_pass, "
        "market_status = excluded.market_status, theme_name = excluded.theme_name, "
        "theme_tags = excluded.theme_tags, theme_rank_today = excluded.theme_rank_today, "
        "theme_strength_score = excluded.theme_strength_score, "
        "theme_position = excluded.theme_position, theme_confidence = excluded.theme_confidence, "
        "event_confidence = excluded.event_confidence, entry_reason = excluded.entry_reason, "
        "veto_items = excluded.veto_items, buy_observation = excluded.buy_observation, "
        "abandon_conditions = excluded.abandon_conditions, max_chase_limit = excluded.max_chase_limit, "
        "structural_stop = excluded.structural_stop, suggested_position = excluded.suggested_position, "
        "max_loss = excluded.max_loss, data_confidence = excluded.data_confidence",
        [
            (
                trade_date,
                candidate.ts_code,
                candidate.strategy_type,
                candidate.candidate_grade,
                1,
                "观察",
                candidate.theme_name,
                candidate.theme_tags,
                candidate.theme_rank_today,
                candidate.theme_strength_score,
                candidate.theme_position,
                candidate.theme_confidence,
                candidate.event_confidence,
                None,
                None,
                None,
                candidate.entry_reason,
                candidate.veto_items,
                candidate.buy_observation,
                candidate.abandon_conditions,
                candidate.max_chase_limit,
                candidate.structural_stop,
                candidate.suggested_position,
                candidate.max_loss,
                candidate.data_confidence,
            )
            for candidate in candidates
        ],
    )
