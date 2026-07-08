from collections.abc import Sequence
from pathlib import Path
import argparse
import os

from trading_x.config import load_tushare_token
from trading_x.research import (
    AdjFactorSyncRequest,
    BacktestTrustAuditRequest,
    RegimeClassificationRequest,
    ResearchBacktestRequest,
    ResearchEdgeRequest,
    analyze_research_edge,
    audit_research_backtest,
    classify_market_regimes,
    run_research_backtest,
    sync_backtest_adj_factors,
)
from trading_x.tushare_adapter import TushareP0Adapter
from trading_x.tushare_models import TushareUnavailableError
from trading_x.types import StrategyType


def configure_research_cli(parser: argparse.ArgumentParser, strategy_choices: Sequence[str]) -> None:
    subparsers = parser.add_subparsers(dest="research_command", required=True)
    regime_parser = subparsers.add_parser("classify-regime")
    regime_parser.add_argument("--start", required=True)
    regime_parser.add_argument("--end", default="latest")
    regime_parser.add_argument("--method-version", default="regime-v1")
    backtest_parser = subparsers.add_parser("backtest")
    backtest_parser.add_argument("--start", required=True)
    backtest_parser.add_argument("--end", default="latest")
    backtest_parser.add_argument("--strategy", choices=strategy_choices, default=StrategyType.B_CAPACITY_LEADER.value)
    backtest_parser.add_argument("--config-version", default="v1.0")
    backtest_parser.add_argument("--report-dir", type=Path, default=Path("reports/research"))
    audit_parser = subparsers.add_parser("audit-backtest")
    audit_parser.add_argument("--run-id")
    audit_parser.add_argument("--report-dir", type=Path, default=Path("reports/research"))
    sync_parser = subparsers.add_parser("sync-adj-factors")
    sync_parser.add_argument("--run-id")
    edge_parser = subparsers.add_parser("edge")
    edge_parser.add_argument("--run-id")
    edge_parser.add_argument("--report-dir", type=Path, default=Path("reports/research"))


def handle_research_command(db_path: Path, args: argparse.Namespace) -> int:
    if args.research_command == "classify-regime":
        result = classify_market_regimes(
            db_path,
            RegimeClassificationRequest(args.start, args.end, args.method_version),
        )
        print(f"market_regimes={result.classified_count} {result.start_date}-{result.end_date}")
        print(f"limit_events_daily_proxy={result.proxy_count}")
        return 0
    if args.research_command == "backtest":
        result = run_research_backtest(
            db_path,
            ResearchBacktestRequest(
                start_date=args.start,
                end_date=args.end,
                strategy_type=StrategyType(args.strategy),
                config_version=args.config_version,
                report_dir=args.report_dir,
            ),
        )
        print(
            f"research_backtest={result.status} {result.start_date}-{result.end_date} "
            f"candidates={result.candidate_count} trades={result.trade_count}"
        )
        print(f"report={result.report_path}")
        return 0
    if args.research_command == "audit-backtest":
        result = audit_research_backtest(
            db_path,
            BacktestTrustAuditRequest(args.run_id, args.report_dir),
        )
        print(f"backtest_trust_audit={result.status} run_id={result.run_id} issues={result.issue_count}")
        print(f"report={result.report_path}")
        return 0 if result.status == "PASS" else 1
    if args.research_command == "edge":
        result = analyze_research_edge(db_path, ResearchEdgeRequest(args.run_id, args.report_dir))
        print(
            f"research_edge=SUCCESS run_id={result.run_id} "
            f"buy_filled={result.buy_filled_count} benchmark={result.benchmark_count}"
        )
        print(f"report={result.report_path}")
        return 0
    if args.research_command == "sync-adj-factors":
        token = load_tushare_token(env_value=os.environ.get("TUSHARE_TOKEN"))
        if token is None or token.strip() == "":
            print("TUSHARE_TOKEN is required")
            return 1
        try:
            result = sync_backtest_adj_factors(db_path, AdjFactorSyncRequest(args.run_id), TushareP0Adapter(token))
        except TushareUnavailableError as exc:
            print(str(exc))
            return 1
        print(
            f"adj_factors run_id={result.run_id} missing_before={result.missing_before} "
            f"inserted={result.inserted_count} missing_after={result.missing_after}"
        )
        return 0 if result.missing_after == 0 else 1
    return 1