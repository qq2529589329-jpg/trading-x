from pathlib import Path

from intraday_replay_fixtures import PlanFixture, alert_rows, insert_plan, write_replay_csv
from trading_x.db import init_db
from trading_x.intraday import run_replay


def test_replay_rejects_positive_volume_with_zero_amount(tmp_path: Path) -> None:
    db_path = tmp_path / "trading_x.db"
    input_path = tmp_path / "replay.csv"
    report_dir = tmp_path / "reports"
    init_db(db_path)
    insert_plan(
        db_path,
        PlanFixture(
            official_pre_close=10.0,
            volume_min_abs_amount=1000.0,
            volume_gate_enabled=False,
        ),
    )
    write_replay_csv(input_path, "20260630,09:36:00,300001.SZ,12.00,0,1000,12.00,11.80\n")

    result = run_replay(db_path, "20260630", input_path, report_dir)

    report = (report_dir / "20260630_replay_report.md").read_text(encoding="utf-8")
    assert result.status == "FAILED"
    assert result.error_message == "REPLAY_CSV_INVALID_ROW"
    assert alert_rows(db_path) == []
    assert "REPLAY_CSV_INVALID_ROW" in report
