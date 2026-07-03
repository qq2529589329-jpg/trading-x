import sqlite3
from typing import Final

from trading_x.candidate_models import CandidateReport
from trading_x.types import Confidence, StrategyType


CONFIDENCE_SORT: Final[dict[str, float]] = {
    Confidence.HIGH: 3.0,
    Confidence.MEDIUM: 2.0,
    Confidence.LOW: 1.0,
    Confidence.UNAVAILABLE: 0.0,
}


def sort_candidates(
    candidates: list[CandidateReport],
    rows: list[sqlite3.Row],
) -> list[CandidateReport]:
    return sorted(candidates, key=lambda candidate: _sort_key(candidate, rows), reverse=True)


def _sort_key(
    candidate: CandidateReport,
    rows: list[sqlite3.Row],
) -> tuple[float, float, float, float, float]:
    row = next(row for row in rows if row[0] == candidate.ts_code)
    strategy_score = 2.0 if candidate.strategy_type == StrategyType.A_SPACE_LEADER else 1.0
    return (
        strategy_score,
        candidate.theme_strength_score or 0.0,
        CONFIDENCE_SORT.get(candidate.theme_confidence, 0.0),
        row[7],
        row[6],
    )
