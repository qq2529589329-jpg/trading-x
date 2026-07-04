from collections.abc import Mapping
from pathlib import Path
import csv
import math

from trading_x.intraday_models import REQUIRED_REPLAY_COLUMNS, ReplayBar, is_clock_time


def load_replay_bars(input_path: Path, trade_date: str) -> tuple[list[ReplayBar], str | None]:
    try:
        with input_path.open(newline="", encoding="utf-8-sig") as file:
            reader = csv.DictReader(file)
            fieldnames = reader.fieldnames or ()
            if fieldnames and (len(fieldnames) != len(set(fieldnames)) or any(name.strip() == "" for name in fieldnames)):
                return [], "REPLAY_CSV_INVALID_HEADER"
            missing = sorted(REQUIRED_REPLAY_COLUMNS - set(fieldnames))
            if missing:
                return [], "REPLAY_CSV_MISSING_REQUIRED_COLUMNS: " + ",".join(missing)
            rows = [bar_from_replay_row(row) for row in reader]
    except FileNotFoundError:
        if len(trade_date) != 8 or not trade_date.isdigit():
            return [], "REPLAY_DATE_INVALID"
        return [], "REPLAY_CSV_FILE_NOT_FOUND"
    except OSError:
        if len(trade_date) != 8 or not trade_date.isdigit():
            return [], "REPLAY_DATE_INVALID"
        return [], "REPLAY_CSV_UNREADABLE"
    except (KeyError, TypeError, ValueError):
        return [], "REPLAY_CSV_INVALID_ROW"
    if len(trade_date) != 8 or not trade_date.isdigit():
        return [], "REPLAY_DATE_INVALID"
    if [bar.trade_date for bar in rows if bar.trade_date != trade_date]:
        return [], "REPLAY_CSV_DATE_MISMATCH"
    latest_by_symbol: dict[str, ReplayBar] = {}
    seen_points: set[tuple[str, str]] = set()
    for bar in sorted(rows, key=lambda item: (item.ts_code, item.quote_time)):
        point = (bar.ts_code, bar.quote_time)
        if point in seen_points:
            return [], "REPLAY_CSV_INVALID_ROW"
        seen_points.add(point)
        previous = latest_by_symbol.get(bar.ts_code)
        if previous is not None and (
            bar.amount_since_open < previous.amount_since_open
            or bar.volume_since_open < previous.volume_since_open
        ):
            return [], "REPLAY_CSV_INVALID_ROW"
        latest_by_symbol[bar.ts_code] = bar
    return rows, None


def bar_from_replay_row(row: Mapping[str, str]) -> ReplayBar:
    if None in row:
        raise ValueError
    if any(row[column] is None for column in REQUIRED_REPLAY_COLUMNS):
        raise ValueError
    if len(row["trade_date"]) != 8 or not row["trade_date"].isdigit():
        raise ValueError
    if not is_clock_time(row["quote_time"]):
        raise ValueError
    ts_code = row["ts_code"].strip()
    if ts_code == "":
        raise ValueError
    amount_since_open = float(row["amount_since_open"])
    volume_since_open = float(row["volume_since_open"])
    price = float(row["price"])
    bar_high = float(row["bar_high"])
    bar_low = float(row["bar_low"])
    if (
        not all(math.isfinite(value) for value in (amount_since_open, volume_since_open, price, bar_high, bar_low))
        or amount_since_open < 0
        or volume_since_open < 0
        or (volume_since_open > 0 and amount_since_open <= 0)
        or price <= 0
        or bar_high <= 0
        or bar_low <= 0
        or bar_high < bar_low
        or price < bar_low
        or price > bar_high
    ):
        raise ValueError
    return ReplayBar(
        trade_date=row["trade_date"],
        quote_time=row["quote_time"],
        ts_code=ts_code,
        price=price,
        amount_since_open=amount_since_open,
        volume_since_open=volume_since_open,
        bar_high=bar_high,
        bar_low=bar_low,
    )
