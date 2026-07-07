import argparse
from pathlib import Path

from trading_x.positions import import_positions


def configure_positions_cli(parser: argparse.ArgumentParser) -> None:
    subparsers = parser.add_subparsers(dest="positions_command", required=True)
    import_parser = subparsers.add_parser("import")
    import_parser.add_argument("--date", required=True)
    import_parser.add_argument("--input", type=Path, required=True)


def handle_positions_command(db_path: Path, args: argparse.Namespace) -> int:
    if args.positions_command == "import":
        result = import_positions(db_path, args.date, args.input)
        print(f"positions_import={result.status} {args.date} positions={result.position_count}")
        if result.error_message:
            print(result.error_message)
        return 0 if result.status == "SUCCESS" else 1
    return 1