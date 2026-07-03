from pathlib import Path
import json
import sqlite3

from intraday_replay_fixtures import PlanFixture, insert_plan, write_replay_csv
from trading_x.db import init_db
from trading_x.intraday import run_replay


def test_alert_snapshot_keeps_replay_bar_high_low(tmp_path: Path) -> None:
    db_path = tmp_path / "trading_x.db"
    input_path = tmp_path / "replay.csv"
    init_db(db_path)
    insert_plan(db_path, PlanFixture(official_pre_close=10.0, volume_min_abs_amount=1000.0))
    write_replay_csv(
        input_path,
        "20260630,09:36:00,300001.SZ,12.00,10000,1000,12.30,11.70\n",
    )

    run_replay(db_path, "20260630", input_path, tmp_path / "reports")

    with sqlite3.connect(db_path) as conn:
        snapshot_json = conn.execute("SELECT snapshot_json FROM intraday_alerts").fetchone()[0]

    snapshot = json.loads(snapshot_json)
    assert snapshot["bar_high"] == 12.3
    assert snapshot["bar_low"] == 11.7


def test_alert_snapshot_records_vwap_from_amount_and_volume(tmp_path: Path) -> None:
    db_path = tmp_path / "trading_x.db"
    input_path = tmp_path / "replay.csv"
    init_db(db_path)
    insert_plan(db_path, PlanFixture(official_pre_close=10.0, volume_min_abs_amount=1000.0))
    write_replay_csv(
        input_path,
        "20260630,09:36:00,300001.SZ,12.00,10000,1000,12.30,11.70\n",
    )

    run_replay(db_path, "20260630", input_path, tmp_path / "reports")

    with sqlite3.connect(db_path) as conn:
        snapshot_json = conn.execute("SELECT snapshot_json FROM intraday_alerts").fetchone()[0]

    snapshot = json.loads(snapshot_json)
    assert snapshot["continuous_vwap"] == 10.0
    assert snapshot["continuous_vwap"] != snapshot["price"]


def test_zero_volume_alert_snapshot_keeps_vwap_null(tmp_path: Path) -> None:
    db_path = tmp_path / "trading_x.db"
    input_path = tmp_path / "replay.csv"
    init_db(db_path)
    insert_plan(db_path, PlanFixture(official_pre_close=10.0, volume_min_abs_amount=1000.0))
    write_replay_csv(
        input_path,
        "20260630,09:36:00,300001.SZ,12.00,10000,0,12.30,11.70\n",
    )

    run_replay(db_path, "20260630", input_path, tmp_path / "reports")

    with sqlite3.connect(db_path) as conn:
        snapshot_json = conn.execute("SELECT snapshot_json FROM intraday_alerts").fetchone()[0]

    snapshot = json.loads(snapshot_json)
    assert snapshot["continuous_vwap"] is None


def test_alert_snapshot_keeps_required_replay_bar_fields(tmp_path: Path) -> None:
    db_path = tmp_path / "trading_x.db"
    input_path = tmp_path / "replay.csv"
    init_db(db_path)
    insert_plan(db_path, PlanFixture(official_pre_close=10.0, volume_min_abs_amount=1000.0))
    write_replay_csv(
        input_path,
        "20260630,09:36:00,300001.SZ,12.00,10000,1000,12.30,11.70\n",
    )

    run_replay(db_path, "20260630", input_path, tmp_path / "reports")

    with sqlite3.connect(db_path) as conn:
        snapshot_json = conn.execute("SELECT snapshot_json FROM intraday_alerts").fetchone()[0]

    snapshot = json.loads(snapshot_json)
    assert snapshot == {
        "amount_since_open": 10000.0,
        "bar_high": 12.3,
        "bar_low": 11.7,
        "continuous_vwap": 10.0,
        "price": 12.0,
        "volume_since_open": 1000.0,
    }


def test_alert_keeps_plan_json_machine_payload(tmp_path: Path) -> None:
    db_path = tmp_path / "trading_x.db"
    input_path = tmp_path / "replay.csv"
    plan_payload = {"entry_low": 10.0, "source": "fixture", "stop_price": 9.8}
    plan_json = json.dumps(plan_payload, ensure_ascii=False, sort_keys=True)
    init_db(db_path)
    insert_plan(db_path, PlanFixture(official_pre_close=10.0, volume_min_abs_amount=1000.0))
    with sqlite3.connect(db_path) as conn:
        conn.execute("UPDATE intraday_plans SET plan_json = ? WHERE trade_date = ?", (plan_json, "20260630"))
    write_replay_csv(
        input_path,
        "20260630,09:36:00,300001.SZ,12.00,10000,1000,12.30,11.70\n",
    )

    run_replay(db_path, "20260630", input_path, tmp_path / "reports")

    with sqlite3.connect(db_path) as conn:
        alert_plan_json = conn.execute("SELECT plan_json FROM intraday_alerts").fetchone()[0]
    assert alert_plan_json == plan_json


def test_alert_keeps_state_transition_metadata(tmp_path: Path) -> None:
    db_path = tmp_path / "trading_x.db"
    input_path = tmp_path / "replay.csv"
    init_db(db_path)
    insert_plan(db_path, PlanFixture(official_pre_close=10.0, volume_min_abs_amount=1000.0))
    write_replay_csv(
        input_path,
        "20260630,09:36:00,300001.SZ,12.00,10000,1000,12.30,11.70\n",
    )

    run_replay(db_path, "20260630", input_path, tmp_path / "reports")

    with sqlite3.connect(db_path) as conn:
        state_row = conn.execute(
            "SELECT state_before, state_after FROM intraday_alerts WHERE alert_type = ?",
            ("BUY_TRIGGER",),
        ).fetchone()
    assert state_row == ("ENTRY_ARMED", "BUY_TRIGGER")


def test_alert_keeps_readable_metadata(tmp_path: Path) -> None:
    db_path = tmp_path / "trading_x.db"
    input_path = tmp_path / "replay.csv"
    init_db(db_path)
    insert_plan(db_path, PlanFixture(official_pre_close=10.0, volume_min_abs_amount=1000.0))
    write_replay_csv(
        input_path,
        "20260630,09:36:00,300001.SZ,12.00,10000,1000,12.30,11.70\n",
    )

    run_replay(db_path, "20260630", input_path, tmp_path / "reports")

    with sqlite3.connect(db_path) as conn:
        metadata_row = conn.execute(
            "SELECT severity, title, message FROM intraday_alerts WHERE alert_type = ?",
            ("BUY_TRIGGER",),
        ).fetchone()
    assert metadata_row == ("HIGH", "容量龙 BUY_TRIGGER", "B_BUY_TRIGGERED")


def test_alert_keeps_rule_id_reason_code_pair(tmp_path: Path) -> None:
    db_path = tmp_path / "trading_x.db"
    input_path = tmp_path / "replay.csv"
    init_db(db_path)
    insert_plan(db_path, PlanFixture(official_pre_close=10.0, volume_min_abs_amount=1000.0))
    write_replay_csv(
        input_path,
        "20260630,09:36:00,300001.SZ,12.00,10000,1000,12.30,11.70\n",
    )

    run_replay(db_path, "20260630", input_path, tmp_path / "reports")

    with sqlite3.connect(db_path) as conn:
        rule_row = conn.execute(
            "SELECT rule_id, reason_code FROM intraday_alerts WHERE alert_type = ?",
            ("BUY_TRIGGER",),
        ).fetchone()
    assert rule_row == ("B_BUY_TRIGGERED", "B_BUY_TRIGGERED")


def test_alert_keeps_created_at_as_utc_audit_timestamp(tmp_path: Path) -> None:
    db_path = tmp_path / "trading_x.db"
    input_path = tmp_path / "replay.csv"
    init_db(db_path)
    insert_plan(db_path, PlanFixture(official_pre_close=10.0, volume_min_abs_amount=1000.0))
    write_replay_csv(
        input_path,
        "20260630,09:36:00,300001.SZ,12.00,10000,1000,12.30,11.70\n",
    )

    run_replay(db_path, "20260630", input_path, tmp_path / "reports")

    with sqlite3.connect(db_path) as conn:
        time_row = conn.execute(
            "SELECT alert_time, created_at FROM intraday_alerts WHERE alert_type = ?",
            ("BUY_TRIGGER",),
        ).fetchone()
    assert time_row[0] == "09:36:00"
    assert time_row[1].endswith("+00:00")
    assert time_row[1] != time_row[0]
