from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
import sqlite3


@dataclass(frozen=True, slots=True)
class ReportRecord:
    trade_date: str
    system_version: str
    report_md_path: Path
    report_html_path: Path | None
    report_json_path: Path
    report_snapshot_json: str
    data_capability: str


def persist_report_snapshot(db_path: Path, record: ReportRecord) -> None:
    generated_at = datetime.now(UTC).isoformat()
    with sqlite3.connect(db_path) as conn:
        conn.execute(
            "INSERT INTO reports ("
            "trade_date, system_version, report_md_path, report_html_path, "
            "report_json_path, report_snapshot_json, data_capability, generated_at"
            ") VALUES (?, ?, ?, ?, ?, ?, ?, ?) "
            "ON CONFLICT(trade_date) DO UPDATE SET "
            "system_version = excluded.system_version, "
            "report_md_path = excluded.report_md_path, "
            "report_html_path = excluded.report_html_path, "
            "report_json_path = excluded.report_json_path, "
            "report_snapshot_json = excluded.report_snapshot_json, "
            "data_capability = excluded.data_capability, "
            "generated_at = excluded.generated_at",
            (
                record.trade_date,
                record.system_version,
                str(record.report_md_path),
                str(record.report_html_path) if record.report_html_path is not None else None,
                str(record.report_json_path),
                record.report_snapshot_json,
                record.data_capability,
                generated_at,
            ),
        )
