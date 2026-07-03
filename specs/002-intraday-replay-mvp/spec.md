# Feature Specification: Intraday Replay MVP

**Feature Branch**: `002-intraday-replay-mvp`
**Created**: 2026-06-30
**Status**: Draft
**Input**: User-approved plan for replay-first B-class intraday discipline alerts.

## User Scenarios & Testing

### User Story 1 - Materialize Structured Intraday Plans (Priority: P1)

As the trader, I want yesterday's B-class candidates converted into machine-executable intraday plans, so replay does not guess trading rules from Markdown.

**Independent Test**: Generate or seed B-class candidates, run plan materialization, and verify `intraday_plans` contains explicit entry, breakout, stop, VWAP, volume gate, and source metadata.

**Acceptance Scenarios**:

1. **Given** a B-class candidate exists, **When** intraday plans are materialized, **Then** one `intraday_plans` row is written for that candidate.
2. **Given** a plan lacks `entry_low`, `entry_high`, `breakout_price`, `stop_price`, or `vwap_active_after`, **When** replay runs, **Then** that plan is disabled with `PLAN_INVALID`.
3. **Given** a real trading day, **When** replay runs, **Then** it uses `intraday_plans` and never parses Markdown for execution values.
4. **Given** latest `candidate_snapshots` contain structured plan prices, **When** intraday plans are materialized, **Then** those snapshot prices are copied into `intraday_plans` instead of being recalculated from daily bars.
5. **Given** a latest candidate report run exists but has no B-class snapshots, **When** intraday plans are materialized, **Then** no plans are written even if `candidates` contains manual or stale B-class rows.
6. **Given** a plan has impossible price relationships, **When** replay runs, **Then** that plan is disabled with `PLAN_INVALID` before alert evaluation.
7. **Given** a plan's stop distance exceeds `max_stop_distance`, **When** replay runs, **Then** that plan is disabled with `PLAN_INVALID` before alert evaluation.
8. **Given** a plan's `plan_json` is not a JSON object, **When** replay runs, **Then** that plan is disabled with `PLAN_INVALID` before alert evaluation.
9. **Given** a plan's risk budget is missing or below planned stop loss, **When** replay runs, **Then** that plan is disabled with `PLAN_INVALID` before alert evaluation.
10. **Given** latest `candidate_snapshots` omit `max_position_cash` or `max_loss`, **When** intraday plans are materialized, **Then** those missing values are not replaced with fixture defaults.
11. **Given** latest `candidate_snapshots` omit `plan_json`, **When** intraday plans are materialized, **Then** the missing machine plan is not replaced with an empty JSON object.
12. **Given** a plan enables the volume gate but has no positive absolute amount threshold, **When** replay runs, **Then** that plan is disabled with `PLAN_INVALID` before alert evaluation.
13. **Given** a plan has invalid volume multiplier or non-monotonic time-bucket volume ratios, **When** replay runs, **Then** that plan is disabled with `PLAN_INVALID` before alert evaluation.
14. **Given** candidate snapshots persist machine plan JSON, **When** risk fields are written, **Then** `plan_json.max_loss` mirrors the numeric structured risk budget and narrative loss text is stored under `max_loss_text`.
15. **Given** a plan contains non-finite execution numeric values such as `Infinity`, **When** replay runs, **Then** that plan is disabled with `PLAN_INVALID` before alert evaluation.
16. **Given** a plan has a negative `vwap_above_confirm_seconds`, **When** replay runs, **Then** that plan is disabled with `PLAN_INVALID` before alert evaluation.
17. **Given** a loaded plan has missing or `NULL` `plan_json`, **When** replay runs, **Then** that plan is disabled with `PLAN_INVALID` before alert evaluation.
18. **Given** loaded plan boolean fields contain SQLite text values such as `false`, **When** replay runs, **Then** those fields are not treated as truthy merely because the text is non-empty.
19. **Given** a loaded plan has missing or `NULL` `vwap_active_after`, **When** replay runs, **Then** that plan is disabled with `PLAN_INVALID` before alert evaluation.
20. **Given** a loaded plan contains malformed numeric text in execution, risk, VWAP confirmation, or volume profile fields, **When** replay runs, **Then** that plan is disabled with `PLAN_INVALID` instead of escaping a runtime conversion error.
21. **Given** a loaded plan has missing or `NULL` `vwap_above_confirm_seconds`, **When** replay runs, **Then** that plan is disabled with `PLAN_INVALID` before alert evaluation.
22. **Given** a loaded plan has fractional `vwap_above_confirm_seconds`, **When** replay runs, **Then** that plan is disabled with `PLAN_INVALID` instead of truncating the window.
23. **Given** latest `candidate_snapshots` contain malformed numeric structured plan fields, **When** intraday plans are materialized, **Then** a plan row is still written with invalid numeric values so replay can disable it with `PLAN_INVALID` instead of crashing.
24. **Given** an existing local database has the pre-replay `candidate_snapshots` table without structured plan columns, **When** `init_db` runs, **Then** those columns are added so the next report run can persist machine plans.
25. **Given** an existing local database has an early `intraday_plans` table without the full Replay MVP columns, composite primary key, or non-null key columns, **When** `init_db` runs, **Then** the missing plan columns, `(trade_date, ts_code, strategy_type)` key, and key-column `NOT NULL` constraints are restored so replay can insert and evaluate unique structured plans.
26. **Given** an existing local database has early intraday output tables without full alert, lock, replay-run columns, or primary-key constraints, **When** `init_db` runs, **Then** replay can write alerts, locks, and run records without `OperationalError` and new alert/run rows receive stable ids.
27. **Given** a plan has negative `official_pre_close`, **When** replay runs, **Then** that plan is disabled with `PLAN_INVALID` before it can emit `PRE_CLOSE_MISSING`.
28. **Given** a loaded plan has malformed `official_pre_close` text, **When** replay runs, **Then** that plan is disabled with `PLAN_INVALID` instead of treating the value as missing pre-close.
29. **Given** plan materialization reads malformed pre-close source data, **When** replay runs the materialized plan, **Then** that plan is disabled with `PLAN_INVALID` instead of emitting `PRE_CLOSE_MISSING`.

---

### User Story 2 - Replay B-Class Alerts From CSV (Priority: P1)

As the trader, I want to replay intraday bars for B-class candidates, so I can validate discipline alerts before connecting live data.

**Independent Test**: Run `python -m trading_x replay --date YYYYMMDD --input data/replay/YYYYMMDD.csv` against fixed CSV fixtures and verify alerts and report output.

**Acceptance Scenarios**:

1. **Given** B-class intraday plans exist and replay CSV lacks `volume_since_open`, **When** replay starts, **Then** it fails with `REPLAY_CSV_MISSING_REQUIRED_COLUMNS`.
2. **Given** price is above VWAP but volume gate fails, **When** replay runs, **Then** it writes `WATCH` and does not write `BUY_TRIGGER`.
3. **Given** price is above VWAP, volume gate passes, price breaks `breakout_price`, and the plan is valid, **When** replay runs, **Then** it writes one `BUY_TRIGGER`.
4. **Given** price first moves above VWAP but has not remained above it for `vwap_above_confirm_seconds`, **When** replay runs, **Then** it writes `WATCH` with `B_VWAP_CONFIRMING` and does not write `BUY_TRIGGER` until the confirmation window is met.
5. **Given** replay validation fails, **When** replay exits, **Then** it records `intraday_replay_runs` and writes `replay_report.md` with `error_message`.
6. **Given** no candidates or no B-class intraday plans exist and no input CSV was exported, **When** replay runs with a valid command date, **Then** it exits normally and writes `replay_report.md`.
7. **Given** replay CSV rows are not sorted, **When** replay runs, **Then** each stock is evaluated by `quote_time`.
8. **Given** replay CSV contains invalid `quote_time`, **When** replay starts, **Then** it fails with `REPLAY_CSV_INVALID_ROW` before alert evaluation.
9. **Given** replay CSV contains malformed `trade_date`, **When** replay starts, **Then** it fails with `REPLAY_CSV_INVALID_ROW` before date matching or alert evaluation.
10. **Given** replay CSV contains negative cumulative amount or volume, **When** replay starts, **Then** it fails with `REPLAY_CSV_INVALID_ROW` before alert evaluation.
11. **Given** same-stock replay CSV rows contain decreasing `amount_since_open` or `volume_since_open` after sorting by `quote_time`, **When** replay starts, **Then** it fails with `REPLAY_CSV_INVALID_ROW` before alert evaluation.
12. **Given** replay CSV contains non-positive price fields or `price` outside `bar_low..bar_high`, **When** replay starts, **Then** it fails with `REPLAY_CSV_INVALID_ROW` before alert evaluation.
13. **Given** replay CSV contains non-finite numeric values such as `NaN` or `Infinity`, **When** replay starts, **Then** it fails with `REPLAY_CSV_INVALID_ROW` before alert evaluation.
14. **Given** `intraday_plans` contains non-B strategy rows, **When** replay runs, **Then** those rows are not counted, evaluated, or alerted in this MVP.
15. **Given** price is above confirmed VWAP, volume gate passes, and price is inside the entry range but below `breakout_price`, **When** replay runs, **Then** it writes `BUY_READY` with reason `B_BREAKOUT_READY` and does not write `BUY_TRIGGER`.
16. **Given** B-class intraday plans exist and replay CSV validation fails, **When** replay exits, **Then** `intraday_replay_runs.plan_count` and `replay_report.md` still record the B-class plan count.
17. **Given** replay CSV has a blank or whitespace-only `ts_code`, **When** replay starts, **Then** it fails with `REPLAY_CSV_INVALID_ROW` before alert evaluation.
18. **Given** replay CSV has the required header but a row omits any required cell, **When** replay starts, **Then** it fails with `REPLAY_CSV_INVALID_ROW` through the recorded failed-run path.
19. **Given** replay CSV has the required header but a row contains unnamed extra cells, **When** replay starts, **Then** it fails with `REPLAY_CSV_INVALID_ROW` instead of ignoring trailing malformed input.
20. **Given** B-class intraday plans exist and replay CSV has the required header but no data rows, **When** replay starts, **Then** it fails with `REPLAY_CSV_NO_ROWS` through the recorded failed-run path.
21. **Given** valid B-class intraday plans exist but replay CSV contains no rows for one or more active plan symbols, **When** replay runs, **Then** it fails with `REPLAY_CSV_MISSING_PLAN_SYMBOLS` through the recorded failed-run path.
22. **Given** replay CSV is encoded as UTF-8 with a BOM before `trade_date`, **When** replay starts, **Then** the header is accepted as the required replay CSV contract instead of being reported as missing `trade_date`.
23. **Given** replay CSV repeats a header name or contains a blank header name, **When** replay starts, **Then** it fails with `REPLAY_CSV_INVALID_HEADER` before row parsing.
24. **Given** replay CSV contains two rows for the same `ts_code` and `quote_time`, **When** replay starts, **Then** it fails with `REPLAY_CSV_INVALID_ROW` before alert evaluation.
25. **Given** replay CSV has positive `volume_since_open` but zero `amount_since_open`, **When** replay starts, **Then** it fails with `REPLAY_CSV_INVALID_ROW` before VWAP or alert evaluation.

---

### User Story 3 - Lock Duplicate Buy Triggers (Priority: P2)

As the trader, I want repeated price crosses to produce at most one buy trigger, so replay reflects trading discipline rather than alert noise.

**Independent Test**: Replay a fixture where price breaks out twice and later fails; verify only one `BUY_TRIGGER` exists and later `ENTRY_CANCELLED` can still be written.

**Acceptance Scenarios**:

1. **Given** a `BUY_TRIGGER` was already written for a stock and strategy, **When** price breaks out again, **Then** no second `BUY_TRIGGER` is written.
2. **Given** a `BUY_TRIGGER` is locked, **When** price later fails the plan, **Then** `ENTRY_CANCELLED` or risk alerts may still be written.
3. **Given** a `BUY_TRIGGER` is locked, **When** price later breaks `stop_price`, **Then** the `ENTRY_CANCELLED` reason is `ENTRY_CANCELLED_PRICE_OUT_OF_RANGE`, not `ENTRY_CANCELLED_VWAP_BREAK`.
4. **Given** `ENTRY_CANCELLED` was already written before buy trigger, **When** price later breaks out, **Then** no `BUY_TRIGGER` is written for that plan.
5. **Given** repeated bars produce the same WATCH reason, **When** replay runs, **Then** the database, `alert_count`, and replay report count that WATCH once.
6. **Given** repeated bars produce the same BUY_READY reason, **When** replay runs, **Then** the database, `alert_count`, and replay report count that BUY_READY once.

## Edge Cases

- `official_pre_close` missing allows `WATCH` but blocks `BUY_TRIGGER`.
- `official_pre_close = 0.0` means missing official pre-close; negative values are invalid plan data and must not be treated as missing.
- `amount_since_open` below the absolute volume threshold blocks `BUY_TRIGGER`.
- `volume_since_open <= 0` blocks VWAP-based trigger logic.
- `volume_since_open <= 0` emits `WATCH / VOLUME_GATE_FAILED` only when price is inside `entry_low..entry_high`.
- `B_VWAP_CONFIRMING` emits `WATCH` only when price is inside `entry_low..entry_high`.
- `volume_since_open <= 0` must not hide a pre-buy `stop_price` break; structural cancellation takes priority over VWAP/volume observation.
- `vwap_active_after` only gates VWAP-based observation and buy logic; it must not hide a structural `stop_price` break.
- `vwap_above_confirm_seconds` delays `BUY_TRIGGER` until price has stayed above computed VWAP for the configured seconds.
- `vwap_above_confirm_seconds` starts counting only after price is above computed VWAP and the volume gate passes.
- `vwap_above_confirm_seconds` starts counting only while price is inside `entry_low..entry_high`; bars above `entry_high` cannot pre-age a later `BUY_TRIGGER`.
- `vwap_above_confirm_seconds` must be zero or positive; negative confirmation windows are invalid.
- Missing or `NULL` `vwap_above_confirm_seconds` is invalid and must not be treated as zero.
- Fractional `vwap_above_confirm_seconds` values are invalid and must not be truncated into valid integer windows.
- Missing or malformed `vwap_active_after` disables the plan before alert evaluation.
- Missing or `NULL` `vwap_active_after` is invalid and must not crash replay.
- Plans must satisfy `stop_price < entry_low <= breakout_price <= entry_high`.
- Plans must satisfy `(entry_low - stop_price) / entry_low <= max_stop_distance`.
- Plans must have positive `max_position_cash` and `max_loss`, and planned loss `max_position_cash * ((entry_low - stop_price) / entry_low)` must not exceed `max_loss`.
- Plan execution, risk, pre-close, and volume profile numeric fields must be finite values.
- Malformed loaded plan numeric fields must be converted into invalid plan values at the DB boundary, so replay can disable the plan and still write its report.
- Malformed candidate snapshot numeric plan fields must be preserved as invalid plan values during materialization; materialization must not crash or synthesize valid defaults.
- `plan_json` must be a valid JSON object, preserving the machine-readable plan truth.
- Missing or `NULL` `plan_json` is an invalid machine plan and must not crash replay.
- Structurally valid replay input must still mark invalid plans `DISABLED` before no-row or missing-symbol failure exits.
- If `volume_gate_enabled = 1`, `volume_min_abs_amount` must be positive.
- `volume_same_window_multiplier` must be positive, and `volume_ratio_0935 <= volume_ratio_0945 <= volume_ratio_1000` with all ratios non-negative.
- `volume_gate_enabled = 0` disables the absolute amount gate for that plan.
- Loaded plan boolean fields treat only integer/text `1` as true; text such as `false` must not become truthy.
- Price breaking `stop_price` before buy trigger emits `ENTRY_CANCELLED`, not `SELL_TRIGGER`.
- Price breaking `stop_price` after `BUY_TRIGGER` still emits `ENTRY_CANCELLED_PRICE_OUT_OF_RANGE`, preserving structural-stop statistics without sell semantics.
- `ENTRY_CANCELLED` lock is terminal for later buy observation, readiness, and trigger alerts on the same plan.
- Command `--date` must be a valid `YYYYMMDD` value even when the CSV has no data rows.
- Command `--date` must also be validated when the input file is missing; missing files must not hide a malformed command date.
- Input path that exists but cannot be opened as a CSV must fail as `REPLAY_CSV_UNREADABLE` and still produce replay-run metadata and a report.
- Input CSV `trade_date` rows must be valid `YYYYMMDD` values and must match the command `--date`.
- Input CSV row order must not change same-stock replay results; `quote_time` is the execution order.
- Input CSV rows must provide values for required cells; short rows with missing cells are invalid rows.
- Input CSV rows must not contain unnamed extra cells beyond the header; named extra columns remain allowed by the contract.
- Input CSV with only the required header is allowed only when no B-class intraday plans exist; if B-class plans exist, replay fails with `REPLAY_CSV_NO_ROWS`.
- A missing input CSV is skipped when no B-class intraday plans exist and the command date is valid, because no replay evaluation will run.
- Existing but malformed or unreadable input paths still use the normal CSV error path even when no B-class plans exist.
- Input CSV must include at least one row for every active B-class plan symbol; otherwise replay fails with `REPLAY_CSV_MISSING_PLAN_SYMBOLS`.
- Input CSV may include a UTF-8 BOM before the first header name; BOM must not change required-column validation.
- Input CSV header names must be unique and nonblank; duplicate or blank headers are invalid because they can hide malformed cells.
- Input CSV `ts_code` must contain at least one non-whitespace character.
- Input CSV `quote_time` must be a valid zero-padded `HH:MM:SS` clock time.
- Input CSV must contain at most one row for each `ts_code` and `quote_time` pair.
- Input CSV `amount_since_open` and `volume_since_open` must be non-negative cumulative values.
- Input CSV with positive `volume_since_open` must also have positive `amount_since_open`, so a positive-volume bar cannot produce a zero VWAP.
- Input CSV cumulative amount and volume must be non-decreasing per stock after sorting by `quote_time`.
- Input CSV `price`, `bar_high`, and `bar_low` must be positive, and `bar_low <= price <= bar_high`.
- Input CSV numeric fields must be finite values; `NaN` and `Infinity` are invalid rows.
- Replay CSV contract must encode runtime numeric lower bounds and keep named extra columns allowed.
- Replay records input SHA-256 to make threshold tuning reproducible.
- Failed replay runs still generate `replay_report.md` with the failure reason.
- Failed replay runs clear same-date stale B-class alerts and alert locks before recording the failed run.
- Repeated `BUY_READY` reasons must not inflate `alert_count` or replay report lines.
- Alert `snapshot_json` keeps the triggering bar's `bar_high` and `bar_low` for replay review.
- Non-B `intraday_plans` rows are out of scope for Replay MVP and must not receive B-class alerts.
- Intraday Replay MVP runtime must not introduce deferred `SELL_TRIGGER`, `A_STRONG`, or realtime provider semantics; those belong to later specification lines.
- CLI must not expose a live `watch` command in this Replay MVP; live watch belongs to a later specification line.
- Candidate snapshot `plan_json.max_loss` must be numeric machine data; narrative max-loss text must not occupy that key.
- Existing local databases must migrate `candidate_snapshots` to include structured plan columns before report snapshots are persisted.
- Existing local databases must migrate early intraday tables to include Replay MVP columns before replay writes plans, locks, or run records.
- Existing local databases with early output tables must keep replay's observable alert and run-record query surfaces usable after migration, including stable alert/run ids and alert-lock uniqueness with non-null lock keys.

## Requirements

- **FR-001**: System MUST provide `python -m trading_x replay --date YYYYMMDD --input PATH`.
- **FR-002**: Replay MUST default input to `data/replay/<date>.csv` when `--input` is omitted.
- **FR-003**: Replay CSV MUST require `trade_date,quote_time,ts_code,price,amount_since_open,volume_since_open,bar_high,bar_low`.
- **FR-004**: System MUST compute `continuous_vwap = amount_since_open / volume_since_open`.
- **FR-005**: System MUST write `intraday_replay_runs` with non-null `input_file`, `input_sha256`, plan count, alert count, status, start/end time, and optional error message.
- **FR-006**: System MUST write alerts to `intraday_alerts` with stable non-null `reason_code`.
- **FR-007**: System MUST lock `BUY_TRIGGER` by trade date, stock, strategy, and alert type.
- **FR-008**: System MUST NOT emit `SELL_TRIGGER` in this MVP.
- **FR-009**: System MUST generate `reports/<date>_replay_report.md` for both successful and failed replay runs.
- **FR-010**: System MUST NOT parse Markdown or free text for execution values.
- **FR-011**: System MUST provide `python -m trading_x plans materialize --date YYYYMMDD` to create `intraday_plans` from structured candidates.
- **FR-012**: System MUST enforce `vwap_above_confirm_seconds` before `BUY_TRIGGER`.
- **FR-013**: Alert `snapshot_json` MUST include the triggering bar's price, amount, volume, VWAP, `bar_high`, and `bar_low`.
- **FR-014**: System MUST treat an `ENTRY_CANCELLED` lock as terminal for later buy-side alerts in the same trade date, stock, and strategy.
- **FR-015**: Replay MUST evaluate same-stock bars in ascending `quote_time` order regardless of CSV row order.
- **FR-016**: Replay MUST disable plans with missing `entry_low`, `entry_high`, `breakout_price`, `stop_price`, or `vwap_active_after` before evaluating alerts.
- **FR-017**: Replay MUST reject malformed or non-zero-padded `quote_time` values as `REPLAY_CSV_INVALID_ROW` before strategy evaluation.
- **FR-018**: Replay MUST require plan `vwap_active_after` to be a valid zero-padded `HH:MM:SS` clock time.
- **FR-019**: Replay `alert_count` and `replay_report.md` MUST count only alerts actually inserted into `intraday_alerts`.
- **FR-020**: Replay MUST reject negative `amount_since_open` or `volume_since_open` values as `REPLAY_CSV_INVALID_ROW`.
- **FR-021**: Plan materialization MUST prefer latest structured `candidate_snapshots` values for `entry_low`, `entry_high`, `breakout_price`, `stop_price`, `max_position_cash`, `max_loss`, and `plan_json`; direct `candidates` materialization is only a fixture fallback when no candidate snapshot run exists.
- **FR-022**: When any `candidate_runs` row exists for the trade date, plan materialization MUST treat latest `candidate_snapshots` as authoritative, including an empty B-class snapshot set.
- **FR-023**: Replay MUST clear same-date `B_CAPACITY_LEADER` rows in `intraday_alerts` and `intraday_alert_locks` before CSV validation, so failed B-class runs cannot leave stale B-class alerts from earlier runs.
- **FR-024**: Replay MUST reject decreasing same-stock `amount_since_open` or `volume_since_open` values after sorting rows by `quote_time`.
- **FR-025**: Replay MUST reject non-positive `price`, `bar_high`, or `bar_low`, and rows where `price` is outside `[bar_low, bar_high]`.
- **FR-026**: Replay MUST load and evaluate only `B_CAPACITY_LEADER` intraday plans in this MVP.
- **FR-027**: Replay MUST disable plans whose price relationships do not satisfy `stop_price < entry_low <= breakout_price <= entry_high`.
- **FR-028**: Replay MUST disable plans whose planned stop distance exceeds `max_stop_distance`.
- **FR-029**: Replay MUST disable plans whose `plan_json` is not a valid JSON object.
- **FR-030**: Replay MUST disable plans whose `max_position_cash` or `max_loss` are non-positive, or whose planned stop loss exceeds `max_loss`.
- **FR-031**: Plan materialization from `candidate_snapshots` MUST NOT synthesize default `max_position_cash` or `max_loss` when those structured snapshot values are missing.
- **FR-032**: Plan materialization from `candidate_snapshots` MUST NOT synthesize `{}` for missing `plan_json`.
- **FR-033**: Replay MUST disable plans with `volume_gate_enabled = 1` and non-positive `volume_min_abs_amount`.
- **FR-034**: Replay MUST disable plans whose volume multiplier is non-positive or whose time-bucket volume ratios are negative or non-monotonic.
- **FR-035**: Candidate snapshot persistence MUST write numeric structured risk budget to `plan_json.max_loss` and narrative loss text to `plan_json.max_loss_text`.
- **FR-036**: Failed replay runs MUST record `plan_count` as the number of same-date B-class `intraday_plans`, not as zero unless there are no B-class plans.
- **FR-037**: Replay MUST reject malformed CSV `trade_date` values as `REPLAY_CSV_INVALID_ROW` before comparing them to the command date.
- **FR-038**: Replay MUST reject non-finite CSV numeric values as `REPLAY_CSV_INVALID_ROW` before strategy evaluation.
- **FR-039**: Replay MUST disable plans with non-finite execution, risk, pre-close, or volume profile numeric values before alert evaluation.
- **FR-040**: Replay MUST disable plans with negative `vwap_above_confirm_seconds` before alert evaluation.
- **FR-041**: Replay MUST disable plans with missing or `NULL` `plan_json` before alert evaluation instead of raising a runtime exception.
- **FR-042**: Replay MUST parse loaded `allow_trade` and `volume_gate_enabled` as true only when the stored value is integer/text `1`.
- **FR-043**: Replay MUST disable plans with missing or `NULL` `vwap_active_after` before alert evaluation instead of raising a runtime exception.
- **FR-044**: Replay MUST disable plans with malformed loaded numeric execution, risk, VWAP confirmation, or volume profile fields before alert evaluation instead of raising a runtime conversion exception.
- **FR-045**: Replay MUST reject blank or whitespace-only CSV `ts_code` values as `REPLAY_CSV_INVALID_ROW` before strategy evaluation.
- **FR-046**: Replay MUST reject rows with missing required cell values as `REPLAY_CSV_INVALID_ROW` instead of raising runtime field-access exceptions.
- **FR-047**: Replay MUST reject rows with unnamed extra cells as `REPLAY_CSV_INVALID_ROW` instead of ignoring trailing malformed input.
- **FR-048**: Replay MUST fail with `REPLAY_CSV_NO_ROWS` when same-date B-class plans exist but the validated CSV contains zero data rows.
- **FR-049**: Replay MUST disable plans with missing or `NULL` `vwap_above_confirm_seconds` before alert evaluation instead of treating the missing confirmation window as zero.
- **FR-050**: Replay MUST emit pre-buy `ENTRY_CANCELLED` when price breaks `stop_price` even if `volume_since_open <= 0` prevents VWAP calculation.
- **FR-051**: Replay MUST fail with `REPLAY_CSV_MISSING_PLAN_SYMBOLS` when any active same-date B-class plan has no corresponding CSV row.
- **FR-052**: Plan materialization from `candidate_snapshots` MUST parse malformed numeric plan fields into invalid plan values instead of raising runtime conversion exceptions or synthesizing valid defaults.
- **FR-053**: Replay MUST accept UTF-8 CSV files with a BOM before the first header name while enforcing the same required replay CSV columns.
- **FR-054**: Replay MUST reject duplicate or blank CSV header names as `REPLAY_CSV_INVALID_HEADER` before row parsing.
- **FR-055**: `init_db` MUST migrate existing `candidate_snapshots` tables to include `entry_low`, `entry_high`, `stop_price`, `breakout_price`, `max_position_cash`, and `max_loss`.
- **FR-056**: `init_db` MUST migrate existing early intraday tables with missing Replay MVP columns needed by plan insertion, alert locks, and replay run records.
- **FR-057**: `init_db` MUST migrate existing early `intraday_alerts`, `intraday_alert_locks`, and `intraday_replay_runs` tables with columns, primary-key constraints, non-null alert core fields, non-null replay-run audit fields, and non-null alert-lock key columns needed by replay writes and reportable query surfaces.
- **FR-058**: Replay MUST reject malformed command `--date` values as `REPLAY_DATE_INVALID` before date matching or strategy evaluation, while preserving malformed CSV row errors.
- **FR-059**: Replay MUST disable invalid same-date B-class plans before returning `REPLAY_CSV_NO_ROWS` or `REPLAY_CSV_MISSING_PLAN_SYMBOLS` after CSV structure validation succeeds.
- **FR-060**: Replay MUST report `REPLAY_DATE_INVALID` for malformed command `--date` values when the input file is missing, because no CSV row error exists to preserve.
- **FR-061**: `replay_report.md` MUST include both `input_file` and `input_sha256` so the report remains reproducible without querying SQLite.
- **FR-062**: Replay MUST convert unreadable input paths such as directories into `REPLAY_CSV_UNREADABLE` while still recording `intraday_replay_runs` and writing `replay_report.md`.
- **FR-063**: After `BUY_TRIGGER` is locked, replay MUST classify a later `stop_price` break as `ENTRY_CANCELLED_PRICE_OUT_OF_RANGE` before evaluating VWAP-break cancellation.
- **FR-064**: Replay MUST emit pre-buy `ENTRY_CANCELLED_PRICE_OUT_OF_RANGE` for `stop_price` breaks even when the bar is earlier than `vwap_active_after`.
- **FR-065**: When multiple `candidate_runs` share the latest `generated_at` for a trade date, plan materialization MUST choose one deterministic latest run by descending `run_id`.
- **FR-066**: Replay MUST return successful no-plan output when the input CSV is absent, no same-date B-class intraday plans exist, and `--date` is a valid `YYYYMMDD`.
- **FR-067**: B-class plan materialization MUST refresh only same-date `B_CAPACITY_LEADER` rows in `intraday_plans`, preserving non-B strategy rows for future specification lines.
- **FR-068**: `init_db` MUST migrate existing early `intraday_plans` tables with the composite primary-key constraint and non-null key columns needed to keep one machine plan per trade date, stock, and strategy.
- **FR-069**: Replay MUST disable plans with fractional `vwap_above_confirm_seconds` before alert evaluation instead of truncating the value.
- **FR-070**: `intraday_alerts` MUST enforce non-null `trade_date`, `ts_code`, `strategy_type`, `alert_time`, `alert_type`, and `reason_code` for replay alert statistics.
- **FR-071**: `intraday_replay_runs` MUST enforce non-null `trade_date`, `input_file`, `input_sha256`, `plan_count`, `alert_count`, `status`, `started_at`, and `ended_at` for replay reproducibility records.
- **FR-072**: B-class replay MUST preserve non-B rows in `intraday_alerts` and `intraday_alert_locks`, so MVP replay cannot delete output owned by future specification lines.
- **FR-073**: Replay MUST count repeated same-reason `BUY_READY` alerts once in `intraday_alerts`, `alert_count`, and `replay_report.md`.
- **FR-074**: Replay CSV contract MUST encode runtime numeric lower bounds for amount, volume, price, `bar_high`, and `bar_low`, and MUST allow named extra columns.
- **FR-075**: Intraday Replay MVP runtime under `src/trading_x/intraday*.py` MUST remain free of deferred sell, A-class, and realtime-provider semantics.
- **FR-076**: CLI MUST NOT expose a live `watch` command in the Replay MVP.
- **FR-077**: Replay MUST disable same-date B-class plans whose `source_report_date` does not equal `trade_date`, so stale or manually mismatched plan snapshots cannot execute.
- **FR-078**: Replay MUST disable B-class plans with blank `source_candidate_id`, so unsourced manual rows cannot execute as machine plan snapshots.
- **FR-079**: Replay MUST disable B-class plans with blank `system_version`, so plan snapshots without producer-version metadata cannot execute.
- **FR-080**: Replay MUST disable B-class plans with blank `created_at`, so plan snapshots without creation audit metadata cannot execute.
- **FR-081**: Replay MUST disable B-class plans with blank `pre_close_source`, so official pre-close values without source provenance cannot execute.
- **FR-082**: Replay MUST disable B-class plans with blank `ts_code`, so malformed machine plan identity cannot be treated as a missing CSV symbol.
- **FR-083**: Replay MUST disable B-class plans with blank `name`, so machine plan snapshots remain auditable in reports and alerts.
- **FR-084**: Replay MUST NOT emit `WATCH / VOLUME_GATE_FAILED` for zero-volume bars below `entry_low`, so idle bars outside the observation zone do not create false watch alerts.
- **FR-085**: Replay MUST NOT emit `WATCH / VOLUME_GATE_FAILED` for zero-volume bars above `entry_high`, so chased bars outside the entry zone do not inflate watch alerts.
- **FR-086**: Replay MUST NOT emit `WATCH / VOLUME_GATE_FAILED` above `entry_high` when VWAP is calculable but the absolute volume gate fails.
- **FR-087**: Replay MUST NOT emit `WATCH / B_VWAP_CONFIRMING` above `entry_high` when price is above VWAP but the confirmation window is not yet satisfied.
- **FR-088**: Replay MUST start the `vwap_above_confirm_seconds` timer only after the bar is above VWAP and passes the volume gate, so no-volume or under-threshold bars cannot pre-age a later `BUY_TRIGGER`.
- **FR-089**: Replay MUST start the `vwap_above_confirm_seconds` timer only while price is inside `entry_low..entry_high`, so chased-zone bars cannot pre-age a later `BUY_TRIGGER`.
- **FR-090**: Replay MUST reject duplicate same-stock same-`quote_time` CSV rows as `REPLAY_CSV_INVALID_ROW`, so a replay point has exactly one market snapshot.
- **FR-091**: Replay MUST reject rows where `volume_since_open > 0` and `amount_since_open <= 0` as `REPLAY_CSV_INVALID_ROW`, so VWAP cannot be computed as zero from impossible cumulative inputs.
- **FR-092**: Replay MUST disable B-class plans with negative `official_pre_close` as `PLAN_INVALID`, while preserving `0.0` as the missing-pre-close sentinel that can emit `WATCH / PRE_CLOSE_MISSING`.
- **FR-093**: Replay MUST parse malformed loaded `official_pre_close` values as invalid plan data, not coerce them to `0.0` missing-pre-close semantics.
- **FR-094**: Plan materialization MUST preserve malformed pre-close source values as invalid plan data, not coerce them to the `0.0` missing-pre-close sentinel.
- **FR-095**: Intraday Replay MVP runtime MUST remain free of deferred positions and sell-guidance semantics such as `SELL_WARN`, T+1, available shares, entry dates, and sell guidance.
- **FR-096**: Alert-table migration MUST drop legacy rows whose `reason_code` is blank or whitespace-only, so replay statistics cannot inherit unclassifiable alerts.
- **FR-097**: Alert-lock migration MUST drop legacy rows whose composite-key fields are blank or whitespace-only, so stale locks remain addressable by trade date, stock, strategy, and alert type.
- **FR-098**: Intraday-plan migration MUST drop legacy rows whose composite-key fields are blank or whitespace-only, so machine plans remain addressable by trade date, stock, and strategy.
- **FR-099**: Replay-run migration MUST drop legacy rows whose required text audit fields are blank or whitespace-only, while preserving empty `input_sha256` for unreadable-input failure records.
- **FR-100**: Replay-run migration MUST drop legacy rows whose `status` is not `SUCCESS` or `FAILED`, so replay-run statistics keep a closed status set.
- **FR-101**: Alert-table migration MUST drop legacy rows whose core text fields are blank or whitespace-only, so alert statistics cannot inherit unaddressable alert rows.

## Success Criteria

- **SC-001**: Fixed replay fixtures produce stable alert counts and reason codes.
- **SC-002**: Missing required CSV columns fail before strategy evaluation when B-class plans exist.
- **SC-003**: No-volume VWAP stand-up never produces `BUY_TRIGGER`.
- **SC-004**: Missing `official_pre_close` allows `WATCH` but blocks `BUY_TRIGGER`.
- **SC-005**: No-plan days generate a replay report instead of failing.
- **SC-006**: Buy-before-risk failure emits `ENTRY_CANCELLED` without sell semantics.
- **SC-007**: Above-VWAP bars before the confirmation window emit observation only, not `BUY_TRIGGER`.
- **SC-008**: Stored alerts preserve triggering bar high/low in `snapshot_json`.
- **SC-009**: Replay validation failures produce a report containing `error_message`.
- **SC-010**: A plan cancelled before buy trigger never produces a later `BUY_TRIGGER` in the same replay run.
- **SC-011**: Unsorted same-stock replay CSV rows produce the same alerts as chronological rows.
- **SC-012**: Plans missing any core entry, risk, or VWAP activation field are marked `PLAN_INVALID` and produce no alerts.
- **SC-013**: Invalid replay row values fail through the recorded failed-run path instead of escaping as runtime exceptions.
- **SC-014**: Duplicate WATCH reasons do not inflate replay `alert_count` or report lines.
- **SC-015**: Negative cumulative amount or volume rows fail before strategy evaluation.
- **SC-016**: Materialized `intraday_plans` preserve the latest structured candidate snapshot prices and execution `plan_json`.
- **SC-017**: A report run with no B-class snapshots produces zero `intraday_plans` and never falls back to manual or stale `candidates` rows.
- **SC-018**: A failed replay run leaves no stale same-date B-class alerts or alert locks from a previous replay run.
- **SC-019**: Same-stock cumulative amount or volume decreases fail before strategy evaluation.
- **SC-020**: Invalid price or bar range rows fail before strategy evaluation.
- **SC-021**: Non-B intraday plans produce zero replay alerts and do not inflate `plan_count`.
- **SC-022**: Plans with impossible price relationships are marked `PLAN_INVALID` and produce no alerts.
- **SC-023**: Plans with stop distance above `max_stop_distance` are marked `PLAN_INVALID` and produce no alerts.
- **SC-024**: Plans with malformed `plan_json` are marked `PLAN_INVALID` and produce no alerts.
- **SC-025**: Plans with missing or insufficient risk budget are marked `PLAN_INVALID` and produce no alerts.
- **SC-026**: Snapshot-sourced plans with missing risk budget keep invalid zero budget values instead of receiving fixture defaults.
- **SC-027**: Snapshot-sourced plans with missing `plan_json` keep an invalid empty machine plan instead of receiving `{}`.
- **SC-028**: Plans with an enabled but thresholdless volume gate are marked `PLAN_INVALID` and produce no alerts.
- **SC-029**: Plans with invalid volume profile parameters are marked `PLAN_INVALID` and produce no alerts.
- **SC-030**: Candidate snapshot `plan_json` keeps `max_loss` numeric and does not emit legacy `plan_max_loss`.
- **SC-031**: Confirmed above-VWAP, volume-passing bars inside the entry range but below breakout emit `BUY_READY`.
- **SC-032**: CSV validation failures preserve the same-date B-class plan count in `intraday_replay_runs` and `replay_report.md`.
- **SC-033**: Non-zero-padded clock values such as `9:36:00` fail before strategy evaluation.
- **SC-034**: Malformed CSV dates such as `2026-06-30` fail before strategy evaluation, even when the command date has the same malformed value.
- **SC-035**: Non-finite CSV numeric values such as `NaN` or `Infinity` fail before strategy evaluation.
- **SC-036**: Plans with non-finite execution numeric values are marked `PLAN_INVALID` and produce no alerts.
- **SC-037**: Plans with negative VWAP confirmation windows are marked `PLAN_INVALID` and produce no alerts.
- **SC-038**: Plans with `NULL` `plan_json` are marked `PLAN_INVALID`, produce no alerts, and replay still writes its report.
- **SC-039**: Text `false` in `allow_trade` disables the plan, while text `false` in `volume_gate_enabled` disables the absolute amount gate.
- **SC-040**: Plans with `NULL` `vwap_active_after` are marked `PLAN_INVALID`, produce no alerts, and replay still writes its report.
- **SC-041**: Plans with malformed loaded numeric fields are marked `PLAN_INVALID`, produce no alerts, and replay still writes its report.
- **SC-042**: Blank or whitespace-only CSV `ts_code` values fail before strategy evaluation and produce a failed replay report.
- **SC-043**: Short CSV rows with missing required cells fail before strategy evaluation and produce a failed replay report.
- **SC-044**: Long CSV rows with unnamed extra cells fail before strategy evaluation and produce a failed replay report.
- **SC-045**: Header-only replay CSV files succeed only on no-plan days; when B-class plans exist they fail with `REPLAY_CSV_NO_ROWS` and produce a failed replay report.
- **SC-046**: Plans with `NULL` VWAP confirmation windows are marked `PLAN_INVALID`, produce no alerts, and replay still writes its report.
- **SC-047**: A no-volume bar below `stop_price` emits `ENTRY_CANCELLED_PRICE_OUT_OF_RANGE`, not `VOLUME_GATE_FAILED`.
- **SC-048**: Replay CSV files that omit an active plan symbol fail with `REPLAY_CSV_MISSING_PLAN_SYMBOLS`, preserve plan count, and produce a failed replay report.
- **SC-049**: Snapshot-sourced plans with malformed numeric structured fields materialize successfully with invalid plan values and follow the `PLAN_INVALID` replay path.
- **SC-050**: UTF-8 BOM replay CSV headers are accepted and can produce the same alerts as BOM-free headers.
- **SC-051**: Duplicate replay CSV header names fail with `REPLAY_CSV_INVALID_HEADER` instead of allowing later columns to overwrite earlier cells.
- **SC-052**: A pre-replay local database can run `init_db` and then persist candidate snapshots with structured plan fields without `OperationalError`.
- **SC-053**: An early local `intraday_plans` table can run `init_db`, regain the `(trade_date, ts_code, strategy_type)` primary key with non-null key columns, accept a full structured plan insert, and complete replay without `OperationalError`.
- **SC-054**: Early local intraday output tables can run `init_db`, restore non-null alert-lock key columns, complete a replay that writes `BUY_TRIGGER`, record `intraday_replay_runs.status` and `alert_count`, and assign non-null ids to new alert/run rows.
- **SC-055**: Malformed command dates such as `2026-06-30` fail with `REPLAY_DATE_INVALID` even when there are no B-class plans and the CSV only has headers.
- **SC-056**: Header-only replay input with an invalid B-class plan fails with `REPLAY_CSV_NO_ROWS`, marks the plan `DISABLED`, and includes `PLAN_INVALID` in the failed replay report.
- **SC-057**: Malformed command dates such as `2026-06-30` fail with `REPLAY_DATE_INVALID` even when the replay input file is missing.
- **SC-058**: A replay report generated from a fixed CSV includes the exact input path and the SHA-256 of that file.
- **SC-059**: A directory passed as replay input fails with `REPLAY_CSV_UNREADABLE`, records an empty `input_sha256`, and includes the input path in the failed replay report.
- **SC-060**: A post-`BUY_TRIGGER` bar below `stop_price` writes `ENTRY_CANCELLED_PRICE_OUT_OF_RANGE` even when the same bar is also below VWAP.
- **SC-061**: A pre-`vwap_active_after` bar below `stop_price` writes `ENTRY_CANCELLED_PRICE_OUT_OF_RANGE` and prevents a later `BUY_TRIGGER`.
- **SC-062**: Two candidate runs with identical latest `generated_at` materialize from the lexicographically highest `run_id` only, without duplicate intraday-plan inserts.
- **SC-063**: Duplicate BUY_READY reasons do not inflate replay `alert_count` or report lines.
- **SC-064**: Replay CSV contract numeric bounds and named-extra-column behavior match runtime CSV validation.
- **SC-065**: Intraday Replay MVP boundary guard fails if runtime intraday modules introduce deferred `SELL_TRIGGER`, `A_STRONG`, or realtime-provider tokens.
- **SC-066**: Calling `trading_x watch` fails as an unknown CLI command in the Replay MVP.
- **SC-067**: A B-class plan with `source_report_date` from another date is marked `PLAN_INVALID`, emits no alerts, and leaves a failed plan reason in `replay_report.md`.
- **SC-068**: A B-class plan with blank `source_candidate_id` is marked `PLAN_INVALID`, emits no alerts, and leaves a failed plan reason in `replay_report.md`.
- **SC-069**: A B-class plan with blank `system_version` is marked `PLAN_INVALID`, emits no alerts, and leaves a failed plan reason in `replay_report.md`.
- **SC-070**: A B-class plan with blank `created_at` is marked `PLAN_INVALID`, emits no alerts, and leaves a failed plan reason in `replay_report.md`.
- **SC-071**: A B-class plan with blank `pre_close_source` is marked `PLAN_INVALID`, emits no alerts, and leaves a failed plan reason in `replay_report.md`.
- **SC-072**: A B-class plan with blank `ts_code` is marked `PLAN_INVALID`, emits no alerts, and leaves a failed plan reason in `replay_report.md`.
- **SC-073**: A B-class plan with blank `name` is marked `PLAN_INVALID`, emits no alerts, and leaves a failed plan reason in `replay_report.md`.
- **SC-074**: A zero-volume bar below `entry_low` and above `stop_price` emits no alert instead of `WATCH / VOLUME_GATE_FAILED`.
- **SC-075**: A zero-volume bar above `entry_high` emits no alert instead of `WATCH / VOLUME_GATE_FAILED`.
- **SC-076**: A VWAP-calculable bar above `entry_high` with amount below the absolute volume threshold emits no alert instead of `WATCH / VOLUME_GATE_FAILED`.
- **SC-077**: A VWAP-calculable, volume-passing bar above `entry_high` before the VWAP confirmation window emits no alert instead of `WATCH / B_VWAP_CONFIRMING`.
- **SC-078**: A first above-VWAP bar below the amount threshold does not count toward `vwap_above_confirm_seconds`; replay emits `B_VWAP_CONFIRMING` when volume first passes and delays `BUY_TRIGGER` until the configured seconds elapse after that bar.
- **SC-079**: A first above-VWAP bar above `entry_high` does not count toward `vwap_above_confirm_seconds`; replay starts confirmation only after price returns inside the entry range.
- **SC-080**: Duplicate same-stock same-`quote_time` replay CSV rows fail with `REPLAY_CSV_INVALID_ROW` and produce no alerts.
- **SC-081**: A replay CSV row with positive `volume_since_open` and zero `amount_since_open` fails with `REPLAY_CSV_INVALID_ROW` and produces no alerts.
- **SC-082**: A B-class plan with negative `official_pre_close` is marked `PLAN_INVALID`, emits no alerts, and leaves a failed plan reason in `replay_report.md`.
- **SC-083**: A B-class plan with malformed loaded `official_pre_close` text is marked `PLAN_INVALID`, emits no alerts, and leaves a failed plan reason in `replay_report.md`.
- **SC-084**: A materialized B-class plan from malformed pre-close source data is marked `PLAN_INVALID`, emits no alerts, and leaves a failed plan reason in `replay_report.md`.
- **SC-085**: Intraday Replay MVP boundary guard fails if runtime intraday modules introduce deferred `SELL_WARN`, T+1, available-shares, entry-date, or sell-guidance tokens.
- **SC-086**: Upgrading a legacy `intraday_alerts` table drops rows with blank or whitespace-only `reason_code` while preserving rows with stable reason codes.
- **SC-087**: Upgrading a legacy `intraday_alert_locks` table drops rows with blank or whitespace-only composite-key fields while preserving addressable locks.
- **SC-088**: Upgrading a legacy `intraday_plans` table drops rows with blank or whitespace-only composite-key fields while preserving addressable machine plans.
- **SC-089**: Upgrading a legacy `intraday_replay_runs` table drops rows with blank or whitespace-only required text audit fields while preserving valid reproducibility records.
- **SC-090**: Upgrading a legacy `intraday_replay_runs` table drops rows with statuses outside `SUCCESS / FAILED` while preserving valid replay-run records.
- **SC-091**: Upgrading a legacy `intraday_alerts` table drops rows with blank or whitespace-only core alert fields while preserving valid alerts.

## Assumptions

- V1 remains a local Python CLI with SQLite.
- Tushare remains the post-market and replay data source.
- Live `IntradayDataProvider` is deferred to a later specification.
- This system is a discipline tool, not investment advice.
