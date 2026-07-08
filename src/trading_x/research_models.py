from dataclasses import dataclass
from pathlib import Path
from typing import Final

from trading_x.types import StrategyType


DATA_SOURCE: Final = "DAILY_PROXY"


@dataclass(frozen=True, slots=True)
class RegimeClassificationRequest:
    start_date: str
    end_date: str
    method_version: str


@dataclass(frozen=True, slots=True)
class RegimeClassificationResult:
    start_date: str
    end_date: str
    classified_count: int
    proxy_count: int


@dataclass(frozen=True, slots=True)
class ResearchBacktestRequest:
    start_date: str
    end_date: str
    strategy_type: StrategyType
    config_version: str
    report_dir: Path


@dataclass(frozen=True, slots=True)
class ResearchBacktestResult:
    run_id: str
    start_date: str
    end_date: str
    candidate_count: int
    order_count: int
    trade_count: int
    total_return: float
    status: str
    report_path: Path


@dataclass(frozen=True, slots=True)
class ResearchDateRange:
    start_date: str
    end_date: str


@dataclass(frozen=True, slots=True)
class DailyRegimeStats:
    trade_date: str
    avg_pct_chg: float
    total_amount: float
    limit_up_count: int
    limit_down_count: int
    candidate_count: int


@dataclass(frozen=True, slots=True)
class BacktestSummary:
    run_id: str
    date_range: ResearchDateRange
    strategy_type: StrategyType
    config_version: str
    report_dir: Path
    candidate_count: int
    order_count: int
    trade_count: int
    win_count: int
    loss_count: int
    total_return: float
    reason_counts: tuple[tuple[str, int], ...]
    status: str = "SUCCESS"

    @property
    def report_path(self) -> Path:
        return self.report_dir / "walk_forward_summary.md"
