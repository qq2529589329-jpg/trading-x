from pathlib import Path
import json
import re
import sqlite3

from trading_x.db import init_db
from trading_x.intraday_models import REQUIRED_REPLAY_COLUMNS


def test_init_db_creates_required_tables_when_empty_database(tmp_path: Path) -> None:
    db_path = tmp_path / "trading_x.db"

    init_db(db_path)

    with sqlite3.connect(db_path) as conn:
        rows = conn.execute(
            "SELECT name FROM sqlite_master WHERE type = 'table'"
        ).fetchall()

    names = {row[0] for row in rows}
    assert {
        "data_capabilities",
        "data_status",
        "data_completeness_summary",
        "stock_universe",
        "daily_quotes",
        "daily_basic",
        "stk_limit_prices",
        "limit_events",
        "theme_strength",
        "theme_members",
        "theme_daily_strength",
        "candidates",
        "candidate_runs",
        "candidate_snapshots",
        "reports",
        "trade_logs",
        "intraday_plans",
        "intraday_alerts",
        "intraday_alert_locks",
        "intraday_replay_runs",
    } <= names

    with sqlite3.connect(db_path) as conn:
        views = conn.execute(
            "SELECT name FROM sqlite_master WHERE type = 'view'"
        ).fetchall()

    assert "candidates_latest" in {row[0] for row in views}


def test_init_db_adds_missing_candidate_columns_to_existing_database(
    tmp_path: Path,
) -> None:
    db_path = tmp_path / "trading_x.db"
    with sqlite3.connect(db_path) as conn:
        conn.execute(
            "CREATE TABLE candidates ("
            "trade_date TEXT, ts_code TEXT, strategy_type TEXT, candidate_grade TEXT, "
            "risk_pass INTEGER NOT NULL, market_status TEXT, theme_confidence TEXT, "
            "event_confidence TEXT, PRIMARY KEY (trade_date, ts_code, strategy_type)"
            ")"
        )

    init_db(db_path)

    with sqlite3.connect(db_path) as conn:
        rows = conn.execute("PRAGMA table_info(candidates)").fetchall()

    columns = {row[1] for row in rows}
    assert {"theme_name", "entry_reason", "veto_items"} <= columns


def test_init_db_adds_theme_weight_columns_to_existing_database(tmp_path: Path) -> None:
    db_path = tmp_path / "trading_x.db"
    with sqlite3.connect(db_path) as conn:
        conn.execute(
            "CREATE TABLE theme_members ("
            "ts_code TEXT PRIMARY KEY, name TEXT, industry TEXT, theme_primary TEXT, "
            "theme_tags TEXT, theme_source TEXT, confidence TEXT, updated_at TEXT, notes TEXT"
            ")"
        )
        conn.execute(
            "CREATE TABLE theme_daily_strength ("
            "trade_date TEXT, theme_name TEXT, theme_member_count INTEGER, "
            "theme_up_count INTEGER, theme_limit_up_count INTEGER, theme_avg_pct_chg REAL, "
            "theme_total_amount REAL, theme_candidate_count INTEGER, "
            "theme_strength_score REAL, theme_confidence TEXT, core_symbols TEXT, "
            "PRIMARY KEY (trade_date, theme_name)"
            ")"
        )

    init_db(db_path)

    with sqlite3.connect(db_path) as conn:
        member_columns = {row[1] for row in conn.execute("PRAGMA table_info(theme_members)")}
        strength_columns = {row[1] for row in conn.execute("PRAGMA table_info(theme_daily_strength)")}

    assert {"theme_tier", "theme_weight"} <= member_columns
    assert {"weighted_limit_up_count", "weighted_avg_pct_chg", "weighted_total_amount"} <= strength_columns


def test_replay_csv_contract_requires_zero_padded_quote_time() -> None:
    contract_path = Path(__file__).parents[1] / "specs" / "002-intraday-replay-mvp" / "contracts" / "replay-csv-schema.json"
    schema = json.loads(contract_path.read_text(encoding="utf-8"))
    pattern = schema["properties"]["quote_time"]["pattern"]

    assert re.fullmatch(pattern, "09:36:00") is not None
    assert re.fullmatch(pattern, "9:36:00") is None


def test_replay_csv_contract_rejects_blank_ts_code() -> None:
    contract_path = Path(__file__).parents[1] / "specs" / "002-intraday-replay-mvp" / "contracts" / "replay-csv-schema.json"
    schema = json.loads(contract_path.read_text(encoding="utf-8"))
    pattern = schema["properties"]["ts_code"].get("pattern")

    assert pattern is not None
    assert re.fullmatch(pattern, "300001.SZ") is not None
    assert re.fullmatch(pattern, "") is None
    assert re.fullmatch(pattern, "   ") is None


def test_replay_csv_contract_requires_vwap_input_columns() -> None:
    contract_path = Path(__file__).parents[1] / "specs" / "002-intraday-replay-mvp" / "contracts" / "replay-csv-schema.json"
    schema = json.loads(contract_path.read_text(encoding="utf-8"))

    assert schema["required"] == [
        "trade_date",
        "quote_time",
        "ts_code",
        "price",
        "amount_since_open",
        "volume_since_open",
        "bar_high",
        "bar_low",
    ]


def test_replay_csv_contract_matches_runtime_required_columns() -> None:
    contract_path = Path(__file__).parents[1] / "specs" / "002-intraday-replay-mvp" / "contracts" / "replay-csv-schema.json"
    schema = json.loads(contract_path.read_text(encoding="utf-8"))

    assert set(schema["required"]) == REQUIRED_REPLAY_COLUMNS


def test_replay_csv_contract_matches_runtime_numeric_bounds() -> None:
    contract_path = Path(__file__).parents[1] / "specs" / "002-intraday-replay-mvp" / "contracts" / "replay-csv-schema.json"
    schema = json.loads(contract_path.read_text(encoding="utf-8"))

    assert schema["properties"]["amount_since_open"]["minimum"] == 0
    assert schema["properties"]["volume_since_open"]["minimum"] == 0
    for field_name in ("price", "bar_high", "bar_low"):
        assert schema["properties"][field_name]["exclusiveMinimum"] == 0
    assert schema["additionalProperties"] is True


def test_replay_csv_contract_requires_amount_when_volume_is_positive() -> None:
    contract_path = Path(__file__).parents[1] / "specs" / "002-intraday-replay-mvp" / "contracts" / "replay-csv-schema.json"
    schema = json.loads(contract_path.read_text(encoding="utf-8"))

    rule = schema["allOf"][0]
    assert rule["if"]["properties"]["volume_since_open"]["exclusiveMinimum"] == 0
    assert rule["then"]["properties"]["amount_since_open"]["exclusiveMinimum"] == 0
