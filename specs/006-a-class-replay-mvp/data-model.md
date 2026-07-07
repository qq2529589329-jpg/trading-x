# Data Model: A-Class Replay MVP

No new tables are introduced.

## `intraday_plans`

A-class rows use the existing primary key `(trade_date, ts_code, strategy_type)` with `strategy_type = A_SPACE_LEADER`.

Minimum A-class machine fields:

- `entry_low`, `entry_high`, `breakout_price`: deterministic A-class trigger price from structured limit/daily price data.
- `stop_price`: deterministic pre-buy invalidation price.
- `vwap_active_after`: `09:30:00`.
- `vwap_above_confirm_seconds`: `0`.
- `volume_gate_enabled`: `0`.
- `plan_json`: generated machine payload, not Markdown text.

## `intraday_alerts`

A-class replay writes existing alert rows with A-specific `reason_code`, starting with `A_BUY_TRIGGERED`.

## `intraday_replay_runs`

Replay run recording is unchanged; it still stores `input_sha256`, counts, status, timing, and error message.
