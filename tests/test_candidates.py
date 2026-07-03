from pathlib import Path
import json
import sqlite3

from trading_x.capabilities import API_DEFINITIONS, ApiCheckResult, persist_capabilities
from trading_x.db import init_db
from trading_x.reports import generate_report
from trading_x.themes import refresh_theme_daily_strength
from trading_x.types import CandidateGrade, Confidence, DataCapabilityLevel, StrategyType


def test_report_selects_a_lite_and_b_candidates_with_required_plan_fields(
    tmp_path: Path,
) -> None:
    db_path = tmp_path / "trading_x.db"
    report_dir = tmp_path / "reports"
    init_db(db_path)
    _persist_all_capabilities(db_path, unavailable={"limit_cpt_list", "top_list"})
    _insert_candidate_fixture(db_path)

    snapshot = generate_report(db_path, "20260701", report_dir)
    payload = json.loads((report_dir / "20260701_report.json").read_text(encoding="utf-8"))

    assert snapshot.data_capability == DataCapabilityLevel.BASIC
    assert snapshot.allow_new_position is True
    assert len(payload["candidates"]) == 2
    first = payload["candidates"][0]
    assert first["strategy_type"] == StrategyType.A_SPACE_LEADER
    assert first["candidate_grade"] == CandidateGrade.A_LITE
    assert first["theme_name"] == "机器人"
    assert first["data_confidence"] == Confidence.MEDIUM
    assert first["theme_confidence"] == Confidence.MEDIUM
    assert first["event_confidence"] == Confidence.LOW
    for field in (
        "entry_reason",
        "veto_items",
        "buy_observation",
        "abandon_conditions",
        "max_chase_limit",
        "structural_stop",
        "suggested_position",
        "max_loss",
    ):
        assert first[field]


def test_limit_event_promotes_a_candidate_to_a_strong(tmp_path: Path) -> None:
    db_path = tmp_path / "trading_x.db"
    report_dir = tmp_path / "reports"
    init_db(db_path)
    _persist_all_capabilities(db_path)
    _insert_candidate_fixture(db_path)
    with sqlite3.connect(db_path) as conn:
        conn.execute(
            "INSERT INTO limit_events ("
            "trade_date, ts_code, limit_type, is_limit_close, first_limit_time, "
            "last_limit_time, open_times, limit_break_count, seal_amount, "
            "event_confidence, data_source"
            ") VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (
                "20260701",
                "000001.SZ",
                "UP",
                1,
                "09:35:00",
                "14:55:00",
                1,
                0,
                120000000.0,
                "HIGH",
                "event_feed",
            ),
        )

    snapshot = generate_report(db_path, "20260701", report_dir)

    assert snapshot.candidates[0].candidate_grade == CandidateGrade.A_STRONG
    assert snapshot.candidates[0].event_confidence == Confidence.HIGH


def test_p0_missing_blocks_candidates_even_when_market_rows_exist(tmp_path: Path) -> None:
    db_path = tmp_path / "trading_x.db"
    report_dir = tmp_path / "reports"
    init_db(db_path)
    _persist_all_capabilities(db_path, unavailable={"daily_basic"})
    _insert_candidate_fixture(db_path)

    snapshot = generate_report(db_path, "20260701", report_dir)

    assert snapshot.data_capability == DataCapabilityLevel.DEGRADED
    assert snapshot.candidates == []
    assert snapshot.allow_new_position is False


def test_candidates_exclude_risk_failed_stocks_and_cap_at_five(tmp_path: Path) -> None:
    db_path = tmp_path / "trading_x.db"
    report_dir = tmp_path / "reports"
    init_db(db_path)
    _persist_all_capabilities(db_path)
    _insert_many_limit_candidates(db_path)

    snapshot = generate_report(db_path, "20260701", report_dir)

    assert len(snapshot.candidates) == 5
    assert "000999.SZ" not in {candidate.ts_code for candidate in snapshot.candidates}


def test_report_explains_candidate_with_local_theme_fallback(tmp_path: Path) -> None:
    db_path = tmp_path / "trading_x.db"
    report_dir = tmp_path / "reports"
    init_db(db_path)
    _persist_all_capabilities(db_path, unavailable={"limit_cpt_list"})
    _insert_candidate_fixture(db_path)
    with sqlite3.connect(db_path) as conn:
        conn.execute("DELETE FROM theme_strength")
        conn.executemany(
            "INSERT INTO theme_members ("
            "ts_code, name, industry, theme_primary, theme_tags, theme_source, "
            "confidence, updated_at, notes"
            ") VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
            [
                ("000001.SZ", "空间龙", "机器人", "机器人", "机器人;减速器", "manual", "MEDIUM", "2026-06-30", ""),
                ("300001.SZ", "容量龙", "机器人", "机器人", "机器人;智能制造", "manual", "MEDIUM", "2026-06-30", ""),
                ("000002.SZ", "助攻股", "机器人", "机器人", "机器人;执行器", "manual", "MEDIUM", "2026-06-30", ""),
            ],
        )
        conn.execute(
            "INSERT INTO stock_universe ("
            "ts_code, symbol, name, exchange, market, list_date, "
            "is_st, is_delisting_risk, included, excluded_reason"
            ") VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            ("000002.SZ", "000002", "助攻股", "SZSE", "主板", "20200101", 0, 0, 1, None),
        )
        conn.execute(
            "INSERT INTO daily_quotes ("
            "trade_date, ts_code, open, high, low, close, pre_close, pct_chg, vol, amount"
            ") VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            ("20260701", "000002.SZ", 10.0, 10.5, 9.8, 10.3, 10.0, 3.0, 1000.0, 100000.0),
        )
        conn.execute(
            "INSERT INTO stk_limit_prices (trade_date, ts_code, pre_close, up_limit, down_limit) "
            "VALUES (?, ?, ?, ?, ?)",
            ("20260701", "000002.SZ", 10.0, 11.0, 9.0),
        )
    refresh_theme_daily_strength(db_path, "20260701")

    generate_report(db_path, "20260701", report_dir)
    payload = json.loads((report_dir / "20260701_report.json").read_text(encoding="utf-8"))
    first = payload["candidates"][0]

    assert payload["data_capability"] == "BASIC_WITH_THEME_FALLBACK"
    assert first["theme_name"] == "机器人"
    assert first["theme_tags"] == "机器人;减速器"
    assert first["theme_rank_today"] == 1
    assert first["theme_strength_score"] > 0
    assert first["theme_confidence"] == Confidence.MEDIUM


def _persist_all_capabilities(db_path: Path, unavailable: set[str] | None = None) -> None:
    missing = unavailable or set()
    persist_capabilities(
        db_path,
        [
            ApiCheckResult(api_name=definition.name, available=definition.name not in missing)
            for definition in API_DEFINITIONS
        ],
    )


def _insert_candidate_fixture(db_path: Path) -> None:
    with sqlite3.connect(db_path) as conn:
        conn.executemany(
            "INSERT INTO stock_universe ("
            "ts_code, symbol, name, exchange, market, list_date, "
            "is_st, is_delisting_risk, included, excluded_reason"
            ") VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            [
                ("000001.SZ", "000001", "空间龙", "SZSE", "主板", "20200101", 0, 0, 1, None),
                ("300001.SZ", "300001", "容量龙", "SZSE", "创业板", "20200101", 0, 0, 1, None),
            ],
        )
        conn.executemany(
            "INSERT INTO daily_quotes ("
            "trade_date, ts_code, open, high, low, close, pre_close, pct_chg, vol, amount"
            ") VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            [
                ("20260701", "000001.SZ", 10.2, 11.0, 10.1, 11.0, 10.0, 10.0, 90000, 360000),
                ("20260701", "300001.SZ", 20.0, 21.5, 19.8, 21.2, 20.0, 6.0, 120000, 520000),
            ],
        )
        conn.executemany(
            "INSERT INTO daily_basic ("
            "trade_date, ts_code, turnover_rate, volume_ratio, pe_ttm, pb, total_mv, circ_mv"
            ") VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            [
                ("20260701", "000001.SZ", 9.0, 2.2, 28.0, 3.0, 800000, 400000),
                ("20260701", "300001.SZ", 5.5, 1.9, 32.0, 4.0, 1200000, 600000),
            ],
        )
        conn.executemany(
            "INSERT INTO stk_limit_prices (trade_date, ts_code, pre_close, up_limit, down_limit) "
            "VALUES (?, ?, ?, ?, ?)",
            [
                ("20260701", "000001.SZ", 10.0, 11.0, 9.0),
                ("20260701", "300001.SZ", 20.0, 24.0, 16.0),
            ],
        )
        conn.execute(
            "INSERT INTO theme_strength ("
            "trade_date, theme_name, strength_level, theme_confidence, limit_count, "
            "candidate_count, leading_stock, data_source, reason"
            ") VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (
                "20260701",
                "机器人",
                "中强",
                "MEDIUM",
                3,
                2,
                "000001.SZ",
                "concept_mapping",
                "涨停数量 + 概念映射，未接入高质量强势板块接口",
            ),
        )


def _insert_many_limit_candidates(db_path: Path) -> None:
    stock_rows = []
    daily_rows = []
    basic_rows = []
    limit_rows = []
    for index in range(6):
        ts_code = f"00000{index}.SZ"
        close = 11.0 + index
        stock_rows.append(
            (ts_code, f"00000{index}", f"空间龙{index}", "SZSE", "主板", "20200101", 0, 0, 1, None)
        )
        daily_rows.append(
            ("20260701", ts_code, close - 0.5, close, close - 1.0, close, close - 1.0, 10.0, 90000, 300000 + index)
        )
        basic_rows.append(("20260701", ts_code, 8.0, 2.0, 25.0, 3.0, 800000, 400000))
        limit_rows.append(("20260701", ts_code, close - 1.0, close, close - 2.0))
    stock_rows.append(("000999.SZ", "000999", "ST风险", "SZSE", "主板", "20200101", 1, 1, 0, "st"))
    daily_rows.append(("20260701", "000999.SZ", 30.0, 33.0, 29.0, 33.0, 30.0, 10.0, 90000, 900000))
    basic_rows.append(("20260701", "000999.SZ", 12.0, 3.0, 25.0, 3.0, 800000, 400000))
    limit_rows.append(("20260701", "000999.SZ", 30.0, 33.0, 27.0))
    with sqlite3.connect(db_path) as conn:
        conn.executemany(
            "INSERT INTO stock_universe ("
            "ts_code, symbol, name, exchange, market, list_date, "
            "is_st, is_delisting_risk, included, excluded_reason"
            ") VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            stock_rows,
        )
        conn.executemany(
            "INSERT INTO daily_quotes ("
            "trade_date, ts_code, open, high, low, close, pre_close, pct_chg, vol, amount"
            ") VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            daily_rows,
        )
        conn.executemany(
            "INSERT INTO daily_basic ("
            "trade_date, ts_code, turnover_rate, volume_ratio, pe_ttm, pb, total_mv, circ_mv"
            ") VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            basic_rows,
        )
        conn.executemany(
            "INSERT INTO stk_limit_prices (trade_date, ts_code, pre_close, up_limit, down_limit) "
            "VALUES (?, ?, ?, ?, ?)",
            limit_rows,
        )
