from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from enum import StrEnum
from typing import Final, TypeAlias
import json
import math
import re

from trading_x.intraday_models import is_clock_time


ProviderSampleValue: TypeAlias = str | int | float | Sequence[str]
ProviderSamplePayload: TypeAlias = Mapping[str, ProviderSampleValue]

REQUIRED_PROVIDER_SAMPLE_FIELDS: Final = frozenset(
    {
        "trade_date",
        "quote_time",
        "ts_code",
        "price",
        "amount_since_open",
        "volume_since_open",
        "bar_high",
        "bar_low",
        "source",
        "latency_ms",
        "validation_status",
        "reason_codes",
    }
)
_SHA256_PATTERN: Final = re.compile(r"^[a-f0-9]{64}$")


class ProviderSource(StrEnum):
    MOOTDX = "mootdx"
    TENCENT_SNAPSHOT = "tencent_snapshot"


class ValidationStatus(StrEnum):
    ACCEPTED = "accepted"
    REJECTED = "rejected"


class ProviderSampleInputError(ValueError):
    reason_code: str

    def __init__(self, reason_code: str) -> None:
        self.reason_code = reason_code
        super().__init__(reason_code)


@dataclass(frozen=True, slots=True)
class ProviderSnapshotSample:
    trade_date: str
    quote_time: str
    ts_code: str
    price: float
    amount_since_open: float
    volume_since_open: float
    bar_high: float
    bar_low: float
    source: ProviderSource
    latency_ms: int
    validation_status: ValidationStatus
    reason_codes: tuple[str, ...]
    previous_close: float | None = None
    limit_up: float | None = None
    limit_down: float | None = None
    raw_payload_sha256: str | None = None


def parse_provider_sample_file_text(text: str) -> tuple[ProviderSnapshotSample, ...]:
    try:
        payload = json.loads(text)
    except json.JSONDecodeError as exc:
        raise ProviderSampleInputError("PROVIDER_SAMPLE_INVALID_JSON") from exc
    if not isinstance(payload, list):
        raise ProviderSampleInputError("PROVIDER_SAMPLE_FILE_NOT_ARRAY")
    if not payload:
        raise ProviderSampleInputError("PROVIDER_SAMPLE_FILE_EMPTY")
    return tuple(parse_provider_snapshot_sample(_sample_payload(item)) for item in payload)


def _sample_payload(item) -> ProviderSamplePayload:
    if not isinstance(item, Mapping):
        raise ProviderSampleInputError("PROVIDER_SAMPLE_ROW_NOT_OBJECT")
    row: dict[str, ProviderSampleValue] = {}
    for key, value in item.items():
        if not isinstance(key, str):
            raise ProviderSampleInputError("PROVIDER_SAMPLE_INVALID_FIELD_NAME")
        row[key] = _sample_value(value)
    return row


def _sample_value(value) -> ProviderSampleValue:
    if isinstance(value, bool):
        raise ProviderSampleInputError("PROVIDER_SAMPLE_INVALID_FIELD_VALUE")
    if isinstance(value, str | int | float):
        return value
    if isinstance(value, list) and all(isinstance(item, str) for item in value):
        return tuple(value)
    raise ProviderSampleInputError("PROVIDER_SAMPLE_INVALID_FIELD_VALUE")

def parse_provider_snapshot_sample(row: ProviderSamplePayload) -> ProviderSnapshotSample:
    missing = sorted(REQUIRED_PROVIDER_SAMPLE_FIELDS - set(row))
    if missing:
        raise ProviderSampleInputError(
            "PROVIDER_SAMPLE_MISSING_REQUIRED_FIELDS: " + ",".join(missing)
        )

    trade_date = _required_text(row, "trade_date")
    if len(trade_date) != 8 or not trade_date.isdigit():
        raise ProviderSampleInputError("PROVIDER_SAMPLE_INVALID_TRADE_DATE")

    quote_time = _required_text(row, "quote_time")
    if not is_clock_time(quote_time):
        raise ProviderSampleInputError("PROVIDER_SAMPLE_INVALID_QUOTE_TIME")

    ts_code = _required_text(row, "ts_code")
    if ts_code == "":
        raise ProviderSampleInputError("PROVIDER_SAMPLE_INVALID_TS_CODE")

    price = _required_float(row, "price")
    amount_since_open = _required_float(row, "amount_since_open")
    volume_since_open = _required_float(row, "volume_since_open")
    bar_high = _required_float(row, "bar_high")
    bar_low = _required_float(row, "bar_low")
    if (
        amount_since_open < 0
        or volume_since_open <= 0
        or price <= 0
        or bar_high <= 0
        or bar_low <= 0
        or bar_high < bar_low
        or price < bar_low
        or price > bar_high
    ):
        raise ProviderSampleInputError("PROVIDER_SAMPLE_INVALID_NUMERIC_BOUNDS")

    return ProviderSnapshotSample(
        trade_date=trade_date,
        quote_time=quote_time,
        ts_code=ts_code,
        price=price,
        amount_since_open=amount_since_open,
        volume_since_open=volume_since_open,
        bar_high=bar_high,
        bar_low=bar_low,
        source=_source(row),
        latency_ms=_latency_ms(row),
        validation_status=_validation_status(row),
        reason_codes=_reason_codes(row),
        previous_close=_optional_positive_float(row, "previous_close"),
        limit_up=_optional_positive_float(row, "limit_up"),
        limit_down=_optional_positive_float(row, "limit_down"),
        raw_payload_sha256=_raw_payload_sha256(row),
    )


def _required_text(row: ProviderSamplePayload, field_name: str) -> str:
    value = row[field_name]
    if not isinstance(value, str):
        raise ProviderSampleInputError(f"PROVIDER_SAMPLE_INVALID_TEXT: {field_name}")
    return value.strip()


def _required_float(row: ProviderSamplePayload, field_name: str) -> float:
    value = row[field_name]
    if isinstance(value, str | Sequence):
        raise ProviderSampleInputError(f"PROVIDER_SAMPLE_INVALID_NUMBER: {field_name}")
    number = float(value)
    if not math.isfinite(number):
        raise ProviderSampleInputError(f"PROVIDER_SAMPLE_INVALID_NUMBER: {field_name}")
    return number


def _optional_positive_float(row: ProviderSamplePayload, field_name: str) -> float | None:
    if field_name not in row:
        return None
    number = _required_float(row, field_name)
    if number <= 0:
        raise ProviderSampleInputError(f"PROVIDER_SAMPLE_INVALID_NUMBER: {field_name}")
    return number


def _source(row: ProviderSamplePayload) -> ProviderSource:
    value = _required_text(row, "source")
    match value:
        case ProviderSource.MOOTDX:
            return ProviderSource.MOOTDX
        case ProviderSource.TENCENT_SNAPSHOT:
            return ProviderSource.TENCENT_SNAPSHOT
        case _:
            raise ProviderSampleInputError("PROVIDER_SAMPLE_INVALID_SOURCE")


def _validation_status(row: ProviderSamplePayload) -> ValidationStatus:
    value = _required_text(row, "validation_status")
    match value:
        case ValidationStatus.ACCEPTED:
            return ValidationStatus.ACCEPTED
        case ValidationStatus.REJECTED:
            return ValidationStatus.REJECTED
        case _:
            raise ProviderSampleInputError("PROVIDER_SAMPLE_INVALID_VALIDATION_STATUS")


def _latency_ms(row: ProviderSamplePayload) -> int:
    value = row["latency_ms"]
    if not isinstance(value, int) or value < 0:
        raise ProviderSampleInputError("PROVIDER_SAMPLE_INVALID_LATENCY")
    return value


def _reason_codes(row: ProviderSamplePayload) -> tuple[str, ...]:
    value = row["reason_codes"]
    if isinstance(value, str) or not isinstance(value, Sequence):
        raise ProviderSampleInputError("PROVIDER_SAMPLE_INVALID_REASON_CODES")
    reason_codes = tuple(value)
    if any(not isinstance(reason_code, str) or reason_code == "" for reason_code in reason_codes):
        raise ProviderSampleInputError("PROVIDER_SAMPLE_INVALID_REASON_CODES")
    return reason_codes


def _raw_payload_sha256(row: ProviderSamplePayload) -> str | None:
    if "raw_payload_sha256" not in row:
        return None
    value = _required_text(row, "raw_payload_sha256")
    if _SHA256_PATTERN.fullmatch(value) is None:
        raise ProviderSampleInputError("PROVIDER_SAMPLE_INVALID_RAW_PAYLOAD_SHA256")
    return value
