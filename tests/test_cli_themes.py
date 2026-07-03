from pathlib import Path
import csv
import sys

from trading_x.cli import main
from trading_x.db import init_db


def test_cli_imports_theme_csv_and_prints_coverage(
    tmp_path: Path,
    monkeypatch,
    capsys,
) -> None:
    db_path = tmp_path / "trading_x.db"
    csv_path = tmp_path / "theme_members.csv"
    init_db(db_path)
    with csv_path.open("w", encoding="utf-8", newline="") as file:
        writer = csv.writer(file)
        writer.writerow(
            [
                "ts_code",
                "name",
                "industry",
                "theme_primary",
                "theme_tags",
                "theme_source",
                "confidence",
                "updated_at",
                "notes",
            ]
        )
        writer.writerow(
            ["300124.SZ", "汇川技术", "自动化设备", "机器人", "机器人;智能制造", "manual", "MEDIUM", "2026-06-30", ""]
        )

    monkeypatch.setattr(
        sys,
        "argv",
        ["trading_x", "--db", str(db_path), "themes", "import", "--file", str(csv_path)],
    )
    assert main() == 0
    assert "imported=1" in capsys.readouterr().out

    monkeypatch.setattr(
        sys,
        "argv",
        ["trading_x", "--db", str(db_path), "themes", "coverage", "--date", "20260630"],
    )
    assert main() == 0
    output = capsys.readouterr().out
    assert "stock_total=" in output
    assert "limit_up_coverage=" in output


def test_cli_exports_missing_theme_candidates(
    tmp_path: Path,
    monkeypatch,
    capsys,
) -> None:
    db_path = tmp_path / "trading_x.db"
    output_path = tmp_path / "missing.csv"
    init_db(db_path)

    monkeypatch.setattr(
        sys,
        "argv",
        [
            "trading_x",
            "--db",
            str(db_path),
            "themes",
            "export-missing",
            "--date",
            "20260630",
            "--output",
            str(output_path),
        ],
    )

    assert main() == 0
    assert output_path.exists()
    assert "exported_missing=" in capsys.readouterr().out
