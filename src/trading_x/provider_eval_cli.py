import argparse
import csv
import json
import sqlite3
from pathlib import Path

from trading_x.provider_decision import (
    ComplianceUseStatus,
    ProviderEvaluationEvidence,
    decide_provider_evaluation,
)
from trading_x.provider_evaluation import (
    ProviderSampleInputError,
    ProviderSnapshotSample,
    ProviderSource,
    parse_provider_sample_file_text,
)
from trading_x.provider_report import write_provider_evaluation_report
from trading_x.types import StrategyType


_PROVIDER_SOURCES = [source.value for source in ProviderSource]


def configure_provider_evaluation_cli(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--source", required=True, choices=_PROVIDER_SOURCES)
    parser.add_argument("--date", required=True)
    parser.add_argument("--symbols", required=True)
    parser.add_argument("--sample", type=Path, required=True)
    parser.add_argument("--output-dir", type=Path, default=Path("reports/provider_eval"))
    parser.add_argument(
        "--compliance-use-status",
        choices=[status.value for status in ComplianceUseStatus],
        default=ComplianceUseStatus.UNKNOWN,
    )
    parser.add_argument("--timestamp-order-trusted", action=argparse.BooleanOptionalAction, default=True)


def configure_provider_replay_export_cli(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--source", required=True, choices=_PROVIDER_SOURCES)
    parser.add_argument("--date", required=True)
    parser.add_argument("--sample", type=Path, required=True)
    parser.add_argument("--output", type=Path)


def configure_provider_sample_template_cli(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--source", required=True, choices=_PROVIDER_SOURCES)
    parser.add_argument("--date", required=True)
    parser.add_argument("--strategy", choices=[strategy.value for strategy in StrategyType], default=StrategyType.B_CAPACITY_LEADER.value)
    parser.add_argument("--output", type=Path)


def handle_provider_evaluation_command(args: argparse.Namespace) -> int:
    try:
        samples = _load_samples(args.sample, args.source, args.date)
        source = args.source
        requested_symbols = tuple(symbol.strip() for symbol in args.symbols.split(",") if symbol.strip())
        if not requested_symbols:
            raise ProviderSampleInputError("PROVIDER_SAMPLE_SYMBOLS_REQUIRED")
        evidence = ProviderEvaluationEvidence(
            requested_symbols=requested_symbols,
            samples=samples,
            compliance_use_status=ComplianceUseStatus(args.compliance_use_status),
            timestamp_order_trusted=args.timestamp_order_trusted,
        )
        decision = decide_provider_evaluation(evidence)
        artifacts = write_provider_evaluation_report(args.output_dir, evidence, decision)
    except FileNotFoundError:
        print(f"provider_evaluation=FAILED {args.source} {args.date}")
        print("PROVIDER_SAMPLE_FILE_NOT_FOUND")
        return 1
    except ProviderSampleInputError as exc:
        print(f"provider_evaluation=FAILED {args.source} {args.date}")
        print(exc.reason_code)
        return 1

    print(f"provider_evaluation={decision.status} {source} {args.date} samples={len(samples)}")
    print(f"json={artifacts.json_path}")
    print(f"markdown={artifacts.markdown_path}")
    return 0


def handle_provider_replay_export_command(args: argparse.Namespace) -> int:
    output_path = args.output or Path("data") / "replay" / f"{args.date}.csv"
    try:
        samples = _load_samples(args.sample, args.source, args.date)
        _write_replay_csv(output_path, samples)
    except FileNotFoundError:
        print(f"replay_csv=FAILED {args.source} {args.date}")
        print("PROVIDER_SAMPLE_FILE_NOT_FOUND")
        return 1
    except ProviderSampleInputError as exc:
        print(f"replay_csv=FAILED {args.source} {args.date}")
        print(exc.reason_code)
        return 1
    except OSError:
        print(f"replay_csv=FAILED {args.source} {args.date}")
        print("REPLAY_CSV_UNWRITABLE")
        return 1

    print(f"replay_csv={output_path} rows={len(samples)}")
    return 0


def handle_provider_sample_template_command(db_path: Path, args: argparse.Namespace) -> int:
    source = ProviderSource(args.source)
    output_path = args.output or Path("data") / "provider_samples" / f"{args.date}_{source.value}_template.json"
    rows = [
        {
            "trade_date": args.date,
            "quote_time": "09:35:00",
            "ts_code": symbol,
            "price": 0.0,
            "amount_since_open": 0.0,
            "volume_since_open": 0.0,
            "bar_high": 0.0,
            "bar_low": 0.0,
            "source": source.value,
            "latency_ms": 0,
            "validation_status": "rejected",
            "reason_codes": ["TEMPLATE_FILL_REQUIRED"],
        }
        for symbol in _plan_symbols(db_path, args.date, StrategyType(args.strategy))
    ]
    try:
        output_path.parent.mkdir(parents=True, exist_ok=True)
        output_path.write_text(json.dumps(rows, ensure_ascii=False, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    except OSError:
        print(f"provider_sample_template=FAILED {source.value} {args.date}")
        print("PROVIDER_SAMPLE_TEMPLATE_UNWRITABLE")
        return 1

    print(f"provider_sample_template={output_path} rows={len(rows)}")
    return 0


def _load_samples(sample_path: Path, source: str, trade_date: str) -> tuple[ProviderSnapshotSample, ...]:
    samples = parse_provider_sample_file_text(sample_path.read_text(encoding="utf-8"))
    if any(sample.trade_date != trade_date for sample in samples):
        raise ProviderSampleInputError("PROVIDER_SAMPLE_TRADE_DATE_MISMATCH")
    if any(sample.source != source for sample in samples):
        raise ProviderSampleInputError("PROVIDER_SAMPLE_SOURCE_MISMATCH")
    return samples


def _plan_symbols(db_path: Path, trade_date: str, strategy_type: StrategyType) -> tuple[str, ...]:
    with sqlite3.connect(db_path) as conn:
        rows = conn.execute(
            "SELECT ts_code FROM intraday_plans WHERE trade_date = ? AND strategy_type = ? ORDER BY ts_code",
            (trade_date, strategy_type),
        ).fetchall()
    return tuple(str(row[0]) for row in rows)


def _write_replay_csv(output_path: Path, samples: tuple[ProviderSnapshotSample, ...]) -> None:
    output_path.parent.mkdir(parents=True, exist_ok=True)
    with output_path.open("w", encoding="utf-8", newline="") as handle:
        writer = csv.DictWriter(
            handle,
            fieldnames=[
                "trade_date",
                "quote_time",
                "ts_code",
                "price",
                "amount_since_open",
                "volume_since_open",
                "bar_high",
                "bar_low",
            ],
        )
        writer.writeheader()
        for sample in samples:
            writer.writerow(
                {
                    "trade_date": sample.trade_date,
                    "quote_time": sample.quote_time,
                    "ts_code": sample.ts_code,
                    "price": sample.price,
                    "amount_since_open": sample.amount_since_open,
                    "volume_since_open": sample.volume_since_open,
                    "bar_high": sample.bar_high,
                    "bar_low": sample.bar_low,
                }
            )
