import sqlite3


def is_limit_close(close: float, up_limit: float) -> bool:
    return up_limit > 0 and close >= up_limit - 0.001


def is_capacity_breakout(row: sqlite3.Row) -> bool:
    return row[6] >= 5.0 and row[8] >= 3.0 and row[5] >= row[3] * 0.96
