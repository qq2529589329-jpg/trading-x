from trading_x.report_markdown import render_markdown
from trading_x.reports import ReportSnapshot
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
    )

    markdown = render_markdown(snapshot)

    assert "今日无符合纪律候选" in markdown
    assert "禁买原因：市场情绪弱或无满足风控/结构条件标的。" in markdown
