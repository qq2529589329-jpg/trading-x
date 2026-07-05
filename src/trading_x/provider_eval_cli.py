from pathlib import Path
import argparse

from trading_x.provider_decision import (
    ComplianceUseStatus,
    ProviderEvaluationEvidence,
    decide_provider_evaluation,
)
from trading_x.provider_evaluation import (
    ProviderSampleInputError,
    parse_provider_sample_file_text,
)
from trading_x.provider_report import write_provider_evaluation_report


def configure_provider_evaluation_cli(parser: argparse.ArgumentParser) -> None:
    parser.add_argument("--source", required=True, choices=["mootdx", "tencent_snapshot"])
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


def handle_provider_evaluation_command(args: argparse.Namespace) -> int:
    try:
        samples = parse_provider_sample_file_text(args.sample.read_text(encoding="utf-8"))
        source = args.source
        if any(sample.trade_date != args.date for sample in samples):
            raise ProviderSampleInputError("PROVIDER_SAMPLE_TRADE_DATE_MISMATCH")
        if any(sample.source != source for sample in samples):
            raise ProviderSampleInputError("PROVIDER_SAMPLE_SOURCE_MISMATCH")
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
