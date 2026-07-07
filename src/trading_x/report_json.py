from typing import TypedDict

from trading_x.candidate_models import CandidateReport
from trading_x.market import MarketEmotion
from trading_x.trading_rules import NewRuleCompatibility


class CandidateJson(TypedDict):
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
    plan_entry_low: float | None
    plan_entry_high: float | None
    plan_breakout_price: float | None
    plan_stop_price: float | None
    plan_max_position_cash: float | None
    plan_max_loss: float | None


class MarketEmotionJson(TypedDict):
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


class NewRuleCompatibilityJson(TypedDict):
    trading_rule_version: str
    mainboard_st_limit_ratio: float
    post_close_fixed_price_scope: str
    normal_emotion_excludes_st: bool
    data_rule_match: bool
    post_close_data_available: bool
    system_action: str


def candidate_json(candidate: CandidateReport) -> CandidateJson:
    return {
        "ts_code": candidate.ts_code,
        "name": candidate.name,
        "strategy_type": candidate.strategy_type,
        "candidate_grade": candidate.candidate_grade,
        "theme_name": candidate.theme_name,
        "theme_tags": candidate.theme_tags,
        "theme_rank_today": candidate.theme_rank_today,
        "theme_strength_score": candidate.theme_strength_score,
        "theme_position": candidate.theme_position,
        "entry_reason": candidate.entry_reason,
        "veto_items": candidate.veto_items,
        "buy_observation": candidate.buy_observation,
        "abandon_conditions": candidate.abandon_conditions,
        "max_chase_limit": candidate.max_chase_limit,
        "structural_stop": candidate.structural_stop,
        "suggested_position": candidate.suggested_position,
        "max_loss": candidate.max_loss,
        "data_confidence": candidate.data_confidence,
        "theme_confidence": candidate.theme_confidence,
        "event_confidence": candidate.event_confidence,
        "plan_entry_low": candidate.plan_entry_low,
        "plan_entry_high": candidate.plan_entry_high,
        "plan_breakout_price": candidate.plan_breakout_price,
        "plan_stop_price": candidate.plan_stop_price,
        "plan_max_position_cash": candidate.plan_max_position_cash,
        "plan_max_loss": candidate.plan_max_loss,
    }


def market_emotion_json(item: MarketEmotion) -> MarketEmotionJson:
    return {
        "core_market_emotion_score": item.core_market_emotion_score,
        "normal_limit_up_count": item.normal_limit_up_count,
        "normal_limit_down_count": item.normal_limit_down_count,
        "normal_break_limit_rate": item.normal_break_limit_rate,
        "normal_highest_board": item.normal_highest_board,
        "normal_limit_premium": item.normal_limit_premium,
        "st_speculation_score": item.st_speculation_score,
        "st_limit_up_count": item.st_limit_up_count,
        "st_limit_down_count": item.st_limit_down_count,
        "st_highest_board": item.st_highest_board,
    }


def new_rule_compatibility_json(item: NewRuleCompatibility) -> NewRuleCompatibilityJson:
    return {
        "trading_rule_version": item.trading_rule_version,
        "mainboard_st_limit_ratio": item.mainboard_st_limit_ratio,
        "post_close_fixed_price_scope": item.post_close_fixed_price_scope,
        "normal_emotion_excludes_st": item.normal_emotion_excludes_st,
        "data_rule_match": item.data_rule_match,
        "post_close_data_available": item.post_close_data_available,
        "system_action": item.system_action,
    }