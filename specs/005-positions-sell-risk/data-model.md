# Data Model: Positions Sell Risk MVP

## `position_import_runs`

Records reproducible position ledger imports.

| Field | Type | Notes |
| --- | --- | --- |
| `id` | INTEGER PRIMARY KEY | Autoincrement run id |
| `trade_date` | TEXT | `YYYYMMDD` |
| `input_file` | TEXT | Ledger path |
| `input_sha256` | TEXT | Hash of imported ledger |
| `position_count` | INTEGER | Imported rows |
| `status` | TEXT | `SUCCESS` or `FAILED` |
| `started_at` | TEXT | UTC timestamp |
| `ended_at` | TEXT | UTC timestamp |
| `error_message` | TEXT | Nullable |

## `positions`

Current structured position snapshot for a trade date.

| Field | Type | Notes |
| --- | --- | --- |
| `trade_date` | TEXT | `YYYYMMDD` |
| `ts_code` | TEXT | Stock code |
| `name` | TEXT | Optional stock name |
| `total_shares` | REAL | Held shares |
| `available_shares` | REAL | Sellable shares |
| `avg_cost` | REAL | Average cost |
| `market_value` | REAL | Snapshot market value |
| `source` | TEXT | `csv` or `json` |
| `source_run_id` | INTEGER | Links to `position_import_runs.id` |
| `created_at` | TEXT | UTC timestamp |

Primary key: `(trade_date, ts_code)`.

## Alert Position Context

Sell-side alerts continue to use `intraday_alerts`.

The alert `snapshot_json` should include:

- `price`
- `bar_high`
- `bar_low`
- `total_shares`
- `available_shares`
- `avg_cost`
- `market_value`

## Alert Locks

Sell-side terminal alerts continue to use `intraday_alert_locks`.

Lock key:

- `trade_date`
- `ts_code`
- `strategy_type`
- `alert_type`
