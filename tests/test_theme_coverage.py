from pathlib import Path
import csv

from trading_x.db import init_db
from trading_x.themes import (
    ThemeMissingExportRequest,
    export_missing_theme_candidates,
    theme_coverage,
)
from theme_fixtures import insert_theme_market_fixture


def test_theme_coverage_reports_unmapped_candidates(tmp_path: Path) -> None:
    db_path = tmp_path / "trading_x.db"
    init_db(db_path)
    insert_theme_market_fixture(db_path)

    coverage = theme_coverage(db_path, "20260630")

    assert coverage.stock_total == 4
    assert coverage.mapped_stock_count == 3
    assert coverage.candidate_total == 2
    assert coverage.candidate_mapped_count == 1
    assert coverage.unmapped_candidates == ("000004.SZ",)
    assert coverage.limit_up_total == 2
    assert coverage.limit_up_mapped_count == 2
    assert coverage.top_amount_total == 4
    assert coverage.top_amount_mapped_count == 3
    assert coverage.limit_active_total == 2
    assert coverage.limit_active_mapped_count == 2
    assert coverage.missing_suggestions == ("000004.SZ",)


def test_export_missing_theme_candidates_writes_maintenance_csv(tmp_path: Path) -> None:
    db_path = tmp_path / "trading_x.db"
    output_path = tmp_path / "theme_missing_candidates.csv"
    init_db(db_path)
    insert_theme_market_fixture(db_path)

    count = export_missing_theme_candidates(
        db_path,
        ThemeMissingExportRequest(
            trade_date="20260630",
            top_amount=2,
            top_limit_active=2,
            output_path=output_path,
        ),
    )

    with output_path.open(encoding="utf-8", newline="") as file:
        rows = list(csv.DictReader(file))
    assert count == 1
    assert rows[0]["ts_code"] == "000004.SZ"
    assert rows[0]["reason"] == "candidate"
