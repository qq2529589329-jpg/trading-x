# Implementation Plan: A-Class Replay MVP

**Branch**: `006-a-class-replay-mvp` | **Date**: 2026-07-07 | **Spec**: `specs/006-a-class-replay-mvp/spec.md`

## Summary

Add an explicit A-class replay path on top of the existing intraday replay pipeline. The default CLI and Python API remain B-class, preserving the 002 Replay MVP boundary.

## Technical Context

**Language/Version**: Python 3.11+

**Primary Dependencies**: standard library and existing project stack only.

**Storage**: Existing SQLite tables: `intraday_plans`, `intraday_alerts`, `intraday_alert_locks`, `intraday_replay_runs`.

**Testing**: `pytest`, `pyright`, `ruff`.

## Constitution Check

- Structured plans before alerts: pass. A-class execution values come from structured candidate and daily quote/limit data.
- Replay before live watch: pass. No realtime data source is introduced.
- Reproducible runs before tuning: pass. Replay still records input file hash through the existing run record.
- No sell semantics without positions: pass. A-class replay does not add sell alerts.

## Implementation Notes

- Add optional `strategy_type` parameters to plan materialization, plan loading, and replay orchestration; default stays `B_CAPACITY_LEADER`.
- Add CLI `--strategy` to `plans materialize` and `replay` with choices from `StrategyType`.
- Add `replay --materialize` as the minimal daily replay shortcut, reusing the existing materializer instead of a new orchestration command.
- Derive the A-class entry/breakout price from structured limit/daily price fields, preferring `stk_limit_prices.up_limit` then daily close/high.
- Keep A-class volume gate disabled in this MVP; B-class VWAP/volume discipline remains unchanged.
- Emit `A_BUY_TRIGGERED` only on explicit A-class replay.
