from pathlib import Path
import sqlite3

from trading_x.db import init_db
from trading_x.report_storage import ReportRecord, persist_report_snapshot


def test_persist_report_snapshot_writes_reports_table(tmp_path: Path) -> None:
    db_path = tmp_path / "trading_x.db"
    init_db(db_path)
    record = ReportRecord(
        trade_date="20260701",
        system_version="v1.0",
        report_md_path=tmp_path / "20260701_report.md",
        report_html_path=None,
        report_json_path=tmp_path / "20260701_report.json",
        report_snapshot_json='{"trade_date":"20260701"}',
        data_capability="BASIC",
    )

    persist_report_snapshot(db_path, record)

    with sqlite3.connect(db_path) as conn:
        row = conn.execute(
            "SELECT system_version, report_md_path, report_json_path, report_snapshot_json, data_capability "
            "FROM reports WHERE trade_date = ?",
            ("20260701",),
        ).fetchone()

    assert row == (
        "v1.0",
        str(tmp_path / "20260701_report.md"),
        str(tmp_path / "20260701_report.json"),
        '{"trade_date":"20260701"}',
        "BASIC",
    )
