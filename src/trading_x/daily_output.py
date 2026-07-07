from pathlib import Path

from trading_x.reports import ReportSnapshot
from trading_x.theme_models import ThemeCoverage
from trading_x.types import DataCapabilityLevel, StrategyType


def print_daily_failure(
    trade_date: str,
    level: DataCapabilityLevel,
    reason: str,
    latest_complete_date: str | None = None,
) -> None:
    print(f"交易日：{trade_date}")
    print("数据状态：FAILED")
    print(f"数据能力：{level}")
    print(f"主要原因：{reason}")
    if latest_complete_date is not None:
        print(f"最近完整交易日：{latest_complete_date}")
        print(f"建议命令：uv run python -m trading_x daily --date {latest_complete_date}")


def print_daily_summary(snapshot: ReportSnapshot, report_dir: Path, coverage: ThemeCoverage) -> None:
    themes = sorted({candidate.theme_name for candidate in snapshot.candidates if candidate.theme_name})
    a_count = sum(1 for candidate in snapshot.candidates if candidate.strategy_type == StrategyType.A_SPACE_LEADER)
    b_count = sum(1 for candidate in snapshot.candidates if candidate.strategy_type == StrategyType.B_CAPACITY_LEADER)
    print(f"交易日：{snapshot.trade_date}")
    print("数据状态：OK")
    print(f"数据能力：{snapshot.data_capability}")
    print(f"市场状态：{snapshot.market_status}")
    print(f"允许交易：{'是' if snapshot.allow_new_position else '否'}")
    print(f"主线题材：{'、'.join(themes) if themes else 'unavailable'}")
    print(f"候选数量：{len(snapshot.candidates)}")
    print(f"A类候选：{a_count}")
    print(f"B类候选：{b_count}")
    print(f"题材覆盖率：{_ratio_text(coverage.mapped_stock_count, coverage.stock_total)}")
    print(f"候选题材覆盖率：{_ratio_text(coverage.candidate_mapped_count, coverage.candidate_total)}")
    print(f"未覆盖候选：{','.join(coverage.unmapped_candidates) if coverage.unmapped_candidates else '无'}")
    if not snapshot.candidates:
        reason = snapshot.risk_blocks[0] if snapshot.risk_blocks else "市场情绪弱或无满足风控/结构条件标的"
        print("结论：今日无符合纪律候选")
        print(f"主要原因：{reason}")
    print(f"报告 Markdown：{report_dir / f'{snapshot.trade_date}_report.md'}")
    print("报告 HTML：未生成")
    print(f"报告 JSON：{report_dir / f'{snapshot.trade_date}_report.json'}")
    print("验收命令：uv run python -m trading_x acceptance --last-complete-n 10")


def _ratio_text(part: int, total: int) -> str:
    if total == 0:
        return f"{part}/{total} (unavailable)"
    return f"{part}/{total} ({part / total:.1%})"
