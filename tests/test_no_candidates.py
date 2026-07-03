from pathlib import Path

from trading_x.db import init_db
from trading_x.reports import generate_report


def test_ten_consecutive_weak_days_emit_no_candidate_reports(tmp_path: Path) -> None:
    db_path = tmp_path / "trading_x.db"
    report_dir = tmp_path / "reports"
    init_db(db_path)

    for day in range(1, 11):
        trade_date = f"202607{day:02d}"
        snapshot = generate_report(db_path, trade_date, report_dir)
        markdown = (report_dir / f"{trade_date}_report.md").read_text(encoding="utf-8")

        assert snapshot.candidates == []
        assert snapshot.allow_new_position is False
        assert "禁止新开仓" in markdown
        assert "今日无符合纪律候选" in markdown

