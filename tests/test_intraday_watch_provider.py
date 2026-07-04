import pytest

from trading_x.intraday_watch import (
    FakeIntradayProvider,
    IntradayProviderInputError,
    IntradaySnapshot,
)


def _row(ts_code: str = "300001.SZ") -> dict[str, str]:
    return {
        "trade_date": "20260630",
        "quote_time": "09:35:00",
        "ts_code": ts_code,
        "price": "10.50",
        "amount_since_open": "1050000",
        "volume_since_open": "100000",
        "bar_high": "10.60",
        "bar_low": "10.10",
    }


def test_intraday_snapshot_parses_replay_style_row() -> None:
    # Given
    provider = FakeIntradayProvider.from_rows([_row()])

    # When
    snapshot = provider.snapshots({"300001.SZ"})[0]

    # Then
    assert isinstance(snapshot, IntradaySnapshot)
    assert snapshot.trade_date == "20260630"
    assert snapshot.quote_time == "09:35:00"
    assert snapshot.price == 10.5
    assert snapshot.continuous_vwap == 10.5


def test_intraday_snapshot_rejects_missing_volume_before_rules() -> None:
    # Given
    row = _row()
    del row["volume_since_open"]

    # When / Then
    with pytest.raises(IntradayProviderInputError) as error:
        FakeIntradayProvider.from_rows([row])
    assert str(error.value) == "WATCH_SNAPSHOT_MISSING_REQUIRED_COLUMNS: volume_since_open"


def test_fake_intraday_provider_returns_only_requested_symbols() -> None:
    # Given
    provider = FakeIntradayProvider.from_rows([_row("300001.SZ"), _row("600001.SH")])

    # When
    snapshots = provider.snapshots({"600001.SH"})

    # Then
    assert [snapshot.ts_code for snapshot in snapshots] == ["600001.SH"]
