from pathlib import Path
import argparse
import os

from trading_x.acceptance import (
    incomplete_reports,
    recent_complete_report_dates,
    recent_report_dates,
    run_acceptance,
)
from trading_x.capabilities import ApiCheckResult, run_doctor
from trading_x.config import load_tushare_token
from trading_x.data_status import latest_complete_trade_date, p0_incomplete_reason
from trading_x.db import init_db
from trading_x.intraday import materialize_intraday_plans, run_replay
from trading_x.intraday_replay_csv import load_replay_bars
from trading_x.intraday_watch import FakeIntradayProvider, run_fake_watch
from trading_x.provider_eval_cli import (
    configure_provider_evaluation_cli,
    configure_provider_replay_export_cli,
    handle_provider_evaluation_command,
    handle_provider_replay_export_command,
)
from trading_x.reports import ReportSnapshot, generate_report
from trading_x.theme_cli import configure_theme_cli, handle_theme_command
from trading_x.theme_models import ThemeCoverage
from trading_x.themes import theme_coverage
from trading_x.tushare_adapter import (
    P0DataUnavailableError,
    TushareP0Adapter,
    TushareUnavailableError,
    update_p0_data,
)
from trading_x.tushare_live import TushareCapabilityAdapter
from trading_x.types import DataCapabilityLevel, StrategyType


DEFAULT_DB = Path("data/trading_x.db")
DEFAULT_REPORT_DIR = Path("reports")


class NullAdapter:
    def check_api(self, api_name: str) -> ApiCheckResult:
        return ApiCheckResult(
            api_name=api_name,
            available=False,
            error_code="not_configured",
            error_msg="Live Tushare adapter is not configured in this MVP",
        )


def main() -> int:
    parser = argparse.ArgumentParser(prog="trading_x")
    parser.add_argument("--db", type=Path, default=DEFAULT_DB)
    strategy_choices = [strategy.value for strategy in StrategyType]
    subparsers = parser.add_subparsers(dest="command", required=True)
    subparsers.add_parser("init-db")
    doctor_parser = subparsers.add_parser("doctor")
    doctor_parser.add_argument("--date")
    report_parser = subparsers.add_parser("report")
    report_parser.add_argument("--date", required=True)
    update_parser = subparsers.add_parser("update")
    update_parser.add_argument("--date", required=True)
    replay_parser = subparsers.add_parser("replay")
    replay_parser.add_argument("--date", required=True)
    replay_parser.add_argument("--input", type=Path)
    replay_parser.add_argument("--strategy", choices=strategy_choices, default=StrategyType.B_CAPACITY_LEADER.value)
    replay_parser.add_argument("--materialize", action="store_true")
    watch_parser = subparsers.add_parser("watch")
    watch_parser.add_argument("--date", required=True)
    watch_parser.add_argument("--input", type=Path)
    provider_parser = subparsers.add_parser("provider-evaluate")
    configure_provider_evaluation_cli(provider_parser)
    provider_replay_parser = subparsers.add_parser("provider-export-replay")
    configure_provider_replay_export_cli(provider_replay_parser)
    plans_parser = subparsers.add_parser("plans")
    plans_subparsers = plans_parser.add_subparsers(dest="plans_command", required=True)
    materialize_parser = plans_subparsers.add_parser("materialize")
    materialize_parser.add_argument("--date", required=True)
    materialize_parser.add_argument("--strategy", choices=strategy_choices, default=StrategyType.B_CAPACITY_LEADER.value)
    daily_parser = subparsers.add_parser("daily")
    daily_parser.add_argument("--date", required=True)
    acceptance_parser = subparsers.add_parser("acceptance")
    acceptance_date_group = acceptance_parser.add_mutually_exclusive_group(required=True)
    acceptance_date_group.add_argument("--dates")
    acceptance_date_group.add_argument("--last-n", type=int)
    acceptance_date_group.add_argument("--last-complete-n", type=int)
    acceptance_date_group.add_argument("--list-incomplete", action="store_true")
    acceptance_parser.add_argument("--report-dir", type=Path, default=DEFAULT_REPORT_DIR)
    themes_parser = subparsers.add_parser("themes")
    configure_theme_cli(themes_parser)
    args = parser.parse_args()

    if args.command == "init-db":
        init_db(args.db)
        print(f"initialized {args.db}")
        return 0
    if args.command == "doctor":
        init_db(args.db)
        token = load_tushare_token(env_value=os.environ.get("TUSHARE_TOKEN"))
        adapter = NullAdapter() if token is None else TushareCapabilityAdapter(token)
        summary = run_doctor(args.db, adapter, token, args.date)
        print(f"data_capability={summary.level}")
        for message in summary.messages:
            print(message)
        return 0 if token else 1
    if args.command == "report":
        init_db(args.db)
        snapshot = generate_report(args.db, args.date, DEFAULT_REPORT_DIR)
        print(f"report={snapshot.data_capability} {args.date}")
        return 0
    if args.command == "update":
        init_db(args.db)
        token = load_tushare_token(env_value=os.environ.get("TUSHARE_TOKEN"))
        if token is None or token.strip() == "":
            print("TUSHARE_TOKEN is required")
            return 1
        try:
            update_p0_data(args.db, args.date, TushareP0Adapter(token))
        except (P0DataUnavailableError, TushareUnavailableError) as exc:
            print(str(exc))
            return 1
        print(f"updated P0 data for {args.date}")
        return 0
    if args.command == "replay":
        init_db(args.db)
        strategy_type = StrategyType(args.strategy)
        if args.materialize:
            count = materialize_intraday_plans(args.db, args.date, strategy_type=strategy_type)
            print(f"intraday_plans={count} {args.date}")
        input_path = args.input or Path("data") / "replay" / f"{args.date}.csv"
        result = run_replay(
            args.db,
            args.date,
            input_path,
            DEFAULT_REPORT_DIR,
            strategy_type=strategy_type,
        )
        print(f"replay={result.status} {args.date} alerts={result.alert_count}")
        if result.error_message:
            print(result.error_message)
        return 0 if result.status == "SUCCESS" else 1
    if args.command == "watch":
        init_db(args.db)
        input_path = args.input or Path("data") / "replay" / f"{args.date}.csv"
        bars, error = load_replay_bars(input_path, args.date)
        if error is not None:
            print(f"watch=FAILED {args.date} alerts=0")
            print(error)
            return 1
        alerts = run_fake_watch(args.db, args.date, FakeIntradayProvider(tuple(bars)))
        print(f"watch=SUCCESS {args.date} alerts={len(alerts)}")
        return 0
    if args.command == "provider-evaluate":
        return handle_provider_evaluation_command(args)
    if args.command == "provider-export-replay":
        return handle_provider_replay_export_command(args)
    if args.command == "plans":
        init_db(args.db)
        count = materialize_intraday_plans(args.db, args.date, strategy_type=StrategyType(args.strategy))
        print(f"intraday_plans={count} {args.date}")
        return 0
    if args.command == "daily":
        return _run_daily(args.db, args.date)
    if args.command == "acceptance":
        if args.list_incomplete:
            reports = incomplete_reports(args.db, args.report_dir)
            print(f"incomplete_reports={len(reports)}")
            for report in reports:
                print(f"- {report.trade_date}: {','.join(report.reasons)}")
            return 0
        if args.dates is not None:
            dates = [date.strip() for date in (args.dates or "").split(",") if date.strip()]
        elif args.last_complete_n is not None:
            dates = recent_complete_report_dates(args.db, args.report_dir, args.last_complete_n)
        else:
            dates = recent_report_dates(args.db, args.last_n)
        result = run_acceptance(args.db, args.report_dir, dates)
        print(f"acceptance={'PASS' if result.passed else 'FAIL'}")
        print(f"days={result.checked_days}")
        for failure in result.failures:
            print(f"- {failure}")
        return 0 if result.passed else 1
    if args.command == "themes":
        init_db(args.db)
        return handle_theme_command(args.db, args)
    return 1


def _run_daily(db_path: Path, trade_date: str) -> int:
    init_db(db_path)
    token = load_tushare_token(env_value=os.environ.get("TUSHARE_TOKEN"))
    if token is None or token.strip() == "":
        summary = run_doctor(db_path, NullAdapter(), token)
        _print_daily_failure(trade_date, summary.level, "TUSHARE_TOKEN is required")
        return 1
    summary = run_doctor(db_path, TushareCapabilityAdapter(token), token)
    if summary.level == DataCapabilityLevel.DEGRADED:
        _print_daily_failure(trade_date, summary.level, "P0 数据缺失，停止生成候选")
        return 1
    try:
        update_p0_data(db_path, trade_date, TushareP0Adapter(token))
    except P0DataUnavailableError as exc:
        data_reason = p0_incomplete_reason(db_path, trade_date)
        reason = str(exc) if data_reason is None else f"{exc}；{data_reason}"
        _print_daily_failure(
            trade_date,
            summary.level,
            reason,
            latest_complete_date=latest_complete_trade_date(db_path, trade_date),
        )
        return 1
    except TushareUnavailableError as exc:
        _print_daily_failure(trade_date, summary.level, str(exc))
        return 1
    snapshot = generate_report(db_path, trade_date, DEFAULT_REPORT_DIR)
    coverage = theme_coverage(db_path, trade_date)
    _print_daily_summary(snapshot, DEFAULT_REPORT_DIR, coverage)
    return 0


def _print_daily_failure(
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


def _print_daily_summary(snapshot: ReportSnapshot, report_dir: Path, coverage: ThemeCoverage) -> None:
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
