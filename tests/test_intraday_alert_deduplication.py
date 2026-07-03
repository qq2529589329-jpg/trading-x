from pathlib import Path

from intraday_replay_fixtures import PlanFixture, alert_rows, insert_plan, write_replay_csv
from trading_x.db import init_db
from trading_x.intraday import run_replay


def test_replay_counts_only_inserted_alerts_when_watch_repeats(tmp_path: Path) -> None:
    db_path = tmp_path / "trading_x.db"
    input_path = tmp_path / "replay.csv"
    report_dir = tmp_path / "reports"
    init_db(db_path)
    insert_plan(db_path, PlanFixture(official_pre_close=10.0, volume_min_abs_amount=10_000_000.0))
    write_replay_csv(
        input_path,
        "20260630,09:36:00,300001.SZ,12.00,1000,100,12.00,11.80\n"
        "20260630,09:37:00,300001.SZ,12.10,1200,100,12.10,12.00\n",
    )

    result = run_replay(db_path, "20260630", input_path, report_dir)

    report = (report_dir / "20260630_replay_report.md").read_text(encoding="utf-8")
    assert result.alert_count == 1
    assert alert_rows(db_path) == [("WATCH", "VOLUME_GATE_FAILED")]
    assert report.count("VOLUME_GATE_FAILED") == 1


def test_replay_counts_only_inserted_alerts_when_buy_ready_repeats(tmp_path: Path) -> None:
    db_path = tmp_path / "trading_x.db"
    input_path = tmp_path / "replay.csv"
    report_dir = tmp_path / "reports"
    init_db(db_path)
    insert_plan(db_path, PlanFixture(official_pre_close=10.0, volume_min_abs_amount=1000.0))
    write_replay_csv(
        input_path,
        "20260630,09:36:00,300001.SZ,10.50,10000,1000,10.60,10.40\n"
        "20260630,09:37:00,300001.SZ,10.60,21200,2100,10.70,10.50\n",
    )

    result = run_replay(db_path, "20260630", input_path, report_dir)

    report = (report_dir / "20260630_replay_report.md").read_text(encoding="utf-8")
    assert result.alert_count == 1
    assert alert_rows(db_path) == [("BUY_READY", "B_BREAKOUT_READY")]
    assert report.count("B_BREAKOUT_READY") == 1
