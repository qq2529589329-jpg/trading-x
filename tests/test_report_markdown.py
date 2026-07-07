from trading_x.market import MarketEmotion
from trading_x.report_markdown import render_markdown
from trading_x.reports import ReportSnapshot
from trading_x.trading_rules import new_rule_compatibility_for
from trading_x.types import Confidence, DataCapabilityLevel


def test_render_markdown_states_no_candidate_ban_reason() -> None:
    snapshot = ReportSnapshot(
        trade_date="20260701",
        system_version="v1.0",
        market_status="退潮",
        allow_new_position=False,
        data_capability=DataCapabilityLevel.BASIC,
        available_apis=(),
        unavailable_apis=(),
        risk_blocks=("市场情绪弱；禁止新开仓。",),
        candidates=[],
        theme_confidence=Confidence.LOW,
        market_emotion=MarketEmotion(
            core_market_emotion_score=0.0,
            normal_limit_up_count=0,
            normal_limit_down_count=0,
            normal_break_limit_rate=0.0,
            normal_highest_board=None,
            normal_limit_premium=None,
            st_speculation_score=0.0,
            st_limit_up_count=0,
            st_limit_down_count=0,
            st_highest_board=None,
        ),
        new_rule_compatibility=new_rule_compatibility_for("20260701"),
    )

    markdown = render_markdown(snapshot)

    assert "今日无符合纪律候选" in markdown
    assert "禁买原因：市场情绪弱或无满足风控/结构条件标的。" in markdown
