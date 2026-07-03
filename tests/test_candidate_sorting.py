from pathlib import Path
import sqlite3

from trading_x.candidates import select_candidates
from trading_x.db import init_db
from trading_x.types import DataCapabilityLevel


def test_candidates_sort_theme_strength_before_amount(tmp_path: Path) -> None:
    db_path = tmp_path / "trading_x.db"
    init_db(db_path)
    _insert_sorting_fixture(db_path)

    candidates = select_candidates(
        db_path,
        "20260701",
        DataCapabilityLevel.BASIC_WITH_THEME_FALLBACK,
        {"limit_cpt_list"},
    )

    assert [candidate.ts_code for candidate in candidates[:2]] == [
        "000001.SZ",
        "000002.SZ",
    ]


def _insert_sorting_fixture(db_path: Path) -> None:
    with sqlite3.connect(db_path) as conn:
        conn.executemany(
            "INSERT INTO stock_universe ("
            "ts_code, symbol, name, exchange, market, list_date, "
            "is_st, is_delisting_risk, included, excluded_reason"
            ") VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            [
                ("000001.SZ", "000001", "题材强", "SZSE", "主板", "20200101", 0, 0, 1, None),
                ("000002.SZ", "000002", "成交大", "SZSE", "主板", "20200101", 0, 0, 1, None),
            ],
        )
        conn.executemany(
            "INSERT INTO daily_quotes ("
            "trade_date, ts_code, open, high, low, close, pre_close, pct_chg, vol, amount"
            ") VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            [
                ("20260701", "000001.SZ", 10.0, 11.0, 9.9, 11.0, 10.0, 10.0, 1.0, 200000.0),
                ("20260701", "000002.SZ", 20.0, 22.0, 19.8, 22.0, 20.0, 10.0, 1.0, 900000.0),
            ],
        )
        conn.executemany(
            "INSERT INTO daily_basic ("
            "trade_date, ts_code, turnover_rate, volume_ratio, pe_ttm, pb, total_mv, circ_mv"
            ") VALUES (?, ?, ?, ?, ?, ?, ?, ?)",
            [
                ("20260701", "000001.SZ", 8.0, 2.0, 20.0, 2.0, 100000.0, 80000.0),
                ("20260701", "000002.SZ", 8.0, 2.0, 20.0, 2.0, 100000.0, 80000.0),
            ],
        )
        conn.executemany(
            "INSERT INTO stk_limit_prices (trade_date, ts_code, pre_close, up_limit, down_limit) "
            "VALUES (?, ?, ?, ?, ?)",
            [
                ("20260701", "000001.SZ", 10.0, 11.0, 9.0),
                ("20260701", "000002.SZ", 20.0, 22.0, 18.0),
            ],
        )
        conn.executemany(
            "INSERT INTO theme_members ("
            "ts_code, name, industry, theme_primary, theme_tags, theme_source, "
            "confidence, updated_at, notes"
            ") VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
            [
                ("000001.SZ", "题材强", "机器人", "机器人", "机器人", "manual", "MEDIUM", "2026-06-30", ""),
                ("000002.SZ", "成交大", "电子", "电子", "电子", "manual", "MEDIUM", "2026-06-30", ""),
            ],
        )
        conn.executemany(
            "INSERT INTO theme_daily_strength ("
            "trade_date, theme_name, theme_member_count, theme_up_count, "
            "theme_limit_up_count, theme_avg_pct_chg, theme_total_amount, "
            "theme_candidate_count, theme_strength_score, theme_confidence, core_symbols"
            ") VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            [
                ("20260701", "机器人", 1, 1, 1, 10.0, 200000.0, 1, 95.0, "MEDIUM", "000001.SZ"),
                ("20260701", "电子", 1, 1, 1, 10.0, 900000.0, 1, 40.0, "MEDIUM", "000002.SZ"),
            ],
        )
