from pathlib import Path
import json

import pytest
from jsonschema import Draft202012Validator, ValidationError

from trading_x.provider_evaluation import (
    ProviderSampleInputError,
    ProviderSource,
    ValidationStatus,
    parse_provider_snapshot_sample,
)


CONTRACT_PATH = (
    Path(__file__).parents[1]
    / "specs"
    / "004-real-provider-evaluation"
    / "contracts"
    / "provider-snapshot-sample-schema.json"
)


def _sample_row() -> dict[str, str | int | float | list[str]]:
    return {
        "trade_date": "20260704",
        "quote_time": "09:35:00",
        "ts_code": "300001.SZ",
        "price": 10.5,
        "amount_since_open": 1050000.0,
        "volume_since_open": 100000.0,
        "bar_high": 10.6,
        "bar_low": 10.1,
        "previous_close": 10.0,
        "limit_up": 11.0,
        "limit_down": 9.0,
        "source": "mootdx",
        "latency_ms": 25,
        "validation_status": "accepted",
        "reason_codes": [],
    }


def _validator() -> Draft202012Validator:
    schema = json.loads(CONTRACT_PATH.read_text(encoding="utf-8"))
    return Draft202012Validator(schema)


def test_provider_snapshot_sample_contract_accepts_valid_row() -> None:
    # Given
    row = _sample_row()

    # When / Then
    _validator().validate(row)


def test_provider_snapshot_sample_contract_rejects_missing_volume() -> None:
    # Given
    row = _sample_row()
    del row["volume_since_open"]

    # When / Then
    with pytest.raises(ValidationError):
        _validator().validate(row)


def test_provider_snapshot_sample_contract_rejects_empty_quote_time() -> None:
    # Given
    row = _sample_row()
    row["quote_time"] = ""

    # When / Then
    with pytest.raises(ValidationError):
        _validator().validate(row)


def test_provider_sample_parser_returns_typed_sample() -> None:
    # Given
    row = _sample_row()

    # When
    sample = parse_provider_snapshot_sample(row)

    # Then
    assert sample.trade_date == "20260704"
    assert sample.source == ProviderSource.MOOTDX
    assert sample.validation_status == ValidationStatus.ACCEPTED
    assert sample.reason_codes == ()


def test_provider_sample_parser_rejects_missing_volume() -> None:
    # Given
    row = _sample_row()
    del row["volume_since_open"]

    # When / Then
    with pytest.raises(ProviderSampleInputError) as error:
        parse_provider_snapshot_sample(row)
    assert error.value.reason_code == "PROVIDER_SAMPLE_MISSING_REQUIRED_FIELDS: volume_since_open"


def test_provider_sample_parser_rejects_empty_quote_time() -> None:
    # Given
    row = _sample_row()
    row["quote_time"] = ""

    # When / Then
    with pytest.raises(ProviderSampleInputError) as error:
        parse_provider_snapshot_sample(row)
    assert error.value.reason_code == "PROVIDER_SAMPLE_INVALID_QUOTE_TIME"
