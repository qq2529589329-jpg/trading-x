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
class BacktestTrustAuditRequest:
    run_id: str | None
    report_dir: Path


@dataclass(frozen=True, slots=True)
class AdjFactorSyncRequest:
    run_id: str | None


@dataclass(frozen=True, slots=True)
class AdjFactorSyncResult:
    run_id: str
    missing_before: int
    inserted_count: int
    missing_after: int


@dataclass(frozen=True, slots=True)
class BacktestTrustAuditResult:
    run_id: str
    status: str
    issue_count: int
    report_path: Path


@dataclass(frozen=True, slots=True)
class ResearchDateRange:
    start_date: str
    end_date: str


@dataclass(frozen=True, slots=True)
class BacktestPlan:
    entry_low: float
    entry_high: float
    breakout_price: float
    stop_price: float
    max_position_cash: float
    source: str


@dataclass(frozen=True, slots=True)
class BacktestDecision:
    reason_code: str
    planned_price: float
    fill_price: float
    plan: BacktestPlan | None

    @property
    def is_filled(self) -> bool:
        return self.reason_code == "BUY_FILLED"


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
    total_cost_amount: float
    reason_counts: tuple[tuple[str, int], ...]
    status: str = "SUCCESS"

    @property
    def report_path(self) -> Path:
        return self.report_dir / "walk_forward_summary.md"
