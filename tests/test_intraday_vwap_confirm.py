from pathlib import Path

from intraday_replay_fixtures import PlanFixture, alert_rows, insert_plan, write_replay_csv
from trading_x.db import init_db
from trading_x.intraday import run_replay


def test_buy_trigger_waits_for_vwap_confirm_seconds(tmp_path: Path) -> None:
    db_path = tmp_path / "trading_x.db"
    input_path = tmp_path / "replay.csv"
    init_db(db_path)
    insert_plan(
        db_path,
        PlanFixture(
            official_pre_close=10.0,
            volume_min_abs_amount=1000.0,
            vwap_above_confirm_seconds=120,
        ),
    )
    write_replay_csv(
        input_path,
        "20260630,09:36:00,300001.SZ,12.00,10000,1000,12.00,11.80\n"
        "20260630,09:38:00,300001.SZ,12.10,11000,1000,12.10,12.00\n",
    )

    run_replay(db_path, "20260630", input_path, tmp_path / "reports")

    assert alert_rows(db_path) == [
        ("WATCH", "B_VWAP_CONFIRMING"),
        ("BUY_TRIGGER", "B_BUY_TRIGGERED"),
    ]


def test_zero_volume_vwap_only_watches(tmp_path: Path) -> None:
    db_path = tmp_path / "trading_x.db"
    input_path = tmp_path / "replay.csv"
    init_db(db_path)
    insert_plan(db_path, PlanFixture(official_pre_close=10.0, volume_min_abs_amount=1000.0))
    write_replay_csv(
        input_path,
        "20260630,09:36:00,300001.SZ,12.00,10000,0,12.00,11.80\n",
    )

    run_replay(db_path, "20260630", input_path, tmp_path / "reports")

    assert alert_rows(db_path) == [("WATCH", "VOLUME_GATE_FAILED")]


def test_replay_does_not_watch_vwap_confirming_above_entry_high(tmp_path: Path) -> None:
    db_path = tmp_path / "trading_x.db"
    input_path = tmp_path / "replay.csv"
    init_db(db_path)
    insert_plan(
        db_path,
        PlanFixture(
            official_pre_close=10.0,
            volume_min_abs_amount=1000.0,
            vwap_above_confirm_seconds=120,
        ),
    )
    write_replay_csv(input_path, "20260630,09:36:00,300001.SZ,13.50,10000,1000,13.60,13.40\n")

    run_replay(db_path, "20260630", input_path, tmp_path / "reports")

    assert alert_rows(db_path) == []


def test_vwap_confirm_seconds_start_after_volume_gate_passes(tmp_path: Path) -> None:
    db_path = tmp_path / "trading_x.db"
    input_path = tmp_path / "replay.csv"
    init_db(db_path)
    insert_plan(
        db_path,
        PlanFixture(
            official_pre_close=10.0,
            volume_min_abs_amount=1000.0,
            vwap_above_confirm_seconds=120,
        ),
    )
    write_replay_csv(
        input_path,
        "20260630,09:36:00,300001.SZ,12.00,500,50,12.00,11.80\n"
        "20260630,09:38:00,300001.SZ,12.10,1000,100,12.10,12.00\n"
        "20260630,09:40:00,300001.SZ,12.20,1200,120,12.20,12.10\n",
    )

    run_replay(db_path, "20260630", input_path, tmp_path / "reports")

    assert alert_rows(db_path) == [
        ("WATCH", "VOLUME_GATE_FAILED"),
        ("WATCH", "B_VWAP_CONFIRMING"),
        ("BUY_TRIGGER", "B_BUY_TRIGGERED"),
    ]


def test_vwap_confirm_seconds_start_inside_entry_range(tmp_path: Path) -> None:
    db_path = tmp_path / "trading_x.db"
    input_path = tmp_path / "replay.csv"
    init_db(db_path)
    insert_plan(
        db_path,
        PlanFixture(
            official_pre_close=10.0,
            volume_min_abs_amount=1000.0,
            vwap_above_confirm_seconds=120,
        ),
    )
    write_replay_csv(
        input_path,
        "20260630,09:36:00,300001.SZ,13.50,10000,1000,13.60,13.40\n"
        "20260630,09:38:00,300001.SZ,12.10,11000,1000,12.20,12.00\n"
        "20260630,09:40:00,300001.SZ,12.20,12000,1000,12.30,12.10\n",
    )

    run_replay(db_path, "20260630", input_path, tmp_path / "reports")

    assert alert_rows(db_path) == [
        ("WATCH", "B_VWAP_CONFIRMING"),
        ("BUY_TRIGGER", "B_BUY_TRIGGERED"),
    ]
