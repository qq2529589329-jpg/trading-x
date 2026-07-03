from pathlib import Path
import csv
import sqlite3

import pytest

from trading_x.db import init_db
from trading_x.themes import (
    ThemeCsvError,
    import_theme_members,
    refresh_theme_daily_strength,
)
from theme_fixtures import insert_theme_market_fixture


def test_import_theme_members_csv_upserts_duplicate_codes(tmp_path: Path) -> None:
    db_path = tmp_path / "trading_x.db"
    csv_path = tmp_path / "theme_members.csv"
    init_db(db_path)
    _write_csv(
        csv_path,
        [
            ["300124.SZ", "汇川技术", "自动化设备", "机器人", "机器人;智能制造", "manual", "MEDIUM", "2026-06-30", "旧备注"],
            ["300124.SZ", "汇川技术", "自动化设备", "AI应用", "AI应用;智能制造", "manual", "MEDIUM", "2026-06-30", "新备注"],
        ],
    )

    result = import_theme_members(db_path, csv_path)

    with sqlite3.connect(db_path) as conn:
        row = conn.execute(
            "SELECT theme_primary, theme_tags, notes FROM theme_members WHERE ts_code = ?",
            ("300124.SZ",),
        ).fetchone()
    assert result.imported_count == 2
    assert result.duplicate_count == 1
    assert row == ("AI应用", "AI应用;智能制造", "新备注")


def test_import_theme_members_csv_stores_tier_and_weight(tmp_path: Path) -> None:
    db_path = tmp_path / "trading_x.db"
    csv_path = tmp_path / "theme_members.csv"
    init_db(db_path)
    _write_weighted_csv(
        csv_path,
        [
            [
                "300124.SZ",
                "汇川技术",
                "自动化设备",
                "机器人",
                "机器人;智能制造",
                "CORE",
                "1.0",
                "manual",
                "MEDIUM",
                "2026-06-30",
                "核心容量标的",
            ]
        ],
    )

    import_theme_members(db_path, csv_path)

    with sqlite3.connect(db_path) as conn:
        row = conn.execute(
            "SELECT theme_tier, theme_weight FROM theme_members WHERE ts_code = ?",
            ("300124.SZ",),
        ).fetchone()
    assert row == ("CORE", 1.0)


def test_import_theme_members_csv_defaults_tier_and_weight(tmp_path: Path) -> None:
    db_path = tmp_path / "trading_x.db"
    csv_path = tmp_path / "theme_members.csv"
    init_db(db_path)
    _write_csv(
        csv_path,
        [["300124.SZ", "汇川技术", "自动化设备", "机器人", "机器人", "manual", "MEDIUM", "2026-06-30", ""]],
    )

    import_theme_members(db_path, csv_path)

    with sqlite3.connect(db_path) as conn:
        row = conn.execute(
            "SELECT theme_tier, theme_weight FROM theme_members WHERE ts_code = ?",
            ("300124.SZ",),
        ).fetchone()
    assert row == ("IMPORTANT", 0.7)


def test_import_theme_members_rejects_missing_theme_primary(tmp_path: Path) -> None:
    db_path = tmp_path / "trading_x.db"
    csv_path = tmp_path / "theme_members.csv"
    init_db(db_path)
    _write_csv(
        csv_path,
        [["300124.SZ", "汇川技术", "自动化设备", "", "机器人", "manual", "MEDIUM", "2026-06-30", ""]],
    )

    with pytest.raises(ThemeCsvError):
        import_theme_members(db_path, csv_path)


def test_refresh_theme_daily_strength_aggregates_local_fallback(
    tmp_path: Path,
) -> None:
    db_path = tmp_path / "trading_x.db"
    init_db(db_path)
    insert_theme_market_fixture(db_path)

    count = refresh_theme_daily_strength(db_path, "20260630")

    with sqlite3.connect(db_path) as conn:
        row = conn.execute(
            "SELECT theme_member_count, theme_up_count, theme_limit_up_count, "
            "theme_candidate_count, theme_confidence, core_symbols, weighted_limit_up_count "
            "FROM theme_daily_strength WHERE trade_date = ? AND theme_name = ?",
            ("20260630", "机器人"),
        ).fetchone()
    assert count == 1
    assert row[0:5] == (3, 3, 2, 1, "MEDIUM")
    assert "000001.SZ" in row[5]
    assert row[6] == 1.4


def test_manual_single_member_theme_confidence_is_medium(tmp_path: Path) -> None:
    db_path = tmp_path / "trading_x.db"
    init_db(db_path)
    with sqlite3.connect(db_path) as conn:
        conn.execute(
            "INSERT INTO theme_members ("
            "ts_code, name, industry, theme_primary, theme_tags, theme_source, "
            "confidence, updated_at, notes"
            ") VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
            ("000001.SZ", "样本股", "电子", "半导体", "半导体", "manual", "MEDIUM", "2026-06-30", ""),
        )
        conn.execute(
            "INSERT INTO stock_universe ("
            "ts_code, symbol, name, exchange, market, list_date, "
            "is_st, is_delisting_risk, included, excluded_reason"
            ") VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            ("000001.SZ", "000001", "样本股", "SZSE", "主板", "20200101", 0, 0, 1, None),
        )
        conn.execute(
            "INSERT INTO daily_quotes ("
            "trade_date, ts_code, open, high, low, close, pre_close, pct_chg, vol, amount"
            ") VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            ("20260630", "000001.SZ", 10.0, 11.0, 9.9, 11.0, 10.0, 10.0, 1.0, 1000.0),
        )

    refresh_theme_daily_strength(db_path, "20260630")

    with sqlite3.connect(db_path) as conn:
        confidence = conn.execute(
            "SELECT theme_confidence FROM theme_daily_strength WHERE theme_name = ?",
            ("半导体",),
        ).fetchone()[0]
    assert confidence == "MEDIUM"


def _write_csv(csv_path: Path, rows: list[list[str]]) -> None:
    with csv_path.open("w", encoding="utf-8", newline="") as file:
        writer = csv.writer(file)
        writer.writerow(
            [
                "ts_code",
                "name",
                "industry",
                "theme_primary",
                "theme_tags",
                "theme_source",
                "confidence",
                "updated_at",
                "notes",
            ]
        )
        writer.writerows(rows)


def _write_weighted_csv(csv_path: Path, rows: list[list[str]]) -> None:
    with csv_path.open("w", encoding="utf-8", newline="") as file:
        writer = csv.writer(file)
        writer.writerow(
            [
                "ts_code",
                "name",
                "industry",
                "theme_primary",
                "theme_tags",
                "theme_tier",
                "theme_weight",
                "theme_source",
                "confidence",
                "updated_at",
                "notes",
            ]
        )
        writer.writerows(rows)
