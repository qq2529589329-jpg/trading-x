# Data Model: Intraday Live Watch

## IntradaySnapshot

Typed market snapshot returned by `IntradayDataProvider`.

Required fields:

- `trade_date`
- `quote_time`
- `ts_code`
- `price`
- `amount_since_open`
- `volume_since_open`
- `bar_high`
- `bar_low`

Rules:

- `trade_date` must match the watch command date.
- `quote_time` must be a zero-padded `HH:MM:SS` clock time.
- `ts_code` must be requested from same-date `intraday_plans`.
- `amount_since_open` and `volume_since_open` are cumulative values from market open.
- `continuous_vwap = amount_since_open / volume_since_open` when volume is positive.
- Missing cumulative volume rejects the snapshot before B-class rules run.
- `price`, `bar_high`, and `bar_low` must satisfy replay row price bounds.

## IntradayDataProvider

Read-only source contract.

Minimum signature:

```python
class IntradayDataProvider(Protocol):
    def snapshots(self, symbols: Sequence[str]) -> Sequence[IntradaySnapshot]:
        ...
```

Rules:

- Provider receives the exact plan symbol set.
- Provider must not create, rank, or add symbols.
- Provider must not know strategy rules.
- Fake provider is the first implementation and reads fixed fixture rows.
- Real providers remain candidates until field completeness is documented.

## WatchOutput

Initial watch output reuses existing Replay MVP tables:

- `intraday_alerts`
- `intraday_alert_locks`

Rules:

- Watch writes the same alert types and reason codes as replay for B-class rules.
- Watch does not write orders, positions, or sell instructions.
- A new watch-run table is deferred until fake-provider behavior proves useful run metadata.

## ProviderEvaluation

Documentation record for candidate real data sources.

Fields to assess:

- source name
- timestamp availability
- current price availability
- cumulative amount availability
- cumulative volume availability
- high/low availability
- previous close availability
- limit-price availability
- candidate-symbol coverage
- observed latency
- stability notes
- compliance-use notes

Rules:

- A source missing cumulative volume is unsuitable for BUY-trigger watch.
- A source missing trustworthy timestamp is unsuitable for live watch.
- Provider evaluation does not make a source the default runtime provider.
