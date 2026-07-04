# Implementation Plan: Intraday Live Watch

**Branch**: `003-intraday-live-watch` | **Date**: 2026-07-03 | **Spec**: `specs/003-intraday-live-watch/spec.md`

## Summary

Add a read-only live-watch specification line that proves watch behavior with a fake provider before evaluating real data sources. This line reuses existing B-class plans, rules, alert storage, locks, replay fixtures, pytest, pyright, ruff, and GitHub Actions.

## Technical Context

**Language/Version**: Python 3.11+

**Primary Dependencies**: standard library for fake provider and watch orchestration.

**Storage**: Existing SQLite tables: `intraday_plans`, `intraday_alerts`, `intraday_alert_locks`.

**Testing**: `pytest`, `pyright`, `ruff`, replay fixture parity tests.

**Input**: Typed provider snapshots with the same fields as Replay MVP bars.

**Output**: Existing alert and lock rows. No orders, positions, or sell triggers.

## Constitution Check

- Discipline boundary: pass. Watch is read-only and cannot place orders.
- Structured plans before alerts: pass. Watch reads `intraday_plans`.
- Replay before live watch: pass. Fake provider parity with replay is required before real providers.
- Reproducible runs before tuning: pass. Replay fixtures remain the correctness baseline.
- No sell semantics without positions: pass. Stop failure remains `ENTRY_CANCELLED`.

## Implementation Notes

- Introduce provider protocol only when implementation starts; do not add a plugin system.
- Fake provider reads fixed rows and returns snapshots for requested symbols.
- Watch should call existing B-class alert evaluation surfaces where possible.
- Keep real provider evaluation as documentation or tests until field completeness is proven.
- Do not add `SELL_TRIGGER`, positions, T+1, A-class, L3, automatic orders, or all-market scans.

## Complexity Tracking

No constitution violations are planned.
