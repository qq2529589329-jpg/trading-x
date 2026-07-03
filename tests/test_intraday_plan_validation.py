from pathlib import Path
import math
import sqlite3

import pytest

from intraday_replay_fixtures import PlanFixture, alert_rows, insert_plan, write_replay_csv
from trading_x.db import init_db
from trading_x.intraday import run_replay


def test_replay_disables_plan_when_entry_low_is_missing(tmp_path: Path) -> None:
    db_path = tmp_path / "trading_x.db"
    input_path = tmp_path / "replay.csv"
    report_dir = tmp_path / "reports"
    init_db(db_path)
    insert_plan(db_path, PlanFixture(official_pre_close=10.0, volume_min_abs_amount=1000.0))
    with sqlite3.connect(db_path) as conn:
        conn.execute("UPDATE intraday_plans SET entry_low = 0 WHERE trade_date = ?", ("20260630",))
    write_replay_csv(input_path, "20260630,09:36:00,300001.SZ,12.00,10000,1000,12.00,11.80\n")

    run_replay(db_path, "20260630", input_path, report_dir)

    with sqlite3.connect(db_path) as conn:
        status = conn.execute(
            "SELECT plan_status FROM intraday_plans WHERE trade_date = ? AND ts_code = ?",
            ("20260630", "300001.SZ"),
        ).fetchone()[0]
    report = (report_dir / "20260630_replay_report.md").read_text(encoding="utf-8")
    assert status == "DISABLED"
    assert alert_rows(db_path) == []
    assert "PLAN_INVALID" in report


def test_replay_disables_plan_when_vwap_active_after_is_missing(tmp_path: Path) -> None:
    db_path = tmp_path / "trading_x.db"
    input_path = tmp_path / "replay.csv"
    report_dir = tmp_path / "reports"
    init_db(db_path)
    insert_plan(db_path, PlanFixture(official_pre_close=10.0, volume_min_abs_amount=1000.0))
    with sqlite3.connect(db_path) as conn:
        conn.execute("UPDATE intraday_plans SET vwap_active_after = '' WHERE trade_date = ?", ("20260630",))
    write_replay_csv(input_path, "20260630,09:36:00,300001.SZ,12.00,10000,1000,12.00,11.80\n")

    run_replay(db_path, "20260630", input_path, report_dir)

    with sqlite3.connect(db_path) as conn:
        status = conn.execute(
            "SELECT plan_status FROM intraday_plans WHERE trade_date = ? AND ts_code = ?",
            ("20260630", "300001.SZ"),
        ).fetchone()[0]
    assert status == "DISABLED"
    assert alert_rows(db_path) == []


@pytest.mark.parametrize(
    "update_sql",
    [
        "UPDATE intraday_plans SET entry_high = 9.9 WHERE trade_date = ?",
        "UPDATE intraday_plans SET breakout_price = 9.9 WHERE trade_date = ?",
        "UPDATE intraday_plans SET stop_price = 10.0 WHERE trade_date = ?",
    ],
)
def test_replay_disables_plan_when_price_relationship_is_invalid(
    tmp_path: Path,
    update_sql: str,
) -> None:
    db_path = tmp_path / "trading_x.db"
    input_path = tmp_path / "replay.csv"
    report_dir = tmp_path / "reports"
    init_db(db_path)
    insert_plan(db_path, PlanFixture(official_pre_close=10.0, volume_min_abs_amount=1000.0))
    with sqlite3.connect(db_path) as conn:
        conn.execute(update_sql, ("20260630",))
    write_replay_csv(input_path, "20260630,09:36:00,300001.SZ,12.00,10000,1000,12.00,11.80\n")

    run_replay(db_path, "20260630", input_path, report_dir)

    with sqlite3.connect(db_path) as conn:
        status = conn.execute(
            "SELECT plan_status FROM intraday_plans WHERE trade_date = ? AND ts_code = ?",
            ("20260630", "300001.SZ"),
        ).fetchone()[0]
    report = (report_dir / "20260630_replay_report.md").read_text(encoding="utf-8")
    assert status == "DISABLED"
    assert alert_rows(db_path) == []
    assert "PLAN_INVALID" in report


def test_replay_disables_plan_when_stop_distance_exceeds_limit(tmp_path: Path) -> None:
    db_path = tmp_path / "trading_x.db"
    input_path = tmp_path / "replay.csv"
    report_dir = tmp_path / "reports"
    init_db(db_path)
    insert_plan(db_path, PlanFixture(official_pre_close=10.0, volume_min_abs_amount=1000.0))
    with sqlite3.connect(db_path) as conn:
        conn.execute("UPDATE intraday_plans SET max_stop_distance = 0.01 WHERE trade_date = ?", ("20260630",))
    write_replay_csv(input_path, "20260630,09:36:00,300001.SZ,12.00,10000,1000,12.00,11.80\n")

    run_replay(db_path, "20260630", input_path, report_dir)

    with sqlite3.connect(db_path) as conn:
        status = conn.execute(
            "SELECT plan_status FROM intraday_plans WHERE trade_date = ? AND ts_code = ?",
            ("20260630", "300001.SZ"),
        ).fetchone()[0]
    report = (report_dir / "20260630_replay_report.md").read_text(encoding="utf-8")
    assert status == "DISABLED"
    assert alert_rows(db_path) == []
    assert "PLAN_INVALID" in report


def test_replay_disables_plan_when_plan_json_is_not_json_object(tmp_path: Path) -> None:
    db_path = tmp_path / "trading_x.db"
    input_path = tmp_path / "replay.csv"
    report_dir = tmp_path / "reports"
    init_db(db_path)
    insert_plan(db_path, PlanFixture(official_pre_close=10.0, volume_min_abs_amount=1000.0))
    with sqlite3.connect(db_path) as conn:
        conn.execute("UPDATE intraday_plans SET plan_json = 'not-json' WHERE trade_date = ?", ("20260630",))
    write_replay_csv(input_path, "20260630,09:36:00,300001.SZ,12.00,10000,1000,12.00,11.80\n")

    run_replay(db_path, "20260630", input_path, report_dir)

    with sqlite3.connect(db_path) as conn:
        status = conn.execute(
            "SELECT plan_status FROM intraday_plans WHERE trade_date = ? AND ts_code = ?",
            ("20260630", "300001.SZ"),
        ).fetchone()[0]
    report = (report_dir / "20260630_replay_report.md").read_text(encoding="utf-8")
    assert status == "DISABLED"
    assert alert_rows(db_path) == []
    assert "PLAN_INVALID" in report


@pytest.mark.parametrize(
    "update_sql",
    [
        "UPDATE intraday_plans SET max_position_cash = 0 WHERE trade_date = ?",
        "UPDATE intraday_plans SET max_loss = 100 WHERE trade_date = ?",
    ],
)
def test_replay_disables_plan_when_risk_budget_is_invalid(
    tmp_path: Path,
    update_sql: str,
) -> None:
    db_path = tmp_path / "trading_x.db"
    input_path = tmp_path / "replay.csv"
    report_dir = tmp_path / "reports"
    init_db(db_path)
    insert_plan(db_path, PlanFixture(official_pre_close=10.0, volume_min_abs_amount=1000.0))
    with sqlite3.connect(db_path) as conn:
        conn.execute(update_sql, ("20260630",))
    write_replay_csv(input_path, "20260630,09:36:00,300001.SZ,12.00,10000,1000,12.00,11.80\n")

    run_replay(db_path, "20260630", input_path, report_dir)

    with sqlite3.connect(db_path) as conn:
        status = conn.execute(
            "SELECT plan_status FROM intraday_plans WHERE trade_date = ? AND ts_code = ?",
            ("20260630", "300001.SZ"),
        ).fetchone()[0]
    report = (report_dir / "20260630_replay_report.md").read_text(encoding="utf-8")
    assert status == "DISABLED"
    assert alert_rows(db_path) == []
    assert "PLAN_INVALID" in report


def test_replay_disables_plan_when_enabled_volume_gate_has_no_threshold(
    tmp_path: Path,
) -> None:
    db_path = tmp_path / "trading_x.db"
    input_path = tmp_path / "replay.csv"
    report_dir = tmp_path / "reports"
    init_db(db_path)
    insert_plan(db_path, PlanFixture(official_pre_close=10.0, volume_min_abs_amount=0.0))
    write_replay_csv(input_path, "20260630,09:36:00,300001.SZ,12.00,10000,1000,12.00,11.80\n")

    run_replay(db_path, "20260630", input_path, report_dir)

    with sqlite3.connect(db_path) as conn:
        status = conn.execute(
            "SELECT plan_status FROM intraday_plans WHERE trade_date = ? AND ts_code = ?",
            ("20260630", "300001.SZ"),
        ).fetchone()[0]
    report = (report_dir / "20260630_replay_report.md").read_text(encoding="utf-8")
    assert status == "DISABLED"
    assert alert_rows(db_path) == []
    assert "PLAN_INVALID" in report


@pytest.mark.parametrize(
    "update_sql",
    [
        "UPDATE intraday_plans SET volume_same_window_multiplier = 0 WHERE trade_date = ?",
        "UPDATE intraday_plans SET volume_ratio_0935 = -0.01 WHERE trade_date = ?",
        "UPDATE intraday_plans SET volume_ratio_0945 = 0.02 WHERE trade_date = ?",
        "UPDATE intraday_plans SET volume_ratio_1000 = 0.04 WHERE trade_date = ?",
    ],
)
def test_replay_disables_plan_when_volume_profile_is_invalid(
    tmp_path: Path,
    update_sql: str,
) -> None:
    db_path = tmp_path / "trading_x.db"
    input_path = tmp_path / "replay.csv"
    report_dir = tmp_path / "reports"
    init_db(db_path)
    insert_plan(db_path, PlanFixture(official_pre_close=10.0, volume_min_abs_amount=1000.0))
    with sqlite3.connect(db_path) as conn:
        conn.execute(update_sql, ("20260630",))
    write_replay_csv(input_path, "20260630,09:36:00,300001.SZ,12.00,10000,1000,12.00,11.80\n")

    run_replay(db_path, "20260630", input_path, report_dir)

    with sqlite3.connect(db_path) as conn:
        status = conn.execute(
            "SELECT plan_status FROM intraday_plans WHERE trade_date = ? AND ts_code = ?",
            ("20260630", "300001.SZ"),
        ).fetchone()[0]
    report = (report_dir / "20260630_replay_report.md").read_text(encoding="utf-8")
    assert status == "DISABLED"
    assert alert_rows(db_path) == []
    assert "PLAN_INVALID" in report


def test_replay_disables_plan_when_numeric_field_is_not_finite(tmp_path: Path) -> None:
    db_path = tmp_path / "trading_x.db"
    input_path = tmp_path / "replay.csv"
    report_dir = tmp_path / "reports"
    init_db(db_path)
    insert_plan(db_path, PlanFixture(official_pre_close=10.0, volume_min_abs_amount=1000.0))
    with sqlite3.connect(db_path) as conn:
        conn.execute(
            "UPDATE intraday_plans SET official_pre_close = ? WHERE trade_date = ?",
            (math.inf, "20260630"),
        )
    write_replay_csv(input_path, "20260630,09:36:00,300001.SZ,12.00,10000,1000,12.00,11.80\n")

    run_replay(db_path, "20260630", input_path, report_dir)

    with sqlite3.connect(db_path) as conn:
        status = conn.execute(
            "SELECT plan_status FROM intraday_plans WHERE trade_date = ? AND ts_code = ?",
            ("20260630", "300001.SZ"),
        ).fetchone()[0]
    report = (report_dir / "20260630_replay_report.md").read_text(encoding="utf-8")
    assert status == "DISABLED"
    assert alert_rows(db_path) == []
    assert "PLAN_INVALID" in report
