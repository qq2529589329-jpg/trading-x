from io import StringIO
from pathlib import Path
import csv

from intraday_replay_fixtures import PlanFixture, alert_rows, insert_plan
from trading_x.db import init_db
from trading_x.intraday_watch import FakeIntradayProvider, run_fake_watch


def test_fake_watch_matches_replay_vwap_confirming_then_buy_trigger(tmp_path: Path) -> None:
    db_path = tmp_path / "trading_x.db"
    init_db(db_path)
    insert_plan(
        db_path,
        PlanFixture(
            trade_date="20260630",
            official_pre_close=10.0,
            volume_min_abs_amount=1000.0,
            vwap_above_confirm_seconds=60,
        ),
    )
    provider = _fake_provider(
        "20260630,09:36:00,300001.SZ,10.50,10000,1000,10.50,10.20",
        "20260630,09:37:00,300001.SZ,12.00,11000,1000,12.00,11.80",
    )

    alerts = run_fake_watch(db_path, "20260630", provider)

    assert [(alert.alert_type, alert.reason_code) for alert in alerts] == [
        ("WATCH", "B_VWAP_CONFIRMING"),
        ("BUY_TRIGGER", "B_BUY_TRIGGERED"),
    ]
    assert alert_rows(db_path) == [
        ("WATCH", "B_VWAP_CONFIRMING"),
        ("BUY_TRIGGER", "B_BUY_TRIGGERED"),
    ]


def test_fake_watch_matches_replay_buy_ready(tmp_path: Path) -> None:
    db_path = tmp_path / "trading_x.db"
    init_db(db_path)
    insert_plan(
        db_path,
        PlanFixture(trade_date="20260701", official_pre_close=10.0, volume_min_abs_amount=1000.0),
    )
    provider = _fake_provider("20260701,09:36:00,300001.SZ,10.50,10000,1000,10.50,10.20")

    run_fake_watch(db_path, "20260701", provider)

    assert alert_rows(db_path) == [("BUY_READY", "B_BREAKOUT_READY")]


def test_fake_watch_matches_replay_entry_cancelled_without_sell_trigger(tmp_path: Path) -> None:
    db_path = tmp_path / "trading_x.db"
    init_db(db_path)
    insert_plan(
        db_path,
        PlanFixture(trade_date="20260702", official_pre_close=10.0, volume_min_abs_amount=1000.0),
    )
    provider = _fake_provider("20260702,09:36:00,300001.SZ,9.70,10000,1000,9.80,9.70")

    run_fake_watch(db_path, "20260702", provider)

    assert alert_rows(db_path) == [("ENTRY_CANCELLED", "ENTRY_CANCELLED_PRICE_OUT_OF_RANGE")]


def test_fake_watch_matches_replay_pre_close_missing_blocks_buy(tmp_path: Path) -> None:
    db_path = tmp_path / "trading_x.db"
    init_db(db_path)
    insert_plan(
        db_path,
        PlanFixture(trade_date="20260703", official_pre_close=0.0, volume_min_abs_amount=1000.0),
    )
    provider = _fake_provider("20260703,09:36:00,300001.SZ,12.00,10000,1000,12.00,11.80")

    run_fake_watch(db_path, "20260703", provider)

    assert alert_rows(db_path) == [("WATCH", "PRE_CLOSE_MISSING")]


def _fake_provider(*body_rows: str) -> FakeIntradayProvider:
    csv_text = (
        "trade_date,quote_time,ts_code,price,amount_since_open,volume_since_open,bar_high,bar_low\n"
        + "\n".join(body_rows)
    )
    return FakeIntradayProvider.from_rows(csv.DictReader(StringIO(csv_text)))
