from collections.abc import Sequence
from typing import Protocol

from trading_x.candidate_models import CandidateReport
from trading_x.types import DataCapabilityLevel


class NewRuleCompatibilityView(Protocol):
    @property
    def trading_rule_version(self) -> str:
        ...

    @property
    def mainboard_st_limit_ratio(self) -> float:
        ...

    @property
    def post_close_fixed_price_scope(self) -> str:
        ...

    @property
    def normal_emotion_excludes_st(self) -> bool:
        ...

    @property
    def data_rule_match(self) -> bool:
        ...

    @property
    def post_close_data_available(self) -> bool:
        ...

    @property
    def system_action(self) -> str:
        ...


class MarketEmotionView(Protocol):
    @property
    def core_market_emotion_score(self) -> float:
        ...

    @property
    def normal_limit_up_count(self) -> int:
        ...

    @property
    def normal_limit_down_count(self) -> int:
        ...

    @property
    def normal_break_limit_rate(self) -> float:
        ...

    @property
    def normal_highest_board(self) -> int | None:
        ...

    @property
    def normal_limit_premium(self) -> float | None:
        ...

    @property
    def st_speculation_score(self) -> float:
        ...

    @property
    def st_limit_up_count(self) -> int:
        ...

    @property
    def st_limit_down_count(self) -> int:
        ...

    @property
    def st_highest_board(self) -> int | None:
        ...


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

    @property
    def new_rule_compatibility(self) -> NewRuleCompatibilityView:
        ...

    @property
    def market_emotion(self) -> MarketEmotionView:
        ...


def render_markdown(snapshot: ReportSnapshotView) -> str:
    decision = "允许观察候选" if snapshot.allow_new_position else "禁止新开仓"
    risk_lines = "\n".join(f"- {item}" for item in snapshot.risk_blocks) or "- 无"
    compatibility_lines = _render_new_rule_compatibility(snapshot.new_rule_compatibility)
    emotion_lines = _render_market_emotion(snapshot.market_emotion)
    candidate_lines = _render_candidates(snapshot)
    return (
        f"# AI 龙头盯盘日报 {snapshot.trade_date}\n\n"
        f"- 数据能力等级：{snapshot.data_capability}\n"
        f"- 市场状态：{snapshot.market_status}\n"
        f"- 交易结论：{decision}\n"
        f"- 候选数量：{len(snapshot.candidates)}\n\n"
        f"## 新规兼容检查\n\n{compatibility_lines}\n\n"
        f"{emotion_lines}\n\n"
        f"## 风控与否决\n\n{risk_lines}\n\n"
        f"## 候选池\n\n{candidate_lines}\n\n"
    )


def _render_new_rule_compatibility(item: NewRuleCompatibilityView) -> str:
    st_limit = f"{item.mainboard_st_limit_ratio:.0%}"
    scope = "全部 A 股 / ETF" if item.post_close_fixed_price_scope == "ALL_A_SHARES_ETF" else "未全量启用"
    data_rule_match = "是" if item.data_rule_match else "否"
    excludes_st = "是" if item.normal_emotion_excludes_st else "否"
    post_close_data = "available" if item.post_close_data_available else "unavailable"
    amount_basis = "confirmed regular/post-close split" if item.post_close_data_available else "可能包含盘后固定价格成交"
    system_action = "允许正常生成日报" if item.system_action == "ALLOW_REPORT" else "降级为观察"
    return (
        f"- 交易规则版本：{item.trading_rule_version}\n"
        f"- 主板 ST 涨跌幅：{st_limit}\n"
        f"- 盘后固定价格交易：{scope}\n"
        f"- 普通股情绪是否剔除 ST：{excludes_st}\n"
        f"- 数据源涨跌停价是否匹配新规：{data_rule_match}\n"
        f"- 盘后固定价格数据：{post_close_data}\n"
        f"- 成交额口径：{amount_basis}\n"
        f"- 系统动作：{system_action}"
    )


def _render_market_emotion(item: MarketEmotionView) -> str:
    normal_highest = item.normal_highest_board if item.normal_highest_board is not None else "unavailable"
    normal_premium = item.normal_limit_premium if item.normal_limit_premium is not None else "unavailable"
    st_highest = item.st_highest_board if item.st_highest_board is not None else "unavailable"
    return (
        "## 普通股短线情绪\n\n"
        f"- core_market_emotion_score：{item.core_market_emotion_score}\n"
        f"- normal_limit_up_count：{item.normal_limit_up_count}\n"
        f"- normal_limit_down_count：{item.normal_limit_down_count}\n"
        f"- normal_break_limit_rate：{item.normal_break_limit_rate}\n"
        f"- normal_highest_board：{normal_highest}\n"
        f"- normal_limit_premium：{normal_premium}\n\n"
        "## ST 投机情绪\n\n"
        f"- st_speculation_score：{item.st_speculation_score}\n"
        f"- st_limit_up_count：{item.st_limit_up_count}\n"
        f"- st_limit_down_count：{item.st_limit_down_count}\n"
        f"- st_highest_board：{st_highest}\n"
        "- 交易结论：不因 ST 活跃提高普通龙头战法仓位"
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
