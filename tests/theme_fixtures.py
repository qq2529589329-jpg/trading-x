from pathlib import Path
import sqlite3


def insert_theme_market_fixture(db_path: Path) -> None:
    with sqlite3.connect(db_path) as conn:
        conn.executemany(
            "INSERT INTO theme_members ("
            "ts_code, name, industry, theme_primary, theme_tags, theme_source, "
            "confidence, updated_at, notes"
            ") VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
            [
                ("000001.SZ", "空间龙一", "机器人", "机器人", "机器人;减速器", "manual", "MEDIUM", "2026-06-30", ""),
                ("000002.SZ", "空间龙二", "机器人", "机器人", "机器人;执行器", "manual", "MEDIUM", "2026-06-30", ""),
                ("000003.SZ", "容量龙", "机器人", "机器人", "机器人;智能制造", "manual", "MEDIUM", "2026-06-30", ""),
            ],
        )
        conn.executemany(
            "INSERT INTO stock_universe ("
            "ts_code, symbol, name, exchange, market, list_date, "
            "is_st, is_delisting_risk, included, excluded_reason"
            ") VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            [
                ("000001.SZ", "000001", "空间龙一", "SZSE", "主板", "20200101", 0, 0, 1, None),
                ("000002.SZ", "000002", "空间龙二", "SZSE", "主板", "20200101", 0, 0, 1, None),
                ("000003.SZ", "000003", "容量龙", "SZSE", "主板", "20200101", 0, 0, 1, None),
                ("000004.SZ", "000004", "AI龙", "SZSE", "主板", "20200101", 0, 0, 1, None),
            ],
        )
        conn.executemany(
            "INSERT INTO daily_quotes ("
            "trade_date, ts_code, open, high, low, close, pre_close, pct_chg, vol, amount"
            ") VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            [
                ("20260630", "000001.SZ", 10.0, 11.0, 9.9, 11.0, 10.0, 10.0, 1.0, 1000.0),
                ("20260630", "000002.SZ", 20.0, 22.0, 19.8, 22.0, 20.0, 10.0, 1.0, 900.0),
                ("20260630", "000003.SZ", 30.0, 31.5, 29.8, 31.0, 30.0, 3.3, 1.0, 800.0),
                ("20260630", "000004.SZ", 40.0, 40.5, 39.5, 40.2, 40.0, 0.5, 1.0, 100.0),
            ],
        )
        conn.executemany(
            "INSERT INTO stk_limit_prices (trade_date, ts_code, pre_close, up_limit, down_limit) "
            "VALUES (?, ?, ?, ?, ?)",
            [
                ("20260630", "000001.SZ", 10.0, 11.0, 9.0),
                ("20260630", "000002.SZ", 20.0, 22.0, 18.0),
                ("20260630", "000003.SZ", 30.0, 33.0, 27.0),
                ("20260630", "000004.SZ", 40.0, 44.0, 36.0),
            ],
        )
        conn.executemany(
            "INSERT INTO candidates ("
            "trade_date, ts_code, strategy_type, candidate_grade, risk_pass, market_status"
            ") VALUES (?, ?, ?, ?, ?, ?)",
            [
                ("20260630", "000001.SZ", "A_SPACE_LEADER", "A_LITE", 1, "观察"),
                ("20260630", "000004.SZ", "B_CAPACITY_LEADER", "B_CORE", 1, "观察"),
            ],
        )
