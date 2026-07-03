from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class CandidateReport:
    ts_code: str
    name: str
    strategy_type: str
    candidate_grade: str
    theme_name: str | None
    theme_tags: str | None
    theme_rank_today: int | None
    theme_strength_score: float | None
    theme_position: str | None
    entry_reason: str
    veto_items: str
    buy_observation: str
    abandon_conditions: str
    max_chase_limit: str
    structural_stop: str
    suggested_position: str
    max_loss: str
    data_confidence: str
    theme_confidence: str
    event_confidence: str
    plan_entry_low: float | None = None
    plan_entry_high: float | None = None
    plan_breakout_price: float | None = None
    plan_stop_price: float | None = None
    plan_max_position_cash: float | None = None
    plan_max_loss: float | None = None


@dataclass(frozen=True, slots=True)
class CandidateTheme:
    name: str
    tags: str | None
    rank_today: int | None
    strength_score: float | None
    position: str | None
    confidence: str
