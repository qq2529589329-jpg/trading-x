# Tasks: Intraday Replay MVP

**Input**: `spec.md`, `plan.md`, `data-model.md`, `contracts/replay-csv-schema.json`

**Tests**: Required before production code.

**History**: Detailed completed phases through Phase 82 are archived in `tasks-history.md`. Keep this file as the current Spec Kit task entrypoint and archive completed waves before it approaches 220 pure LOC.

## Completed Scope

- [x] T001-T244 Complete Replay MVP scope through Phase 82; see `tasks-history.md` for the detailed checklist.
- [x] T001-T244 Preserve the locked boundary: replay-only B-class alerts, structured plans, reproducible runs, no sell semantics, and no realtime watch.

## Phase 83: Task Ledger Split

- [x] T245 Archive the completed detailed task ledger in `tasks-history.md`.
- [x] T246 Keep `tasks.md` as a compact current Spec Kit task entrypoint.
- [x] T247 Update analyze artifact with the ledger split result.
- [x] T248 Run full verification after the docs-only split.

## Phase 84: B-Class Materialization Scope

- [x] T249 Add regression coverage that B-class plan materialization preserves non-B intraday plan rows.
- [x] T250 Scope `materialize_intraday_plans()` cleanup to same-date `B_CAPACITY_LEADER` rows.
- [x] T251 Update spec/plan/analyze/data-model/tasks artifacts for B-class materialization scope.
- [x] T252 Run full verification after the scope fix.

## Phase 85: B-Class Replay Output Scope

- [x] T253 Add regression coverage that B-class replay preserves non-B alert and lock rows.
- [x] T254 Scope replay output cleanup to same-date `B_CAPACITY_LEADER` alert and lock rows.
- [x] T255 Update spec/plan/analyze/data-model/tasks artifacts for B-class replay output scope.
- [x] T256 Run full verification after the output-scope fix.

## Phase 86: Spec Integrity Guard

- [x] T257 Add regression coverage that `spec.md` acceptance scenarios do not reuse numbering inside a story.
- [x] T258 Fix duplicated User Story 1 acceptance-scenario numbering.
- [x] T259 Update analyze/tasks artifacts for the Spec Kit integrity guard.
- [x] T260 Run full verification after the spec-integrity fix.

## Phase 87: VWAP Formula Snapshot Guard

- [x] T261 Add replay alert snapshot coverage that `continuous_vwap` is computed from amount divided by volume, not copied from price.
- [x] T262 Mutation-check the VWAP guard by temporarily forcing `continuous_vwap = price` and confirming the targeted test fails.
- [x] T263 Restore the production VWAP formula.
- [x] T264 Update analyze/tasks artifacts for the VWAP formula guard.
- [x] T265 Run full verification after the VWAP guard.

## Phase 88: Spec Numbering Continuity Guard

- [x] T266 Strengthen spec integrity coverage so acceptance scenarios fail on skipped numbering, not only duplicates.
- [x] T267 Add FR/SC contiguous id coverage.
- [x] T268 Mutation-check the guard by temporarily introducing numbering gaps and confirming the spec integrity test fails.
- [x] T269 Restore spec numbering and update analyze/tasks artifacts.
- [x] T270 Run full verification after the numbering-continuity guard.

## Phase 89: BUY_READY Duplicate Guard

- [x] T271 Add replay coverage that repeated same-reason BUY_READY alerts count once in the DB, `alert_count`, and replay report.
- [x] T272 Mutation-check the guard by temporarily disabling alert insert deduplication and confirming the targeted test fails.
- [x] T273 Restore production alert deduplication and update spec/analyze/tasks artifacts.
- [x] T274 Run full verification after the BUY_READY duplicate guard.

## Phase 90: Replay CSV Contract Numeric Bounds Guard

- [x] T275 Add contract coverage that replay CSV schema keeps runtime numeric lower bounds and named extra columns aligned with parser behavior.
- [x] T276 Mutation-check the guard by temporarily removing a numeric lower bound and confirming the targeted test fails.
- [x] T277 Restore the replay CSV contract and update spec/analyze/tasks artifacts.
- [x] T278 Run full verification after the contract numeric-bounds guard.

## Phase 91: Intraday MVP Boundary Guard

- [x] T279 Add boundary coverage that intraday runtime modules stay free of deferred sell, A-class, and realtime-provider tokens.
- [x] T280 Mutation-check the guard by temporarily inserting a deferred `SELL_TRIGGER` token and confirming the targeted test fails.
- [x] T281 Restore the production intraday runtime and update spec/analyze/tasks artifacts.
- [x] T282 Run full verification after the intraday MVP boundary guard.

## Phase 92: CLI Live Watch Boundary Guard

- [x] T283 Add CLI coverage that `trading_x watch` remains an unknown command in the Replay MVP.
- [x] T284 Mutation-check the guard by temporarily registering a `watch` subcommand and confirming the targeted test fails.
- [x] T285 Restore the production CLI and update spec/analyze/tasks artifacts.
- [x] T286 Run full verification after the CLI live-watch boundary guard.

## Phase 93: Intraday Output Primary-Key Migration Guard

- [x] T287 Add migration coverage that early intraday output tables restore `intraday_alerts`, `intraday_alert_locks`, and `intraday_replay_runs` primary-key columns.
- [x] T288 Mutation-check the guard by temporarily removing the alert-lock composite primary key and confirming the targeted test fails.
- [x] T289 Restore the production schema SQL and update analyze/tasks artifacts.
- [x] T290 Run full verification after the output primary-key guard.

## Phase 94: CLI Replay Failure Surface Guard

- [x] T291 Add CLI coverage that `trading_x replay --input` returns non-zero, prints the CSV validation reason, and records `intraday_replay_runs` on failure.
- [x] T292 Mutation-check the guard by temporarily returning success for failed replay CLI runs and confirming the targeted test fails.
- [x] T293 Restore the production CLI and update analyze/tasks artifacts.
- [x] T294 Run full verification after the CLI replay failure-surface guard.

## Phase 95: Complete Alert Snapshot Payload Guard

- [x] T295 Add alert snapshot coverage that locks the complete required replay bar payload: price, amount, volume, VWAP, `bar_high`, and `bar_low`.
- [x] T296 Mutation-check the guard by temporarily omitting `volume_since_open` from `snapshot_json` and confirming the targeted test fails.
- [x] T297 Restore the production alert snapshot payload and update analyze/tasks artifacts.
- [x] T298 Run full verification after the alert snapshot payload guard.

## Phase 96: Observation Alert Lock Boundary Guard

- [x] T299 Add replay coverage that `WATCH` and `BUY_READY` alerts do not create `intraday_alert_locks`.
- [x] T300 Mutation-check the guard by temporarily locking `WATCH` alerts and confirming the targeted test fails.
- [x] T301 Restore the production AlertLock write set and update analyze/tasks artifacts.
- [x] T302 Run full verification after the observation alert lock-boundary guard.

## Phase 97: Alert Lock Metadata Guard

- [x] T303 Add replay coverage that terminal alert locks keep the alert `created_at` timestamp and `reason_code` rule metadata.
- [x] T304 Mutation-check the guard by temporarily writing `alert_time` into `locked_at` and confirming the targeted test fails.
- [x] T305 Restore the production AlertLock metadata write path and update analyze/tasks artifacts.
- [x] T306 Run full verification after the alert lock metadata guard.

## Phase 98: Successful Replay Run Hash Guard

- [x] T307 Add replay coverage that successful `intraday_replay_runs` rows preserve the input file path, SHA-256, counts, status, and error state.
- [x] T308 Mutation-check the guard by temporarily writing an empty `input_sha256` into the replay-run row and confirming the targeted test fails.
- [x] T309 Restore the production replay-run metadata write path and update analyze/tasks artifacts.
- [x] T310 Run full verification after the successful replay-run hash guard.

## Phase 99: Failed Replay Run Hash Guard

- [x] T311 Add replay coverage that CSV validation failures preserve the input file path and SHA-256 in `intraday_replay_runs` and `replay_report.md`.
- [x] T312 Mutation-check the guard by temporarily writing an empty `input_sha256` into the replay-run row and confirming the targeted test fails.
- [x] T313 Restore the production replay-run metadata write path and update analyze/tasks artifacts.
- [x] T314 Run full verification after the failed replay-run hash guard.

## Phase 100: Replay Run Append-Only Hash Guard

- [x] T315 Add replay coverage that same-date reruns after input CSV changes preserve distinct `intraday_replay_runs` rows and SHA-256 values.
- [x] T316 Mutation-check the guard by temporarily deleting same-date replay-run rows before insert and confirming the targeted test fails.
- [x] T317 Restore the production append-only replay-run write path and update analyze/tasks artifacts.
- [x] T318 Run full verification after the append-only replay-run guard.

## Phase 101: Daily Pre-Close Fallback Guard

- [x] T319 Add plan materialization coverage that falls back to `daily_quotes.pre_close` when `stk_limit_prices.pre_close` is missing.
- [x] T320 Mutation-check the guard by temporarily disabling the daily pre-close fallback and confirming the targeted test fails.
- [x] T321 Restore the production `PreCloseProvider` fallback and update analyze/tasks artifacts.
- [x] T322 Run full verification after the daily pre-close fallback guard.

## Phase 102: Missing Pre-Close Source Guard

- [x] T323 Add plan materialization coverage that records `pre_close_source = missing` when both limit and daily pre-close are unavailable.
- [x] T324 Mutation-check the guard by temporarily changing the missing pre-close source and confirming the targeted test fails.
- [x] T325 Restore the production `PreCloseProvider` missing-source path and update analyze/tasks artifacts.
- [x] T326 Run full verification after the missing pre-close guard.

## Phase 103: Zero-Volume VWAP Guard

- [x] T327 Add replay coverage that zero cumulative volume cannot synthesize a VWAP and only emits `WATCH / VOLUME_GATE_FAILED`.
- [x] T328 Mutation-check the guard by temporarily returning price as zero-volume VWAP and confirming the targeted test fails.
- [x] T329 Restore the production `VWAPEngine` zero-volume path and update analyze/tasks artifacts.
- [x] T330 Run full verification after the zero-volume VWAP guard.

## Phase 104: Zero-Volume Snapshot VWAP Guard

- [x] T331 Add alert snapshot coverage that zero cumulative volume records `continuous_vwap = null`.
- [x] T332 Mutation-check the guard by temporarily filling snapshot VWAP from price and confirming the targeted test fails.
- [x] T333 Restore the production alert snapshot VWAP field and update analyze/tasks artifacts.
- [x] T334 Run full verification after the zero-volume snapshot guard.

## Phase 105: CLI Default Replay Input Guard

- [x] T335 Add CLI coverage that omitting `--input` reads `data/replay/<date>.csv`.
- [x] T336 Mutation-check the guard by temporarily changing the default replay input directory and confirming the targeted test fails.
- [x] T337 Restore the production CLI default input path and update analyze/tasks artifacts.
- [x] T338 Run full verification after the CLI default-input guard.

## Phase 106: CLI Plan Materialize Guard

- [x] T339 Add CLI coverage that `plans materialize --date` writes structured `intraday_plans` and prints the count.
- [x] T340 Mutation-check the guard by temporarily bypassing `materialize_intraday_plans()` and confirming the targeted test fails.
- [x] T341 Restore the production CLI materialization call and update analyze/tasks artifacts.
- [x] T342 Run full verification after the CLI materialize guard.

## Phase 107: Replay Report Alert Reason Guard

- [x] T343 Add replay report coverage that successful alert lines include alert time, stock, alert type, and `reason_code`.
- [x] T344 Mutation-check the guard by temporarily omitting `reason_code` from report alert lines and confirming the targeted test fails.
- [x] T345 Restore the production replay report alert line and update analyze/tasks artifacts.
- [x] T346 Run full verification after the replay-report alert reason guard.

## Phase 108: Replay Run Timing Metadata Guard

- [x] T347 Extend successful replay-run coverage to assert `started_at` and `ended_at` persist from `ReplayResult` into `intraday_replay_runs`.
- [x] T348 Mutation-check the guard by temporarily writing a blank `started_at` into the replay-run row and confirming the targeted test fails.
- [x] T349 Restore the production replay-run timing write path and update analyze/tasks artifacts.
- [x] T350 Run full verification after the replay-run timing metadata guard.

## Phase 109: Alert Lock Reset Metadata Guard

- [x] T351 Extend terminal alert-lock metadata coverage to assert new locks start with `reset_count = 0` and `reset_reason = NULL`.
- [x] T352 Mutation-check the guard by temporarily writing `reset_count = 1` during lock insert and confirming the targeted test fails.
- [x] T353 Restore the production AlertLock insert path and update analyze/tasks artifacts.
- [x] T354 Run full verification after the alert-lock reset metadata guard.

## Phase 110: Failed Replay Run Timing Guard

- [x] T355 Extend CSV validation failure coverage to assert failed `ReplayResult` timing persists into `intraday_replay_runs`.
- [x] T356 Mutation-check the guard by temporarily blanking failed-run `ended_at` and confirming the targeted test fails.
- [x] T357 Restore the production failed replay timing path and update analyze/tasks artifacts.
- [x] T358 Run full verification after the failed replay-run timing guard.

## Phase 111: Alert Plan JSON Snapshot Guard

- [x] T359 Add alert coverage that `intraday_alerts.plan_json` preserves the triggering `intraday_plans.plan_json` machine payload.
- [x] T360 Mutation-check the guard by temporarily writing `{}` into alert `plan_json` and confirming the targeted test fails.
- [x] T361 Restore the production alert plan snapshot path and update analyze/tasks artifacts.
- [x] T362 Run full verification after the alert plan-json snapshot guard.

## Phase 112: Alert State Transition Metadata Guard

- [x] T363 Add alert coverage that `intraday_alerts.state_before` and `state_after` preserve the rule intent transition.
- [x] T364 Mutation-check the guard by temporarily writing `state_before` into `state_after` and confirming the targeted test fails.
- [x] T365 Restore the production alert state transition path and update analyze/tasks artifacts.
- [x] T366 Run full verification after the alert state-transition metadata guard.

## Phase 113: Alert Readable Metadata Guard

- [x] T367 Add alert coverage that `intraday_alerts.severity`, `title`, and `message` preserve readable rule metadata.
- [x] T368 Mutation-check the guard by temporarily writing the alert type into `message` and confirming the targeted test fails.
- [x] T369 Restore the production alert readable metadata path and update analyze/tasks artifacts.
- [x] T370 Run full verification after the alert readable-metadata guard.

## Phase 114: Alert Rule ID Pair Guard

- [x] T371 Add alert coverage that `intraday_alerts.rule_id` stays paired with `reason_code`.
- [x] T372 Mutation-check the guard by temporarily writing the alert type into `rule_id` and confirming the targeted test fails.
- [x] T373 Restore the production alert rule-id path and update analyze/tasks artifacts.
- [x] T374 Run full verification after the alert rule-id pair guard.

## Phase 115: Alert Created Timestamp Guard

- [x] T375 Add alert coverage that `intraday_alerts.created_at` is a UTC audit timestamp separate from replay `alert_time`.
- [x] T376 Mutation-check the guard by temporarily writing `bar.quote_time` into `created_at` and confirming the targeted test fails.
- [x] T377 Restore the production alert created-timestamp path and update analyze/tasks artifacts.
- [x] T378 Run full verification after the alert created-timestamp guard.

## Phase 116: Entry-Cancelled State Transition Guard

- [x] T379 Add replay coverage that `ENTRY_CANCELLED` preserves distinct pre-buy and post-buy state transitions.
- [x] T380 Mutation-check the guard by temporarily downgrading the post-buy cancellation state and confirming the targeted test fails.
- [x] T381 Restore the production `ENTRY_CANCELLED` state transition path and update analyze/tasks artifacts.
- [x] T382 Run full verification after the entry-cancelled state-transition guard.

## Phase 117: Observation Alert State Transition Guard

- [x] T383 Add replay coverage that `WATCH` remains `OPEN_OBSERVING` while `BUY_READY` advances to `BUY_READY`.
- [x] T384 Mutation-check the guard by temporarily downgrading `BUY_READY.state_after` and confirming the targeted test fails.
- [x] T385 Restore the production observation alert state transition path and update analyze/tasks artifacts.
- [x] T386 Run full verification after the observation alert state-transition guard.

## Phase 118: Missing Pre-Close Watch Boundary Guard

- [x] T387 Add replay coverage that `PRE_CLOSE_MISSING` writes only a non-terminal `WATCH` alert and no alert lock.
- [x] T388 Mutation-check the guard by temporarily advancing `PRE_CLOSE_MISSING.state_after` and confirming the targeted test fails.
- [x] T389 Restore the production missing-pre-close watch path and update analyze/tasks artifacts.
- [x] T390 Run full verification after the missing-pre-close watch-boundary guard.

## Phase 119: Non-Buy Alert Readable Metadata Guard

- [x] T391 Add replay coverage that `WATCH`, `BUY_READY`, and `ENTRY_CANCELLED` preserve readable alert metadata.
- [x] T392 Mutation-check the guard by temporarily writing the stock code into alert `title` and confirming the targeted test fails.
- [x] T393 Restore the production non-buy alert metadata path and update analyze/tasks artifacts.
- [x] T394 Run full verification after the non-buy alert readable-metadata guard.

## Phase 120: Unreadable Input Report Hash Guard

- [x] T395 Extend unreadable-input replay coverage to assert failed `replay_report.md` still includes the `input_sha256` field.
- [x] T396 Mutation-check the guard by temporarily omitting `input_sha256` from replay reports and confirming the targeted test fails.
- [x] T397 Restore the production replay report metadata path and update analyze/tasks artifacts.
- [x] T398 Run full verification after the unreadable-input report hash guard.

## Phase 121: Legacy Replay-Run Audit Field Migration Guard

- [x] T399 Add migration coverage that legacy `intraday_replay_runs` rows missing required audit fields are dropped during rebuild.
- [x] T400 Mutation-check the guard by temporarily allowing missing `input_sha256` through replay-run migration and confirming the targeted test fails.
- [x] T401 Restore the production replay-run migration filter and update analyze/tasks artifacts.
- [x] T402 Run full verification after the legacy replay-run audit-field migration guard.

## Phase 122: Legacy Alert Reason-Code Migration Guard

- [x] T403 Add migration coverage that legacy `intraday_alerts` rows missing required `reason_code` are dropped during rebuild.
- [x] T404 Mutation-check the guard by temporarily allowing missing `reason_code` through alert migration and confirming the targeted test fails.
- [x] T405 Restore the production alert migration filter and update analyze/tasks artifacts.
- [x] T406 Run full verification after the legacy alert reason-code migration guard.

## Phase 123: Legacy Alert-Lock Key Migration Guard

- [x] T407 Add migration coverage that legacy `intraday_alert_locks` rows missing required key fields are dropped during rebuild.
- [x] T408 Mutation-check the guard by temporarily allowing missing `alert_type` through alert-lock migration and confirming the targeted test fails.
- [x] T409 Restore the production alert-lock migration filter and update analyze/tasks artifacts.
- [x] T410 Run full verification after the legacy alert-lock key migration guard.

## Phase 124: Legacy Intraday-Plan Key Migration Guard

- [x] T411 Add migration coverage that legacy `intraday_plans` rows missing required key fields are dropped during rebuild.
- [x] T412 Mutation-check the guard by temporarily allowing missing `strategy_type` through plan migration and confirming the targeted test fails.
- [x] T413 Restore the production plan migration filter and update analyze/tasks artifacts.
- [x] T414 Run full verification after the legacy intraday-plan key migration guard.

## Phase 125: Realtime Provider Boundary Token Guard

- [x] T415 Extend MVP boundary coverage to block abstract realtime provider and live-watch entrypoint tokens in `src/trading_x/intraday*.py`.
- [x] T416 Mutation-check the guard by temporarily introducing `IntradayDataProvider` and confirming the targeted test fails.
- [x] T417 Restore the production runtime source and update analyze/tasks artifacts.
- [x] T418 Run full verification after the realtime provider boundary-token guard.

## Phase 126: Plan Source-Date Consistency Guard

- [x] T419 Add replay coverage that a B-class plan with `source_report_date != trade_date` is disabled before alert evaluation.
- [x] T420 Implement the minimal `IntradayPlan.is_valid` source-date consistency check.
- [x] T421 Mutation-check the guard by temporarily removing the consistency check and confirming the targeted test fails.
- [x] T422 Restore the production validation path and update Spec Kit artifacts.

## Phase 127: Plan Source-Candidate Guard

- [x] T423 Add replay coverage that a B-class plan with blank `source_candidate_id` is disabled before alert evaluation.
- [x] T424 Implement the minimal `IntradayPlan.is_valid` source-candidate presence check and DB row string coercion.
- [x] T425 Mutation-check the guard by temporarily removing the presence check and confirming the targeted test fails.
- [x] T426 Restore the production validation path and update Spec Kit artifacts.

## Phase 128: Plan System-Version Guard

- [x] T427 Add replay coverage that a B-class plan with blank `system_version` is disabled before alert evaluation.
- [x] T428 Implement the minimal `IntradayPlan.is_valid` system-version presence check and DB row string coercion.
- [x] T429 Mutation-check the guard by temporarily removing the presence check and confirming the targeted test fails.
- [x] T430 Restore the production validation path and update Spec Kit artifacts.

## Phase 129: Plan Created-At Guard

- [x] T431 Add replay coverage that a B-class plan with blank `created_at` is disabled before alert evaluation.
- [x] T432 Implement the minimal `IntradayPlan.is_valid` created-at presence check and DB row string coercion.
- [x] T433 Mutation-check the guard by temporarily removing the presence check and confirming the targeted test fails.
- [x] T434 Restore the production validation path and update Spec Kit artifacts.

## Phase 130: Plan Pre-Close Source Guard

- [x] T435 Add replay coverage that a B-class plan with blank `pre_close_source` is disabled before alert evaluation.
- [x] T436 Implement the minimal `IntradayPlan.is_valid` pre-close-source presence check and DB row string coercion.
- [x] T437 Mutation-check the guard by temporarily removing the presence check and confirming the targeted test fails.
- [x] T438 Restore the production validation path and update Spec Kit artifacts.

## Phase 131: Plan Stock-Code Guard

- [x] T439 Add replay coverage that a B-class plan with blank `ts_code` is disabled before alert evaluation.
- [x] T440 Implement the minimal `IntradayPlan.is_valid` stock-code presence check and DB row string coercion.
- [x] T441 Mutation-check the guard by temporarily removing the presence check and confirming the targeted test fails.
- [x] T442 Restore the production validation path and update Spec Kit artifacts.

## Phase 132: Plan Name Guard

- [x] T443 Add replay coverage that a B-class plan with blank `name` is disabled before alert evaluation.
- [x] T444 Implement the minimal `IntradayPlan.is_valid` name presence check and DB row string coercion.
- [x] T445 Mutation-check the guard by temporarily removing the presence check and confirming the targeted test fails.
- [x] T446 Restore the production validation path and update Spec Kit artifacts.

## Phase 133: Zero-Volume Entry-Zone Guard

- [x] T447 Add replay coverage that a zero-volume bar below `entry_low` does not emit `WATCH / VOLUME_GATE_FAILED`.
- [x] T448 Implement the minimal `VolumeGate` rule guard that keeps below-entry zero-volume bars silent unless stop breaks.
- [x] T449 Mutation-check the guard by temporarily restoring unconditional zero-volume WATCH and confirming the targeted test fails.
- [x] T450 Restore the production rule path and update Spec Kit artifacts.

## Phase 134: Zero-Volume Entry-Ceiling Guard

- [x] T451 Add replay coverage that a zero-volume bar above `entry_high` does not emit `WATCH / VOLUME_GATE_FAILED`.
- [x] T452 Implement the minimal `VolumeGate` rule guard that keeps above-entry zero-volume bars silent.
- [x] T453 Mutation-check the guard by temporarily restoring `bar.price >= entry_low` and confirming the targeted test fails.
- [x] T454 Restore the production rule path and update Spec Kit artifacts.

## Phase 135: Volume-Gate Entry-Ceiling Guard

- [x] T455 Add replay coverage that a VWAP-calculable bar above `entry_high` with insufficient amount does not emit `WATCH / VOLUME_GATE_FAILED`.
- [x] T456 Implement the minimal `VolumeGate` rule guard that keeps amount-threshold failures inside the entry range.
- [x] T457 Mutation-check the guard by temporarily restoring `bar.price >= entry_low` and confirming the targeted test fails.
- [x] T458 Restore the production rule path and update Spec Kit artifacts.

## Phase 136: VWAP-Confirming Entry-Ceiling Guard

- [x] T459 Add replay coverage that a VWAP-confirming bar above `entry_high` does not emit `WATCH / B_VWAP_CONFIRMING`.
- [x] T460 Implement the minimal B-class rule guard that keeps confirming WATCH alerts inside the entry range.
- [x] T461 Mutation-check the guard by temporarily restoring `bar.price >= entry_low` and confirming the targeted test fails.
- [x] T462 Restore the production rule path and update Spec Kit artifacts.

## Phase 137: Volume-Gated VWAP Timer Guard

- [x] T463 Add replay coverage that under-threshold above-VWAP bars do not start `vwap_above_confirm_seconds`.
- [x] T464 Implement the minimal replay evaluator guard that starts VWAP confirmation timing only after the volume gate passes.
- [x] T465 Mutation-check the guard by temporarily removing the volume gate from `_is_above_active_vwap` and confirming the targeted test fails.
- [x] T466 Restore the production replay evaluator path and update Spec Kit artifacts.

## Phase 138: Entry-Range VWAP Timer Guard

- [x] T467 Add replay coverage that chased-zone above-VWAP bars do not start `vwap_above_confirm_seconds`.
- [x] T468 Implement the minimal replay evaluator guard that starts VWAP confirmation timing only inside the entry range.
- [x] T469 Mutation-check the guard by temporarily removing the entry-range check from `_is_above_active_vwap` and confirming the targeted test fails.
- [x] T470 Restore the production replay evaluator path and update Spec Kit artifacts.

## Phase 139: Replay CSV Duplicate Snapshot Guard

- [x] T471 Add replay coverage that duplicate same-stock same-`quote_time` CSV rows fail before alert evaluation.
- [x] T472 Implement the minimal CSV parser guard that rejects duplicate `(ts_code, quote_time)` points.
- [x] T473 Mutation-check the guard by temporarily removing the duplicate-point check and confirming the targeted test fails.
- [x] T474 Restore the production parser path and update Spec Kit artifacts.

## Phase 140: Replay CSV Positive-Volume Amount Guard

- [x] T475 Add replay coverage that positive `volume_since_open` with zero `amount_since_open` fails before VWAP calculation.
- [x] T476 Implement the minimal CSV parser guard that rejects zero cumulative amount when cumulative volume is positive.
- [x] T477 Add replay CSV contract coverage for the same positive-volume/positive-amount rule.
- [x] T478 Mutation-check the guard by temporarily removing the runtime condition and confirming the targeted test fails.
- [x] T479 Restore the production parser path and update Spec Kit artifacts.

## Phase 141: Negative Pre-Close Plan Guard

- [x] T480 Add replay coverage that negative `official_pre_close` disables a B-class plan before `PRE_CLOSE_MISSING`.
- [x] T481 Implement the minimal `IntradayPlan.is_valid` guard requiring non-negative `official_pre_close`.
- [x] T482 Mutation-check the guard by temporarily removing it and confirming the targeted test fails.
- [x] T483 Restore the production validation path and update Spec Kit artifacts.

## Phase 142: Malformed Loaded Pre-Close Guard

- [x] T484 Extend loaded numeric-field coverage so malformed `official_pre_close` cannot become missing-pre-close WATCH.
- [x] T485 Parse malformed loaded float fields to non-finite invalid plan values at the DB boundary.
- [x] T486 Mutation-check the guard by temporarily coercing malformed floats to `0.0` and confirming the targeted test fails.
- [x] T487 Restore production parsing and update Spec Kit artifacts.

## Phase 143: Malformed Pre-Close Source Guard

- [x] T488 Add materialization-to-replay coverage that malformed pre-close source data cannot emit `PRE_CLOSE_MISSING`.
- [x] T489 Preserve malformed pre-close source values as invalid materialized plan data.
- [x] T490 Mutation-check the guard by temporarily treating malformed source values as missing and confirming the targeted test fails.
- [x] T491 Restore production materialization and update Spec Kit artifacts.

## Phase 144: Sell-Semantics Boundary Token Guard

- [x] T492 Extend MVP boundary coverage to block sell-warning, T+1, available-shares, entry-date, and sell-guidance tokens in `src/trading_x/intraday*.py`.
- [x] T493 Mutation-check the guard by temporarily introducing a deferred sell-semantics token and confirming the targeted boundary test fails.
- [x] T494 Restore runtime source and update Spec Kit artifacts.

## Phase 145: Blank Alert Reason-Code Migration Guard

- [x] T495 Extend legacy `intraday_alerts` migration coverage so whitespace-only `reason_code` rows are dropped.
- [x] T496 Filter blank or whitespace-only `reason_code` values during alert-table rebuild.
- [x] T497 Mutation-check by temporarily restoring the null-only migration filter and confirming the targeted test fails.
- [x] T498 Restore production migration filtering and update Spec Kit artifacts.

## Phase 146: Blank Alert-Lock Key Migration Guard

- [x] T499 Extend legacy `intraday_alert_locks` migration coverage so whitespace-only composite-key rows are dropped.
- [x] T500 Filter blank or whitespace-only alert-lock key fields during table rebuild.
- [x] T501 Mutation-check by temporarily restoring the null-only lock-key migration filter and confirming the targeted test fails.
- [x] T502 Restore production migration filtering and update Spec Kit artifacts.

## Phase 147: Blank Intraday-Plan Key Migration Guard

- [x] T503 Extend legacy `intraday_plans` migration coverage so whitespace-only composite-key rows are dropped.
- [x] T504 Filter blank or whitespace-only plan key fields during table rebuild.
- [x] T505 Mutation-check by temporarily restoring the null-only plan-key migration filter and confirming the targeted test fails.
- [x] T506 Restore production migration filtering and update Spec Kit artifacts.

## Phase 148: Blank Replay-Run Audit Migration Guard

- [x] T507 Extend legacy `intraday_replay_runs` migration coverage so whitespace-only status rows are dropped.
- [x] T508 Filter blank or whitespace-only replay-run text audit fields during table rebuild while preserving empty `input_sha256`.
- [x] T509 Mutation-check by temporarily restoring the null-only replay-run audit filter and confirming the targeted test fails.
- [x] T510 Restore production migration filtering and update Spec Kit artifacts.

## Phase 149: Replay-Run Status Enum Migration Guard

- [x] T511 Extend legacy `intraday_replay_runs` migration coverage so statuses outside `SUCCESS / FAILED` are dropped.
- [x] T512 Filter invalid replay-run statuses during table rebuild.
- [x] T513 Mutation-check by temporarily restoring the nonblank-only replay-run status filter and confirming the targeted test fails.
- [x] T514 Restore production migration filtering and update Spec Kit artifacts.

## Phase 150: Blank Alert Core Field Migration Guard

- [x] T515 Extend legacy `intraday_alerts` migration coverage so whitespace-only core text field rows are dropped.
- [x] T516 Filter blank or whitespace-only alert core text fields during table rebuild.
- [x] T517 Mutation-check by temporarily restoring a null-only core-field filter and confirming the targeted test fails.
- [x] T518 Restore production migration filtering and update Spec Kit artifacts.
