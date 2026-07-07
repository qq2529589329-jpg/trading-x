from dataclasses import dataclass
from typing import Final

RULE_20260706_EFFECTIVE_DATE: Final = "20260706"
POST_CLOSE_START: Final = "15:05:00"
POST_CLOSE_END: Final = "15:30:00"
MAINBOARD_ST_LIMIT_BEFORE_20260706: Final = 0.05
MAINBOARD_STANDARD_LIMIT: Final = 0.10
GROWTH_BOARD_LIMIT: Final = 0.20
GROWTH_BOARDS: Final = frozenset({"创业板", "科创板"})


@dataclass(frozen=True, slots=True)
class TradingRuleQuery:
    trade_date: str
    board: str
    is_st: bool
    is_etf: bool


@dataclass(frozen=True, slots=True)
class TradingRule:
    trade_date: str
    board: str
    is_st: bool
    is_etf: bool
    price_limit_ratio: float
    after_hours_enabled: bool
    post_close_trade_start: str
    post_close_trade_end: str
    rule_version: str


@dataclass(frozen=True, slots=True)
class NewRuleCompatibility:
    trading_rule_version: str
    mainboard_st_limit_ratio: float
    post_close_fixed_price_scope: str
    normal_emotion_excludes_st: bool
    data_rule_match: bool
    post_close_data_available: bool
    system_action: str


@dataclass(frozen=True, slots=True)
class TradingRuleRegistry:
    def rule_for(self, query: TradingRuleQuery) -> TradingRule:
        active = _is_20260706_rule_active(query.trade_date)
        return TradingRule(
            trade_date=query.trade_date,
            board=query.board,
            is_st=query.is_st,
            is_etf=query.is_etf,
            price_limit_ratio=_price_limit_ratio(board=query.board, is_st=query.is_st, active=active),
            after_hours_enabled=active,
            post_close_trade_start=POST_CLOSE_START,
            post_close_trade_end=POST_CLOSE_END,
            rule_version="20260706" if active else "pre_20260706",
        )

    def is_post_close_fixed_price_time(self, trade_date: str, quote_time: str) -> bool:
        return _is_20260706_rule_active(trade_date) and POST_CLOSE_START <= quote_time <= POST_CLOSE_END


TRADING_RULE_REGISTRY: Final = TradingRuleRegistry()


def new_rule_compatibility_for(
    trade_date: str,
    *,
    data_rule_match: bool = True,
    post_close_data_available: bool = False,
) -> NewRuleCompatibility:
    mainboard_st_rule = TRADING_RULE_REGISTRY.rule_for(
        TradingRuleQuery(trade_date=trade_date, board="主板", is_st=True, is_etf=False),
    )
    return NewRuleCompatibility(
        trading_rule_version=mainboard_st_rule.rule_version,
        mainboard_st_limit_ratio=mainboard_st_rule.price_limit_ratio,
        post_close_fixed_price_scope="ALL_A_SHARES_ETF" if mainboard_st_rule.after_hours_enabled else "LIMITED_OR_UNAVAILABLE",
        normal_emotion_excludes_st=True,
        data_rule_match=data_rule_match,
        post_close_data_available=post_close_data_available,
        system_action="ALLOW_REPORT" if data_rule_match else "DEGRADE_TO_OBSERVATION",
    )


def is_post_close_fixed_price_time(trade_date: str, quote_time: str) -> bool:
    return TRADING_RULE_REGISTRY.is_post_close_fixed_price_time(trade_date, quote_time)


def rule_regime_for(trade_date: str) -> str:
    return "post_20260706" if _is_20260706_rule_active(trade_date) else "pre_20260706"


def _is_20260706_rule_active(trade_date: str) -> bool:
    return len(trade_date) == 8 and trade_date.isdigit() and trade_date >= RULE_20260706_EFFECTIVE_DATE


def _price_limit_ratio(*, board: str, is_st: bool, active: bool) -> float:
    if board in GROWTH_BOARDS:
        return GROWTH_BOARD_LIMIT
    if is_st and not active:
        return MAINBOARD_ST_LIMIT_BEFORE_20260706
    return MAINBOARD_STANDARD_LIMIT