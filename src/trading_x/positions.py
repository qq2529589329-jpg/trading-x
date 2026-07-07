from collections.abc import Mapping
from dataclasses import dataclass
from typing import Final, TypeAlias
import json
import math


PositionLedgerValue: TypeAlias = str | int | float
PositionLedgerPayload: TypeAlias = Mapping[str, PositionLedgerValue]

REQUIRED_POSITION_LEDGER_FIELDS: Final = frozenset(
    {
        "trade_date",
        "ts_code",
        "total_shares",
        "available_shares",
        "avg_cost",
        "market_value",
    }
)


class PositionLedgerInputError(ValueError):
    reason_code: str

    def __init__(self, reason_code: str) -> None:
        self.reason_code = reason_code
        super().__init__(reason_code)


@dataclass(frozen=True, slots=True)
class PositionLedgerRow:
    trade_date: str
    ts_code: str
    total_shares: float
    available_shares: float
    avg_cost: float
    market_value: float
    name: str | None = None


def parse_position_ledger_file_text(text: str) -> tuple[PositionLedgerRow, ...]:
    try:
        payload = json.loads(text)
    except json.JSONDecodeError as exc:
        raise PositionLedgerInputError("POSITION_LEDGER_INVALID_JSON") from exc
    if not isinstance(payload, list):
        raise PositionLedgerInputError("POSITION_LEDGER_FILE_NOT_ARRAY")
    if not payload:
        raise PositionLedgerInputError("POSITION_LEDGER_FILE_EMPTY")
    return tuple(parse_position_ledger_row(_ledger_payload(item)) for item in payload)


def parse_position_ledger_row(row: PositionLedgerPayload) -> PositionLedgerRow:
    missing = sorted(REQUIRED_POSITION_LEDGER_FIELDS - set(row))
    if missing:
        raise PositionLedgerInputError("POSITION_LEDGER_MISSING_REQUIRED_FIELDS: " + ",".join(missing))

    trade_date = _required_text(row, "trade_date")
    if len(trade_date) != 8 or not trade_date.isdigit():
        raise PositionLedgerInputError("POSITION_LEDGER_INVALID_TRADE_DATE")

    ts_code = _required_text(row, "ts_code")
    if ts_code == "":
        raise PositionLedgerInputError("POSITION_LEDGER_INVALID_TS_CODE")

    total_shares = _required_float(row, "total_shares")
    available_shares = _required_float(row, "available_shares")
    avg_cost = _required_float(row, "avg_cost")
    market_value = _required_float(row, "market_value")
    if total_shares < 0 or available_shares < 0 or avg_cost < 0 or market_value < 0:
        raise PositionLedgerInputError("POSITION_LEDGER_INVALID_NUMERIC_BOUNDS")

    return PositionLedgerRow(
        trade_date=trade_date,
        ts_code=ts_code,
        name=_optional_text(row, "name"),
        total_shares=total_shares,
        available_shares=available_shares,
        avg_cost=avg_cost,
        market_value=market_value,
    )


def _ledger_payload(item) -> PositionLedgerPayload:
    if not isinstance(item, Mapping):
        raise PositionLedgerInputError("POSITION_LEDGER_ROW_NOT_OBJECT")
    row: dict[str, PositionLedgerValue] = {}
    for key, value in item.items():
        if not isinstance(key, str):
            raise PositionLedgerInputError("POSITION_LEDGER_INVALID_FIELD_NAME")
        row[key] = _ledger_value(value)
    return row


def _ledger_value(value) -> PositionLedgerValue:
    if isinstance(value, bool):
        raise PositionLedgerInputError("POSITION_LEDGER_INVALID_FIELD_VALUE")
    if isinstance(value, str | int | float):
        return value
    raise PositionLedgerInputError("POSITION_LEDGER_INVALID_FIELD_VALUE")


def _required_text(row: PositionLedgerPayload, field_name: str) -> str:
    value = row[field_name]
    if not isinstance(value, str):
        raise PositionLedgerInputError(f"POSITION_LEDGER_INVALID_TEXT: {field_name}")
    return value.strip()


def _optional_text(row: PositionLedgerPayload, field_name: str) -> str | None:
    if field_name not in row:
        return None
    return _required_text(row, field_name)


def _required_float(row: PositionLedgerPayload, field_name: str) -> float:
    value = row[field_name]
    if isinstance(value, str):
        raise PositionLedgerInputError(f"POSITION_LEDGER_INVALID_NUMBER: {field_name}")
    number = float(value)
    if not math.isfinite(number):
        raise PositionLedgerInputError(f"POSITION_LEDGER_INVALID_NUMBER: {field_name}")
    return number