# Tasks: Intraday Replay MVP

**Input**: `spec.md`, `plan.md`, `data-model.md`, `contracts/replay-csv-schema.json`

**Tests**: Required before production code.

## Phase 1: Spec Kit Artifacts

- [x] T001 Update constitution with intraday replay principles.
- [x] T002 Add feature spec, data model, replay CSV contract, plan, and tasks.

## Phase 2: Schema And Contract Tests

- [x] T003 Write failing schema test for `intraday_plans`, `intraday_alerts`, `intraday_alert_locks`, `intraday_replay_runs`.
- [x] T004 Write failing replay CSV validation test for missing `volume_since_open`.
- [x] T005 Implement schema additions.

## Phase 3: Plan Materialization

- [x] T006 Write failing test that B-class candidate materializes to `intraday_plans`.
- [x] T007 Write failing test that invalid plans are disabled during replay.
- [x] T008 Implement plan materialization from `candidates`.

## Phase 4: Replay Engine

- [x] T009 Write failing tests for `official_pre_close` priority and missing pre-close behavior.
- [x] T010 Write failing tests for VolumeGate and VWAP behavior.
- [x] T011 Write failing tests for AlertLock and cancellation after buy lock.
- [x] T012 Implement PreCloseProvider, VWAPEngine, VolumeGate, B-class state flow, and AlertLock.

## Phase 5: CLI And Report

- [x] T013 Write failing CLI replay test for no-plan report generation.
- [x] T014 Add `python -m trading_x replay --date YYYYMMDD --input PATH`.
- [x] T015 Generate `reports/<date>_replay_report.md`.
- [x] T016 Record `intraday_replay_runs` with input hash and status.

## Phase 6: Verification

- [x] T017 Run `uv run pytest`.
- [x] T018 Run `uv run pyright`.
- [x] T019 Run `uv run ruff check`.
- [x] T020 Run fixture replay command.

## Phase 7: Candidate-To-Plan CLI Handoff

- [x] T021 Write failing CLI test for `plans materialize --date`.
- [x] T022 Add `python -m trading_x plans materialize --date YYYYMMDD`.
- [x] T023 Verify materialized plan count is stable from fixture candidates.

## Phase 8: Replay Rule Hardening

- [x] T024 Write failing test for pre-buy `ENTRY_CANCELLED` when price breaks `stop_price`.
- [x] T025 Write failing test that `volume_gate_enabled = 0` disables the absolute amount gate.
- [x] T026 Update B-class replay rules without adding sell semantics.

## Phase 9: Rule Module Review

- [x] T027 Split replay rule decisions from alert persistence before adding more B-class rules.
- [x] T028 Verify replay behavior remains stable after module split.

## Phase 10: VWAP Confirmation Window

- [x] T029 Write failing test that `vwap_above_confirm_seconds` delays `BUY_TRIGGER`.
- [x] T030 Enforce continuous above-VWAP confirmation before `BUY_TRIGGER`.
- [x] T031 Update spec/analyze artifacts for the VWAP confirmation rule.

## Phase 11: Alert Snapshot Reviewability

- [x] T032 Write failing test that alert `snapshot_json` preserves `bar_high` and `bar_low`.
- [x] T033 Store triggering bar high/low in alert snapshots.
- [x] T034 Update spec/analyze/data model artifacts for snapshot reviewability.

## Phase 12: Failed Replay Reports

- [x] T035 Write failing test that CSV validation failure still writes `replay_report.md`.
- [x] T036 Generate replay reports for failed replay runs with `error_message`.
- [x] T037 Update spec/analyze artifacts for failed replay report behavior.

## Phase 13: Entry Cancellation Lock Terminal

- [x] T038 Write failing test that pre-buy `ENTRY_CANCELLED` blocks later `BUY_TRIGGER`.
- [x] T039 Enforce `ENTRY_CANCELLED` as terminal for later buy-side alerts.
- [x] T040 Update spec/analyze/data model artifacts for terminal cancellation behavior.

## Phase 14: Replay Time Ordering

- [x] T041 Write failing test that unsorted same-stock CSV rows are evaluated by `quote_time`.
- [x] T042 Sort same-stock replay bars before rule evaluation.
- [x] T043 Update spec/analyze artifacts for replay time ordering.

## Phase 15: Plan Core Price Validation

- [x] T044 Write failing test that missing `entry_low` disables the intraday plan.
- [x] T045 Require `entry_low` in plan validity checks.
- [x] T046 Update spec/analyze artifacts for core price validation.

## Phase 16: Replay Row Time Validation

- [x] T047 Write failing test that invalid `quote_time` fails as `REPLAY_CSV_INVALID_ROW`.
- [x] T048 Validate `quote_time` at CSV parse boundary.
- [x] T049 Update spec/analyze artifacts for replay row time validation.

## Phase 17: Plan VWAP Activation Validation

- [x] T050 Write failing test that missing `vwap_active_after` disables the plan.
- [x] T051 Require valid `vwap_active_after` in plan validity checks.
- [x] T052 Share clock-time validation between replay rows and plans.
- [x] T053 Update spec/analyze artifacts for plan VWAP activation validation.

## Phase 18: Alert Count Deduplication

- [x] T054 Write failing test that repeated WATCH reasons do not inflate `alert_count`.
- [x] T055 Count only alerts actually inserted into `intraday_alerts`.
- [x] T056 Update spec/analyze artifacts for alert count deduplication.

## Phase 19: Replay Cumulative Value Validation

- [x] T057 Write failing test that negative cumulative amount or volume fails replay parsing.
- [x] T058 Reject negative `amount_since_open` and `volume_since_open` values.
- [x] T059 Update spec/analyze artifacts for cumulative value validation.

## Phase 20: Structured Snapshot Plan Handoff

- [x] T060 Write failing test that candidate snapshots persist structured plan prices.
- [x] T061 Write failing test that `intraday_plans` preserve latest snapshot prices and `plan_json`.
- [x] T062 Persist B-class plan prices through candidate reports and candidate snapshots.
- [x] T063 Prefer latest structured candidate snapshot during plan materialization.
- [x] T064 Update spec/analyze/data model artifacts for structured snapshot handoff.

## Phase 21: Authoritative Empty Snapshot Handoff

- [x] T065 Write failing test that an empty latest candidate snapshot blocks fallback to manual `candidates`.
- [x] T066 Treat any report run for the trade date as authoritative during plan materialization.
- [x] T067 Update spec/analyze/data model artifacts for empty snapshot handoff.

## Phase 22: Failed Replay Output Ownership

- [x] T068 Write failing test that failed replay clears same-date stale alerts.
- [x] T069 Clear same-date alerts and alert locks before CSV validation.
- [x] T070 Update spec/analyze/data model artifacts for failed replay output ownership.

## Phase 23: Replay Cumulative Monotonic Validation

- [x] T071 Write failing test that same-stock cumulative amount or volume decreases fail replay parsing.
- [x] T072 Validate cumulative amount and volume as non-decreasing by stock and `quote_time`.
- [x] T073 Update spec/analyze/data model/contract artifacts for cumulative monotonic validation.

## Phase 24: Replay Bar Price Range Validation

- [x] T074 Write failing test that non-positive price fields or price outside bar range fail replay parsing.
- [x] T075 Validate `price`, `bar_high`, and `bar_low` at the CSV parse boundary.
- [x] T076 Update spec/analyze/data model/contract artifacts for replay bar price range validation.

## Phase 25: B-Class Replay Scope Lock

- [x] T077 Write failing test that non-B intraday plans are not counted or alerted during replay.
- [x] T078 Restrict replay plan loading to `B_CAPACITY_LEADER`.
- [x] T079 Update spec/analyze/data model artifacts for B-class replay scope.

## Phase 26: Plan Price Relationship Validation

- [x] T080 Write failing test that impossible plan price relationships disable the plan.
- [x] T081 Require `stop_price < entry_low <= breakout_price <= entry_high` in plan validity.
- [x] T082 Update spec/analyze/data model artifacts for plan price relationship validation.

## Phase 27: Plan Stop Distance Validation

- [x] T083 Write failing test that stop distance above `max_stop_distance` disables the plan.
- [x] T084 Require `(entry_low - stop_price) / entry_low <= max_stop_distance` in plan validity.
- [x] T085 Update spec/analyze/data model artifacts for stop distance validation.

## Phase 28: Plan JSON Object Validation

- [x] T086 Write failing test that malformed `plan_json` disables the plan.
- [x] T087 Require `plan_json` to parse as a JSON object in plan validity.
- [x] T088 Update spec/analyze/data model artifacts for `plan_json` validation.

## Phase 29: Plan Risk Budget Validation

- [x] T089 Write failing test that missing or insufficient risk budget disables the plan.
- [x] T090 Require positive `max_position_cash` and `max_loss`, and planned stop loss <= `max_loss`.
- [x] T091 Update spec/analyze/data model artifacts for risk budget validation.

## Phase 30: Snapshot Risk Budget Preservation

- [x] T092 Write failing test that missing snapshot risk budget is not replaced by fixture defaults.
- [x] T093 Preserve missing snapshot risk budget as invalid zero values during plan materialization.
- [x] T094 Update spec/analyze/data model artifacts for snapshot risk budget preservation.

## Phase 31: Snapshot Plan JSON Preservation

- [x] T095 Write failing test that missing snapshot `plan_json` is not replaced by `{}`.
- [x] T096 Preserve missing snapshot `plan_json` as an invalid empty machine plan.
- [x] T097 Update spec/analyze/data model artifacts for snapshot `plan_json` preservation.

## Phase 32: Enabled Volume Gate Threshold Validation

- [x] T098 Write failing test that an enabled volume gate without a positive threshold disables the plan.
- [x] T099 Require positive `volume_min_abs_amount` when `volume_gate_enabled = 1`.
- [x] T100 Update spec/analyze/data model artifacts for enabled volume gate threshold validation.

## Phase 33: Volume Profile Parameter Validation

- [x] T101 Write failing test that invalid volume profile parameters disable the plan.
- [x] T102 Require a positive `volume_same_window_multiplier` and non-negative monotonic time-bucket volume ratios.
- [x] T103 Update spec/analyze/data model artifacts for volume profile validation.

## Phase 34: Candidate Snapshot Plan JSON Risk Field Alignment

- [x] T104 Write failing test that candidate snapshot `plan_json.max_loss` is numeric and narrative loss text uses `max_loss_text`.
- [x] T105 Persist numeric structured risk budget under `plan_json.max_loss` without legacy `plan_max_loss`.
- [x] T106 Update spec/analyze/data model artifacts for candidate snapshot risk JSON alignment.

## Phase 35: BUY_READY Acceptance Coverage

- [x] T107 Add replay acceptance test for confirmed above-VWAP entry-range bars below breakout emitting `BUY_READY`.
- [x] T108 Update spec/analyze artifacts for explicit `BUY_READY` acceptance coverage.

## Phase 36: Failed Replay Plan Count Preservation

- [x] T109 Write failing test that CSV validation failures preserve same-date B-class `plan_count`.
- [x] T110 Record failed replay `plan_count` from scoped B-class intraday plans.
- [x] T111 Update spec/analyze/data model artifacts for failed replay plan-count preservation.

## Phase 37: Strict Clock-Time Validation

- [x] T112 Write failing test that non-zero-padded replay `quote_time` fails CSV validation.
- [x] T113 Require zero-padded `HH:MM:SS` in shared clock-time validation.
- [x] T114 Update spec/analyze/data model artifacts for strict clock-time validation.

## Phase 38: Replay CSV Contract Clock Pattern

- [x] T115 Write failing contract test that replay CSV schema requires zero-padded `quote_time`.
- [x] T116 Add strict `quote_time` pattern to `contracts/replay-csv-schema.json`.
- [x] T117 Update analyze/tasks artifacts for replay CSV contract clock-pattern alignment.

## Phase 39: Replay CSV Trade Date Format Validation

- [x] T118 Write failing test that malformed CSV `trade_date` fails even when the command date matches the malformed value.
- [x] T119 Reject malformed CSV `trade_date` at the replay row parse boundary.
- [x] T120 Update spec/analyze/data model artifacts for replay CSV trade-date format validation.

## Phase 40: Replay CSV Finite Numeric Validation

- [x] T121 Write failing test that `NaN` or `Infinity` numeric CSV fields fail replay validation.
- [x] T122 Reject non-finite numeric values at the replay row parse boundary.
- [x] T123 Update spec/analyze/data model/contract artifacts for finite numeric replay validation.

## Phase 41: Intraday Plan Finite Numeric Validation

- [x] T124 Write failing test that non-finite plan numeric fields disable the plan before alerts.
- [x] T125 Require finite execution, risk, pre-close, and volume profile numeric values in plan validity.
- [x] T126 Update spec/analyze/data model artifacts for finite plan numeric validation.

## Phase 42: VWAP Confirmation Window Non-Negative Validation

- [x] T127 Write failing test that a negative `vwap_above_confirm_seconds` disables the plan before alerts.
- [x] T128 Require `vwap_above_confirm_seconds >= 0` in plan validity.
- [x] T129 Update spec/analyze/data model artifacts for VWAP confirmation window validation.

## Phase 43: Null Plan JSON Validation

- [x] T130 Write failing test that `NULL` `plan_json` disables the plan instead of crashing replay.
- [x] T131 Parse missing loaded `plan_json` as an invalid machine plan.
- [x] T132 Update spec/analyze/data model artifacts for null plan JSON validation.

## Phase 44: SQLite Boolean Plan Loading

- [x] T133 Write failing tests that text `false` does not become truthy for loaded plan booleans.
- [x] T134 Parse `allow_trade` and `volume_gate_enabled` as true only for integer/text `1`.
- [x] T135 Update spec/analyze/data model artifacts for SQLite boolean loading.

## Phase 45: Null VWAP Activation Window Validation

- [x] T136 Write failing test that `NULL` `vwap_active_after` disables the plan instead of crashing replay.
- [x] T137 Parse missing loaded `vwap_active_after` as an invalid activation window.
- [x] T138 Update spec/analyze/data model artifacts for null VWAP activation validation.

## Phase 46: Malformed Loaded Numeric Plan Validation

- [x] T139 Write failing tests that malformed loaded plan numeric fields disable the plan instead of crashing replay.
- [x] T140 Parse malformed loaded plan numeric fields into invalid plan values at the DB boundary.
- [x] T141 Update spec/plan/analyze/data model artifacts for malformed numeric plan loading.

## Phase 47: Replay CSV Symbol Validation

- [x] T142 Write failing tests that blank or whitespace-only CSV `ts_code` fails replay validation.
- [x] T143 Reject blank CSV `ts_code` values at the replay row parse boundary and align the replay CSV contract.
- [x] T144 Update spec/plan/analyze/data model artifacts for replay CSV symbol validation.

## Phase 48: Replay CSV Short Row Validation

- [x] T145 Write failing tests that short CSV rows missing required cells fail through replay validation.
- [x] T146 Reject missing required row cell values before field normalization can raise runtime access errors.
- [x] T147 Update spec/plan/analyze/data model artifacts for short-row validation.

## Phase 49: Replay CSV Long Row Validation

- [x] T148 Write failing test that long CSV rows with unnamed extra cells fail through replay validation.
- [x] T149 Reject unnamed extra row cells before replay can silently ignore trailing malformed input.
- [x] T150 Update spec/plan/analyze/data model artifacts for long-row validation.

## Phase 50: Replay CSV Header-Only Validation

- [x] T151 Write failing test that header-only replay CSV fails when B-class intraday plans exist.
- [x] T152 Reject empty validated replay rows as `REPLAY_CSV_NO_ROWS` only when same-date B-class plans exist.
- [x] T153 Update spec/plan/analyze/data model artifacts for header-only replay validation.

## Phase 51: Null VWAP Confirmation Window Validation

- [x] T154 Write failing test that `NULL` `vwap_above_confirm_seconds` disables the plan before alerts.
- [x] T155 Parse missing loaded VWAP confirmation windows as invalid plan values.
- [x] T156 Update spec/plan/analyze/data model artifacts for null VWAP confirmation validation.

## Phase 52: Stop Priority Over No-Volume VWAP

- [x] T157 Write failing test that a no-volume bar below `stop_price` emits pre-buy `ENTRY_CANCELLED`.
- [x] T158 Move pre-buy structural cancellation ahead of the VWAP-missing watch path.
- [x] T159 Update spec/plan/analyze artifacts for stop-priority replay behavior.

## Phase 53: Replay CSV Active Plan Symbol Coverage

- [x] T160 Write failing test that replay fails when active plan symbols are missing from CSV rows.
- [x] T161 Reject active-plan symbol coverage gaps as `REPLAY_CSV_MISSING_PLAN_SYMBOLS`.
- [x] T162 Update spec/plan/analyze/data model artifacts for replay symbol coverage.

## Phase 54: Malformed Snapshot Numeric Plan Materialization

- [x] T163 Write failing test that malformed snapshot numeric plan fields do not crash materialization.
- [x] T164 Parse malformed snapshot numeric fields into invalid plan values.
- [x] T165 Update spec/plan/analyze/data model artifacts for malformed snapshot numeric materialization.

## Phase 55: Replay CSV UTF-8 BOM Header Compatibility

- [x] T166 Write failing test that a UTF-8 BOM before `trade_date` does not break replay header validation.
- [x] T167 Read replay CSV input with BOM-aware UTF-8 decoding.
- [x] T168 Update spec/plan/analyze/data model artifacts for replay CSV BOM compatibility.

## Phase 56: Replay CSV Header Integrity Validation

- [x] T169 Write failing test that duplicate replay CSV header names are rejected before row parsing.
- [x] T170 Reject duplicate or blank replay CSV header names as `REPLAY_CSV_INVALID_HEADER`.
- [x] T171 Update spec/plan/analyze/data model artifacts for replay CSV header integrity.

## Phase 57: Candidate Snapshot Structured Plan Migration

- [x] T172 Write failing test that an existing pre-replay `candidate_snapshots` table can persist structured plan fields after `init_db`.
- [x] T173 Migrate existing `candidate_snapshots` tables with structured plan columns.
- [x] T174 Update spec/plan/analyze/data model artifacts for candidate snapshot plan-field migration.

## Phase 58: Intraday Table Replay MVP Migration

- [x] T175 Write failing test that an early `intraday_plans` table can accept full structured plans and run replay after `init_db`.
- [x] T176 Migrate early intraday tables with Replay MVP columns.
- [x] T177 Update spec/plan/analyze/data model artifacts for intraday table migration.

## Phase 59: Intraday Output Table Migration

- [x] T178 Write failing test that early intraday alert, lock, and replay-run tables can complete replay writes after `init_db`.
- [x] T179 Migrate early intraday output tables with Replay MVP write and query columns.
- [x] T180 Update spec/plan/analyze/data model artifacts for intraday output table migration.

## Phase 60: Replay Command Date Validation

- [x] T181 Write failing test that malformed command `--date` fails even on no-plan header-only replay input.
- [x] T182 Reject malformed command `--date` as `REPLAY_DATE_INVALID` after CSV row parsing and before date matching.
- [x] T183 Update spec/plan/analyze/data model artifacts for command date validation.

## Phase 61: Invalid Plan Visibility On Empty Replay Input

- [x] T184 Write failing test that header-only replay input still disables invalid B-class plans.
- [x] T185 Disable invalid plans before no-row or missing-symbol failure exits after CSV structure validation succeeds.
- [x] T186 Update spec/plan/analyze/data model artifacts for empty-input invalid-plan visibility.

## Phase 62: Missing File Command Date Priority

- [x] T187 Write failing test that malformed command `--date` is reported even when the replay input file is missing.
- [x] T188 Return `REPLAY_DATE_INVALID` before `REPLAY_CSV_FILE_NOT_FOUND` when no CSV row error can be preserved.
- [x] T189 Update spec/plan/analyze/data model artifacts for missing-file command-date priority.

## Phase 63: Replay CSV Parser Split

- [x] T190 Move replay CSV parsing from `intraday_replay.py` into `intraday_replay_csv.py`.
- [x] T191 Verify existing CSV validation tests preserve all replay input error semantics.
- [x] T192 Update plan/analyze/tasks artifacts for the parser split.

## Phase 64: Replay Report Reproducibility Metadata

- [x] T193 Write failing test that `replay_report.md` includes both `input_file` and the CSV SHA-256.
- [x] T194 Add `input_file` to replay report metadata without changing replay-run storage.
- [x] T195 Update spec/plan/analyze/data model artifacts for report-level reproducibility metadata.

## Phase 65: Unreadable Replay Input Handling

- [x] T196 Write failing test that a directory input records a failed replay run instead of crashing.
- [x] T197 Convert unreadable replay input paths into `REPLAY_CSV_UNREADABLE` and keep report/run metadata.
- [x] T198 Update spec/plan/analyze/data model/tasks artifacts for unreadable replay input handling.

## Phase 66: Post-Trigger Stop Cancellation Reason

- [x] T199 Write failing test that a post-`BUY_TRIGGER` stop break keeps `ENTRY_CANCELLED_PRICE_OUT_OF_RANGE`.
- [x] T200 Classify locked-plan stop breaks before VWAP-break cancellation.
- [x] T201 Update spec/plan/analyze/data model/tasks artifacts for post-trigger cancellation reason priority.

## Phase 67: Pre-VWAP Stop Cancellation Priority

- [x] T202 Write failing test that a pre-`vwap_active_after` stop break prevents later `BUY_TRIGGER`.
- [x] T203 Evaluate pre-buy stop breaks before the `vwap_active_after` gate.
- [x] T204 Update spec/plan/analyze/data model/tasks artifacts for pre-VWAP stop cancellation priority.

## Phase 68: Candidate Run Tie-Breaking

- [x] T205 Write failing test that equal-`generated_at` candidate runs materialize from one deterministic source run.
- [x] T206 Break `candidates_latest` timestamp ties by descending `run_id`.
- [x] T207 Update spec/plan/analyze/data model/tasks artifacts for candidate-run tie-breaking.

## Phase 69: No-Plan Replay Input Skip

- [x] T208 Write failing test that no-plan replay succeeds even when the input CSV file is absent.
- [x] T209 Short-circuit no-plan replay for absent input CSV after command-date validation.
- [x] T210 Move the missing-`volume_since_open` failure test into a planned replay fixture so CSV schema enforcement remains tied to actual evaluation.
- [x] T211 Update spec/plan/analyze/tasks artifacts for no-plan input skipping.

## Phase 70: Intraday Output Primary-Key Migration

- [x] T212 Write failing test that migrated early output tables assign non-null alert/run ids.
- [x] T213 Rebuild early intraday output tables when their primary-key constraints are missing.
- [x] T214 Update spec/plan/analyze/tasks artifacts for output-table primary-key migration.

## Phase 71: Intraday Plan Primary-Key Migration

- [x] T215 Write failing test that an early `intraday_plans` table regains its composite primary key after `init_db`.
- [x] T216 Rebuild early `intraday_plans` tables when their `(trade_date, ts_code, strategy_type)` primary-key constraint is missing.
- [x] T217 Update spec/plan/analyze/data model/tasks artifacts for plan-table primary-key migration.

## Phase 72: Intraday Plan Key Nullability

- [x] T218 Write failing test that an early `intraday_plans` table regains non-null key columns after `init_db`.
- [x] T219 Rebuild early `intraday_plans` tables when their key-column `NOT NULL` constraints are missing.
- [x] T220 Update spec/plan/analyze/data model/tasks artifacts for plan-key nullability.

## Phase 73: Alert Lock Key Nullability

- [x] T221 Write failing test that an early `intraday_alert_locks` table regains non-null key columns after `init_db`.
- [x] T222 Rebuild early `intraday_alert_locks` tables when their key-column `NOT NULL` constraints are missing.
- [x] T223 Update spec/plan/analyze/data model/tasks artifacts for alert-lock key nullability.

## Phase 74: Replay CSV Required Field Contract Coverage

- [x] T224 Add contract regression coverage for the exact replay CSV MVP field list, including `volume_since_open`.
- [x] T225 Verify the replay CSV contract field-list test.

## Phase 75: VWAP Confirmation Integer Loading

- [x] T226 Write failing test that fractional loaded `vwap_above_confirm_seconds` disables the plan.
- [x] T227 Reject fractional confirmation windows at the SQLite plan-loading boundary.
- [x] T228 Update spec/analyze/data model/tasks artifacts for strict confirmation-window loading.

## Phase 76: Intraday Alert Core Field Nullability

- [x] T229 Write failing schema migration test for non-null `intraday_alerts` core fields.
- [x] T230 Rebuild early `intraday_alerts` tables when replay alert core fields are nullable.
- [x] T231 Update spec/analyze/data model/tasks artifacts for alert core-field nullability.

## Phase 77: Replay Run Audit Field Nullability

- [x] T232 Write failing schema migration test for non-null `intraday_replay_runs` audit fields.
- [x] T233 Rebuild early `intraday_replay_runs` tables when replay-run audit fields are nullable.
- [x] T234 Update spec/analyze/data model/tasks artifacts for replay-run audit-field nullability.

## Phase 78: Replay CSV Runtime-Contract Alignment

- [x] T235 Add regression coverage that `replay-csv-schema.json.required` matches runtime `REQUIRED_REPLAY_COLUMNS`.
- [x] T236 Verify runtime-contract alignment for the replay CSV MVP field list.

## Phase 79: Replay CSV Named Extension Columns

- [x] T237 Add replay coverage that named extra CSV columns are accepted while unnamed extra cells remain invalid.
- [x] T238 Update analyze/tasks artifacts for replay CSV extension-column behavior.

## Phase 80: Structured Plan Fields Over Free Text

- [x] T239 Add plan materialization coverage that conflicting prose prices in `plan_json` do not rewrite execution fields.
- [x] T240 Update analyze/tasks artifacts for structured-field precedence over free text.

## Phase 81: Markdown Report Boundary

- [x] T241 Add plan materialization coverage that conflicting report Markdown prices do not rewrite execution fields.
- [x] T242 Update analyze/tasks artifacts for the Markdown boundary.

## Phase 82: No Sell Trigger Semantics

- [x] T243 Add replay coverage that a triggered plan breaking `stop_price` writes `ENTRY_CANCELLED` and never `SELL_TRIGGER`.
- [x] T244 Update analyze/tasks artifacts for explicit no-sell semantics coverage.
