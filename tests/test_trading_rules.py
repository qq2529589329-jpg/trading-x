from trading_x.trading_rules import TradingRuleQuery, TradingRuleRegistry


def test_mainboard_st_limit_ratio_changes_when_20260706_rule_starts() -> None:
    registry = TradingRuleRegistry()

    before = registry.rule_for(TradingRuleQuery(trade_date="20260703", board="主板", is_st=True, is_etf=False))
    after = registry.rule_for(TradingRuleQuery(trade_date="20260706", board="主板", is_st=True, is_etf=False))

    assert before.price_limit_ratio == 0.05
    assert before.rule_version == "pre_20260706"
    assert after.price_limit_ratio == 0.10
    assert after.rule_version == "20260706"


def test_post_close_fixed_price_window_is_observation_only_after_20260706() -> None:
    registry = TradingRuleRegistry()

    assert registry.is_post_close_fixed_price_time("20260706", "15:10:00")
    assert not registry.is_post_close_fixed_price_time("20260703", "15:10:00")
    assert not registry.is_post_close_fixed_price_time("20260706", "15:00:00")