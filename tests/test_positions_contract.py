from pathlib import Path
import json

import pytest
from jsonschema import Draft202012Validator, ValidationError

from trading_x.positions import (
    PositionLedgerInputError,
    parse_position_ledger_file_text,
    parse_position_ledger_row,
)


CONTRACT_PATH = (
    Path(__file__).parents[1]
    / "specs"
    / "005-positions-sell-risk"
    / "contracts"
    / "position-ledger-schema.json"
)


def _ledger_row() -> dict[str, str | float]:
    return {
        "trade_date": "20260706",
        "ts_code": "300001.SZ",
        "name": "容量龙",
        "total_shares": 1000.0,
        "available_shares": 500.0,
        "avg_cost": 10.2,
        "market_value": 10500.0,
    }


def _validator() -> Draft202012Validator:
    schema = json.loads(CONTRACT_PATH.read_text(encoding="utf-8"))
    return Draft202012Validator(schema)


def test_position_ledger_contract_accepts_valid_rows() -> None:
    # Given
    row = _ledger_row()

    # When / Then
    _validator().validate([row])


def test_position_ledger_contract_rejects_missing_available_shares() -> None:
    # Given
    row = _ledger_row()
    del row["available_shares"]

    # When / Then
    with pytest.raises(ValidationError):
        _validator().validate([row])


@pytest.mark.parametrize("field_name", ["total_shares", "available_shares", "avg_cost", "market_value"])
def test_position_ledger_contract_rejects_negative_numeric_fields(field_name: str) -> None:
    # Given
    row = _ledger_row()
    row[field_name] = -1.0

    # When / Then
    with pytest.raises(ValidationError):
        _validator().validate([row])


def test_position_ledger_parser_returns_typed_row() -> None:
    # Given
    row = _ledger_row()

    # When
    position = parse_position_ledger_row(row)

    # Then
    assert position.trade_date == "20260706"
    assert position.ts_code == "300001.SZ"
    assert position.name == "容量龙"
    assert position.available_shares == 500.0


def test_position_ledger_file_parser_returns_rows() -> None:
    # Given
    text = json.dumps([_ledger_row()], ensure_ascii=False)

    # When
    positions = parse_position_ledger_file_text(text)

    # Then
    assert len(positions) == 1
    assert positions[0].total_shares == 1000.0


def test_position_ledger_parser_rejects_missing_available_shares() -> None:
    # Given
    row = _ledger_row()
    del row["available_shares"]

    # When / Then
    with pytest.raises(PositionLedgerInputError) as error:
        parse_position_ledger_row(row)
    assert error.value.reason_code == "POSITION_LEDGER_MISSING_REQUIRED_FIELDS: available_shares"


@pytest.mark.parametrize("field_name", ["total_shares", "available_shares", "avg_cost", "market_value"])
def test_position_ledger_parser_rejects_negative_numeric_fields(field_name: str) -> None:
    # Given
    row = _ledger_row()
    row[field_name] = -1.0

    # When / Then
    with pytest.raises(PositionLedgerInputError) as error:
        parse_position_ledger_row(row)
    assert error.value.reason_code == "POSITION_LEDGER_INVALID_NUMERIC_BOUNDS"