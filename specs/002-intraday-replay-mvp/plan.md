# Implementation Plan: Intraday Replay MVP

**Branch**: `002-intraday-replay-mvp` | **Date**: 2026-06-30 | **Spec**: `specs/002-intraday-replay-mvp/spec.md`

## Summary

Add replay-first intraday discipline alerts for B-class capacity leaders. The implementation reuses the existing Python CLI, SQLite database, report/candidate data, and test stack. It does not add live data, sell triggers, brokerage integration, or UI.

## Technical Context

**Language/Version**: Python 3.11+

**Primary Dependencies**: standard library only for replay MVP; existing `tushare` dependency remains for V1 data updates.

**Storage**: SQLite at `data/trading_x.db`

**Testing**: `pytest`, `pyright`, `ruff`

**Input**: CSV with `trade_date,quote_time,ts_code,price,amount_since_open,volume_since_open,bar_high,bar_low`

**Output**: `intraday_alerts`, `intraday_replay_runs`, `reports/<date>_replay_report.md`

## Constitution Check

- Discipline boundary: pass. No automatic orders or sell instructions.
- Data capability first: pass. Replay uses structured plans and validates CSV before strategy evaluation.
- JSON as machine truth: pass. Plans are machine-readable rows with `plan_json`.
- Structured plans before alerts: pass. Markdown is never parsed for execution.
- Replay before live watch: pass. No realtime provider is introduced.
- Reproducible runs before tuning: pass. Input SHA-256 is recorded.
- No sell semantics without positions: pass. Stop failure emits `ENTRY_CANCELLED`.

## Implementation Notes

- Add schema tables in `schema.sql`.
- Persist structured plan prices on candidate snapshots, then materialize `intraday_plans` from the latest snapshot for production replay.
- Break latest candidate-run timestamp ties by descending `run_id`, so `candidates_latest` feeds one deterministic source run into materialization.
- Migrate existing `candidate_snapshots` tables with structured plan columns during `init_db`, so existing local databases can keep using the report-to-plan handoff.
- Migrate existing early intraday plan tables with Replay MVP columns, restored composite primary-key behavior, and non-null key columns during `init_db`, so local databases created by earlier MVP iterations can still replay with one machine plan per stock/strategy.
- Drop legacy plan rows with blank or whitespace-only composite-key fields during `intraday_plans` rebuild, keeping machine plans addressable.
- Migrate existing intraday output tables during `init_db`, so replay can write alerts, locks, and run records with restored primary-key behavior and non-null lock keys on older local databases.
- Treat an empty latest B-class candidate snapshot as authoritative; only use direct `candidates` fallback when no report run exists for fixture setup.
- Add replay modules for CSV parsing, VWAP/volume gate, alert locking, replay run persistence, and report rendering.
- Keep replay CSV parsing in its own module so `run_replay` remains an orchestration surface rather than a mixed parser/evaluator.
- Include both `input_file` and `input_sha256` in `replay_report.md`, matching the replay-run reproducibility record.
- Reject malformed command `--date` values after CSV row parsing and before date matching, so no-plan header-only inputs cannot report success under an invalid date.
- Report malformed command `--date` before file-not-found when the replay input file is missing, while preserving malformed CSV row errors when rows are available.
- Convert unreadable replay input paths, including directories, into `REPLAY_CSV_UNREADABLE` through the normal failed-run reporting path.
- Reject blank CSV `ts_code` values at the replay row parse boundary before symbol grouping.
- Reject short CSV rows with missing required cells through the standard invalid-row replay path.
- Reject long CSV rows with unnamed extra cells through the standard invalid-row replay path.
- Reject header-only replay CSV files as `REPLAY_CSV_NO_ROWS` when same-date B-class plans exist; preserve no-plan report success for empty replay inputs.
- Short-circuit no-plan replay when the command date is valid and the input CSV is absent, so daily batch jobs without candidates still produce a successful replay report when no CSV was exported.
- Disable invalid same-date B-class plans before no-row and missing-symbol failure exits once CSV structure validation has succeeded.
- Reject replay CSV files that omit active B-class plan symbols, so replay cannot report success without evaluating a candidate.
- Accept UTF-8 replay CSV files with a BOM before the first header name.
- Reject duplicate or blank replay CSV header names before row parsing.
- Reject duplicate same-stock same-`quote_time` replay rows before strategy evaluation.
- Reject positive-volume replay rows whose cumulative amount is zero before VWAP calculation.
- Parse loaded plan numeric fields at the DB boundary so malformed fixture or persisted values become `PLAN_INVALID` instead of runtime conversion crashes.
- Drop legacy alert rows with blank or whitespace-only `reason_code` during `intraday_alerts` rebuild, keeping reason-code statistics classifiable.
- Drop legacy alert rows with blank or whitespace-only core text fields during `intraday_alerts` rebuild, keeping migrated alert rows addressable.
- Drop legacy replay-run rows with blank or whitespace-only text audit fields during `intraday_replay_runs` rebuild, while preserving empty `input_sha256` for unreadable-input failures.
- Drop legacy replay-run rows whose status is outside `SUCCESS / FAILED` during `intraday_replay_runs` rebuild.
- Disable plans with negative `official_pre_close` before alert evaluation, while preserving `0.0` as the missing-pre-close sentinel for `WATCH / PRE_CLOSE_MISSING`.
- Keep malformed loaded `official_pre_close` distinct from the explicit `0.0` missing-pre-close sentinel by parsing bad numeric text to an invalid plan value.
- Keep malformed pre-close source values during plan materialization distinct from true missing pre-close, so bad source data cannot create `PRE_CLOSE_MISSING` alerts.
- Keep sell-warning, T+1, available-shares, entry-date, and sell-guidance tokens out of `src/trading_x/intraday*.py`, so positions-era semantics cannot enter the Replay MVP runtime.
- Parse malformed candidate snapshot numeric fields during materialization into invalid plan values, preserving the replay validation path instead of crashing before replay.
- Parse missing loaded VWAP confirmation windows as invalid plan values instead of silently converting them to zero-second confirmation.
- Keep pre-buy structural cancellation ahead of VWAP/volume observation, so missing volume cannot hide a stop break.
- Keep pre-buy structural cancellation outside the `vwap_active_after` gate, so early stop breaks disable the plan before later breakout bars.
- Keep post-buy-trigger structural cancellation ahead of VWAP-break cancellation, so reason-code statistics distinguish stop breaks from VWAP failures.
- Add CLI `plans materialize` subcommand for the production candidate-to-plan handoff.
- Keep B-class plan materialization scoped to `B_CAPACITY_LEADER` rows so the MVP command does not clear non-B plans owned by future specification lines.
- Keep B-class replay output cleanup scoped to `B_CAPACITY_LEADER` alerts and locks for the same reason.
- Drop legacy alert-lock rows with blank or whitespace-only composite-key fields during `intraday_alert_locks` rebuild, keeping locks addressable.
- Add CLI `replay` subcommand in `cli.py`.
- Keep constants boring and explicit. Do not add a plugin system or live data abstraction in this MVP.

## Complexity Tracking

No constitution violations are planned.
