# Data Model: Intraday Replay MVP

## IntradayPlan

Machine-executable snapshot derived from latest structured `candidate_snapshots` and report JSON.
Direct `candidates` materialization is allowed only as a test fixture fallback when no candidate snapshot run exists.

Required MVP fields:

- `trade_date`
- `ts_code`
- `name`
- `strategy_type`
- `allow_trade`
- `plan_status`
- `entry_low`
- `entry_high`
- `breakout_price`
- `stop_price`
- `max_stop_distance`
- `max_position_cash`
- `max_loss`
- `official_pre_close`
- `pre_close_source`
- `vwap_active_after`
- `vwap_above_confirm_seconds`
- `volume_gate_enabled`
- `volume_min_abs_amount`
- `volume_same_window_multiplier`
- `volume_ratio_0935`
- `volume_ratio_0945`
- `volume_ratio_1000`
- `theme_name`
- `theme_confidence`
- `theme_strength_score`
- `source_candidate_id`
- `source_report_date`
- `plan_json`
- `system_version`
- `created_at`

Primary key: `(trade_date, ts_code, strategy_type)`.

Rule: `vwap_active_after` must be a valid zero-padded `HH:MM:SS` clock time.
Rule: missing or `NULL` `vwap_active_after` is invalid and disables the plan before alert evaluation.
Rule: `vwap_above_confirm_seconds` must be an integer that is zero or positive.
Rule: missing or `NULL` `vwap_above_confirm_seconds` is invalid and disables the plan before alert evaluation.
Rule: fractional `vwap_above_confirm_seconds` values are invalid and must not be truncated.
Rule: loaded `allow_trade` and `volume_gate_enabled` values treat only integer/text `1` as true.
Rule: Replay MVP loads and evaluates only `B_CAPACITY_LEADER` rows.
Rule: B-class materialization refreshes only same-date `B_CAPACITY_LEADER` rows and does not delete non-B strategy rows.
Rule: execution, risk, pre-close, and volume profile numeric fields must be finite.
Rule: `official_pre_close` must be non-negative; `0.0` is the missing-pre-close sentinel, while negative values disable the plan before alert evaluation.
Rule: malformed loaded `official_pre_close` values must not be coerced to the `0.0` missing-pre-close sentinel.
Rule: materialized malformed pre-close source values must become invalid plan data, not the `0.0` missing-pre-close sentinel.
Rule: malformed loaded numeric values are parsed into invalid plan values at the DB boundary, disabling the plan instead of crashing replay.
Rule: `ts_code` must be non-blank before replay can evaluate the plan.
Rule: `name` must be non-blank before replay can evaluate the plan.
Rule: `pre_close_source` must be non-blank before replay can evaluate the plan.
Rule: `source_candidate_id` must be non-blank before replay can evaluate the plan.
Rule: `source_report_date` must equal `trade_date` before replay can evaluate the plan.
Rule: `system_version` must be non-blank before replay can evaluate the plan.
Rule: `created_at` must be non-blank before replay can evaluate the plan.
Rule: core prices must satisfy `stop_price < entry_low <= breakout_price <= entry_high`.
Rule: planned stop distance must satisfy `(entry_low - stop_price) / entry_low <= max_stop_distance`.
Rule: `max_position_cash` and `max_loss` must be positive, and planned loss
`max_position_cash * ((entry_low - stop_price) / entry_low)` must not exceed `max_loss`.
Rule: `plan_json` must be a valid JSON object.
Rule: missing or `NULL` `plan_json` is invalid and disables the plan before alert evaluation.
Rule: if `volume_gate_enabled = 1`, `volume_min_abs_amount` must be positive.
Rule: `volume_same_window_multiplier` must be positive, and time-bucket volume ratios must satisfy
`0 <= volume_ratio_0935 <= volume_ratio_0945 <= volume_ratio_1000`.
Migration rule: existing local `intraday_plans` tables must be altered to include all Replay MVP plan columns and rebuilt when the `(trade_date, ts_code, strategy_type)` primary key or key-column `NOT NULL` constraints are missing before replay inserts or loads structured plans.
Migration rule: legacy plan rows with blank or whitespace-only composite-key fields must be dropped during rebuild.

Source rule: `entry_low`, `entry_high`, `breakout_price`, `stop_price`, `max_position_cash`,
`max_loss`, and `plan_json` must preserve the latest structured candidate snapshot when one exists.
If multiple candidate runs share the latest `generated_at`, the run with the highest `run_id`
is the deterministic source snapshot.
Missing snapshot `max_position_cash` or `max_loss` must not be replaced with fixture defaults.
Missing snapshot `plan_json` must not be replaced with `{}`.
Malformed snapshot numeric plan fields must materialize as invalid numeric values rather than raising
or being recovered from defaults.
If a `candidate_runs` row exists for the trade date, an empty B-class snapshot set is authoritative
and must materialize to zero intraday plans.

## CandidateSnapshot Plan Fields

The latest candidate snapshot is the production handoff between the post-market report and intraday replay.

Required structured plan fields for B-class replay:

- `entry_low`
- `entry_high`
- `breakout_price`
- `stop_price`
- `max_position_cash`
- `max_loss`
- `plan_json`

Rule: these values are written during report candidate persistence and must not be recovered by parsing Markdown.
Rule: malformed numeric values remain invalid machine data for replay validation instead of blocking materialization.
Rule: `plan_json.max_position_cash` and `plan_json.max_loss` mirror numeric structured fields.
Rule: narrative max-loss text is stored as `plan_json.max_loss_text` and must not occupy the machine `max_loss` key.
Migration rule: existing local `candidate_snapshots` tables must be altered to include all structured plan fields before the next report run persists snapshots.

## IntradayAlert

Append-only replay output.

Required MVP fields:

- `trade_date`
- `ts_code`
- `strategy_type`
- `alert_time`
- `alert_type`
- `severity`
- `rule_id`
- `title`
- `message`
- `reason_code`
- `state_before`
- `state_after`
- `snapshot_json`
- `plan_json`
- `created_at`

`reason_code` is mandatory because later tuning depends on stable statistics.
`trade_date`, `ts_code`, `strategy_type`, `alert_time`, `alert_type`, and `reason_code`
are database-required fields for replay alert rows.
`ENTRY_CANCELLED_PRICE_OUT_OF_RANGE` takes priority over `ENTRY_CANCELLED_VWAP_BREAK` when a locked buy plan breaks `stop_price`.
Pre-buy `ENTRY_CANCELLED_PRICE_OUT_OF_RANGE` is allowed before `vwap_active_after`; the VWAP start time gates observation, not structural invalidation.
`VOLUME_GATE_FAILED` is an observation alert only when price is inside `entry_low..entry_high`; zero-volume bars outside the entry range remain silent unless they break `stop_price`.
The same entry-range boundary applies both when VWAP is unavailable and when VWAP is calculable but the absolute amount gate fails.
`B_VWAP_CONFIRMING` is also an observation alert only when price is inside `entry_low..entry_high`.
`vwap_above_confirm_seconds` counts only continuous bars that are after `vwap_active_after`, above computed VWAP, volume-gate passing, and inside `entry_low..entry_high`.
`snapshot_json` must preserve the triggering bar's price, amount, volume, computed VWAP, `bar_high`, and `bar_low`.
Migration rule: existing local `intraday_alerts` tables must include Replay MVP alert fields,
restore `id INTEGER PRIMARY KEY AUTOINCREMENT`, and rebuild missing `NOT NULL`
constraints for the replay alert core fields before replay writes.
Migration rule: legacy alert rows with blank or whitespace-only `reason_code` must be dropped during rebuild.
Migration rule: legacy alert rows with blank or whitespace-only core text fields must be dropped during rebuild.

## IntradayAlertLock

Pessimistic alert lock.

Primary key: `(trade_date, ts_code, strategy_type, alert_type)`.

Rules:

- `BUY_TRIGGER` locks for the whole trade date.
- `WATCH` and `BUY_READY` may repeat through cooldown logic later.
- `ENTRY_CANCELLED` locks after first cancellation and terminates later buy-side alerts for that plan.
- Buy locks do not block risk or cancellation alerts.
Migration rule: existing local alert-lock tables must include trade date, stock, strategy, alert type, lock state, timestamp, rule id, reset metadata, the composite primary key, and non-null key columns before replay lock checks.
Migration rule: legacy alert-lock rows with blank or whitespace-only composite-key fields must be dropped during rebuild.

## IntradayReplayRun

Reproducibility record.

Required fields:

- `id`
- `trade_date`
- `input_file`
- `input_sha256`
- `plan_count`
- `alert_count`
- `status`
- `started_at`
- `ended_at`
- `error_message`

Status values: `SUCCESS`, `FAILED`.

Rule: each B-class replay run owns the same-date B-class alert output. Failed runs still clear stale
same-date `B_CAPACITY_LEADER` rows in `intraday_alerts` and `intraday_alert_locks` before recording `FAILED`.
Rule: B-class replay does not delete non-B alert or lock rows owned by later specification lines.
Rule: `plan_count` counts same-date `B_CAPACITY_LEADER` intraday plans even when replay fails during CSV validation.
Rule: `replay_report.md` repeats `input_file` and `input_sha256` so the report is reproducible without a database lookup.
Rule: `trade_date`, `input_file`, `input_sha256`, `plan_count`, `alert_count`, `status`,
`started_at`, and `ended_at` are database-required fields for replay-run rows.
Migration rule: existing local replay-run tables must include Replay MVP metadata columns,
restore `id INTEGER PRIMARY KEY AUTOINCREMENT`, and rebuild missing `NOT NULL`
constraints for replay-run audit fields before replay records failed or successful runs.
Migration rule: legacy replay-run rows with blank or whitespace-only `trade_date`, `input_file`,
`status`, `started_at`, or `ended_at` must be dropped during rebuild; empty `input_sha256`
remains valid for unreadable-input failure records.
Migration rule: legacy replay-run rows with statuses outside `SUCCESS` and `FAILED` must be dropped during rebuild.

## ReplayCsvRows

Replay CSV rows are parsed into `ReplayBar` values before strategy evaluation.

Rules:

- Command `--date` must be an 8-digit `YYYYMMDD` value; malformed command dates record `REPLAY_DATE_INVALID` after CSV row parsing and before date matching or strategy evaluation.
- If the input file is missing, malformed command dates record `REPLAY_DATE_INVALID` instead of `REPLAY_CSV_FILE_NOT_FOUND`.
- If the input path exists but cannot be opened as a CSV, replay records `REPLAY_CSV_UNREADABLE`, keeps `input_file`, and stores an empty `input_sha256`.
- `amount_since_open` and `volume_since_open` must be non-negative.
- `price`, `bar_high`, and `bar_low` must be positive.
- Numeric fields must be finite; `NaN` and `Infinity` are invalid.
- `price` must be inside the bar range: `bar_low <= price <= bar_high`.
- `trade_date` must be an 8-digit `YYYYMMDD` value.
- Required row cells must be present; short rows with missing cells are invalid.
- Unnamed extra row cells beyond the header are invalid; named extra columns remain allowed.
- A UTF-8 BOM before the first header name is accepted and must not hide `trade_date`.
- Header names must be unique and nonblank; duplicate or blank headers are invalid before row parsing.
- `ts_code` must contain at least one non-whitespace character.
- `quote_time` must be a zero-padded `HH:MM:SS` clock time.
- Each `ts_code` and `quote_time` pair may appear at most once in the replay input.
- For each `ts_code`, cumulative amount and volume must be non-decreasing after rows are sorted by `quote_time`.
- If `volume_since_open` is positive, `amount_since_open` must also be positive; otherwise the row would compute an impossible zero VWAP.
- Header-only input is valid only when no same-date B-class intraday plans exist; otherwise replay records `REPLAY_CSV_NO_ROWS`.
- After CSV structure validation succeeds, invalid same-date B-class plans are marked `DISABLED` before no-row or missing-symbol replay failures are recorded.
- When active same-date B-class plans exist, input must include at least one row for every active plan `ts_code`; otherwise replay records `REPLAY_CSV_MISSING_PLAN_SYMBOLS`.
