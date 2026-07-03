from pathlib import Path
import argparse

from trading_x.theme_models import ThemeCoverage, ThemeMissingExportRequest
from trading_x.themes import (
    ThemeCsvError,
    export_missing_theme_candidates,
    import_theme_members,
    theme_coverage,
)


def configure_theme_cli(parser: argparse.ArgumentParser) -> None:
    subparsers = parser.add_subparsers(dest="themes_command", required=True)
    import_parser = subparsers.add_parser("import")
    import_parser.add_argument("--file", type=Path, required=True)
    coverage_parser = subparsers.add_parser("coverage")
    coverage_parser.add_argument("--date", required=True)
    export_parser = subparsers.add_parser("export-missing")
    export_parser.add_argument("--date", required=True)
    export_parser.add_argument("--top-amount", type=int, default=200)
    export_parser.add_argument("--top-limit-active", type=int, default=100)
    export_parser.add_argument("--output", type=Path, required=True)


def handle_theme_command(db_path: Path, args: argparse.Namespace) -> int:
    if args.themes_command == "import":
        try:
            result = import_theme_members(db_path, args.file)
        except ThemeCsvError as exc:
            print(str(exc))
            return 1
        print(
            f"imported={result.imported_count} "
            f"failed={result.failed_count} duplicates={result.duplicate_count}"
        )
        return 0
    if args.themes_command == "coverage":
        _print_coverage(theme_coverage(db_path, args.date))
        return 0
    if args.themes_command == "export-missing":
        count = export_missing_theme_candidates(
            db_path,
            ThemeMissingExportRequest(
                trade_date=args.date,
                top_amount=args.top_amount,
                top_limit_active=args.top_limit_active,
                output_path=args.output,
            ),
        )
        print(f"exported_missing={count}")
        print(f"output={args.output}")
        return 0
    return 1


def _print_coverage(coverage: ThemeCoverage) -> None:
    print(f"stock_total={coverage.stock_total}")
    print(f"mapped_stock_count={coverage.mapped_stock_count}")
    print(f"candidate_total={coverage.candidate_total}")
    print(f"candidate_mapped_count={coverage.candidate_mapped_count}")
    print(f"limit_up_coverage={_ratio_text(coverage.limit_up_mapped_count, coverage.limit_up_total)}")
    print(f"top_amount_coverage={_ratio_text(coverage.top_amount_mapped_count, coverage.top_amount_total)}")
    print(f"limit_active_coverage={_ratio_text(coverage.limit_active_mapped_count, coverage.limit_active_total)}")
    print("unmapped_candidates=" + ",".join(coverage.unmapped_candidates))
    print("missing_suggestions=" + ",".join(coverage.missing_suggestions))


def _ratio_text(part: int, total: int) -> str:
    if total == 0:
        return f"{part}/{total} (unavailable)"
    return f"{part}/{total} ({part / total:.1%})"
