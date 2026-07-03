from dataclasses import dataclass


@dataclass(frozen=True, slots=True)
class CandidateExplanation:
    entry_reason: str
    veto_items: str
    buy_observation: str
    abandon_conditions: str
    max_chase_limit: str
    structural_stop: str
    suggested_position: str
    max_loss: str


def a_space_leader_explanation(low: float, is_strong_event: bool) -> CandidateExplanation:
    return CandidateExplanation(
        entry_reason="收盘涨停且事件数据确认封板质量。"
        if is_strong_event
        else "收盘涨停，具备空间板观察资格。",
        veto_items="P0 风控通过；若同梯队退潮或开盘核按钮则否决。",
        buy_observation="明日只观察弱转强或分歧回封。",
        abandon_conditions="不能维持空间地位、同梯队高位股明显转弱或市场情绪转弱则放弃。",
        max_chase_limit="不追高超过计划买点 3%。",
        structural_stop=f"跌破当日低点 {low:.2f} 或回落平台内。",
        suggested_position="试错仓 10%-20%。",
        max_loss="单笔最大亏损控制在总资金 1% 内。",
    )


def b_capacity_leader_explanation(low: float) -> CandidateExplanation:
    return CandidateExplanation(
        entry_reason="放量上涨且未触及涨停，具备容量趋势龙观察资格。",
        veto_items="P0 风控通过；若板块前排掉队或跌回平台则否决。",
        buy_observation="明日只观察放量突破或回踩承接。",
        abandon_conditions="高开超过 7%、冲高回落、板块前排掉队或跌回平台内则放弃。",
        max_chase_limit="不追高超过计划买点 5%。",
        structural_stop=f"跌破当日低点 {low:.2f} 或突破 K 线实体下沿。",
        suggested_position="观察仓 10%-20%。",
        max_loss="单笔最大亏损控制在总资金 1% 内。",
    )
