from collections.abc import Sequence
from typing import Protocol

from trading_x.candidate_models import CandidateReport
from trading_x.types import DataCapabilityLevel


class ReportSnapshotView(Protocol):
    @property
    def trade_date(self) -> str:
        ...

    @property
    def market_status(self) -> str:
        ...

    @property
    def allow_new_position(self) -> bool:
        ...

    @property
    def data_capability(self) -> DataCapabilityLevel:
        ...

    @property
    def risk_blocks(self) -> Sequence[str]:
        ...

    @property
    def candidates(self) -> Sequence[CandidateReport]:
        ...


def render_markdown(snapshot: ReportSnapshotView) -> str:
    decision = "允许观察候选" if snapshot.allow_new_position else "禁止新开仓"
    risk_lines = "\n".join(f"- {item}" for item in snapshot.risk_blocks) or "- 无"
    candidate_lines = _render_candidates(snapshot)
    return (
        f"# AI 龙头盯盘日报 {snapshot.trade_date}\n\n"
        f"- 数据能力等级：{snapshot.data_capability}\n"
        f"- 市场状态：{snapshot.market_status}\n"
        f"- 交易结论：{decision}\n"
        f"- 候选数量：{len(snapshot.candidates)}\n\n"
        f"## 风控与否决\n\n{risk_lines}\n\n"
        f"## 候选池\n\n{candidate_lines}\n\n"
    )


def _render_candidates(snapshot: ReportSnapshotView) -> str:
    if not snapshot.candidates:
        reason = (
            "数据不足。"
            if snapshot.data_capability == DataCapabilityLevel.DEGRADED
            else "市场情绪弱或无满足风控/结构条件标的。"
        )
        return f"今日无符合纪律候选。\n\n禁买原因：{reason}"
    sections = []
    for index, candidate in enumerate(snapshot.candidates, start=1):
        sections.append(
            f"### {index}. {candidate.name}（{candidate.ts_code}）\n\n"
            f"- 策略类型：{candidate.strategy_type}\n"
            f"- 候选等级：{candidate.candidate_grade}\n"
            f"- 主线题材：{candidate.theme_name or 'unavailable'}\n"
            f"- 题材标签：{candidate.theme_tags or 'unmapped'}\n"
            f"- 题材今日排名：{candidate.theme_rank_today or 'unavailable'}\n"
            f"- 题材强度：{candidate.theme_strength_score or 'unavailable'}\n"
            f"- 题材内地位：{candidate.theme_position or 'unmapped'}\n"
            f"- 入池理由：{candidate.entry_reason}\n"
            f"- 否决项：{candidate.veto_items}\n"
            f"- 买入观察条件：{candidate.buy_observation}\n"
            f"- 放弃条件：{candidate.abandon_conditions}\n"
            f"- 最大追高限制：{candidate.max_chase_limit}\n"
            f"- 结构止损位：{candidate.structural_stop}\n"
            f"- 建议仓位：{candidate.suggested_position}\n"
            f"- 最大亏损：{candidate.max_loss}\n"
            f"- 数据置信度：{candidate.data_confidence}\n"
            f"- theme_confidence：{candidate.theme_confidence}\n"
            f"- event_confidence：{candidate.event_confidence}"
        )
    return "\n\n".join(sections)
