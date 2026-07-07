# Implementation Plan: Positions Sell Risk MVP

**Branch**: `005-positions-sell-risk` | **Date**: 2026-07-07 | **Spec**: `specs/005-positions-sell-risk/spec.md`

## Summary

Add sell-side semantics only after structured positions exist. The implementation will keep Replay MVP buy-side behavior unchanged, then layer position import, position-aware risk evaluation, and sell-side alert locking on top of the existing SQLite and alert surfaces.

## Technical Context

**Language/Version**: Python 3.11+

**Primary Dependencies**: standard library only.

**Storage**: SQLite at `data/trading_x.db`.

**Testing**: `pytest`, `pyright`, `ruff`.

**Input**: Position ledger CSV or JSON with `trade_date`, `ts_code`, `total_shares`, `available_shares`, `avg_cost`, and `market_value`.

**Output**: Position rows, position import run rows, and sell-side alerts through the existing alert table.

## Constitution Check

- Structured data before alerts: pass. Positions are imported from a structured ledger.
- No sell semantics without positions: pass. `SELL_TRIGGER` remains forbidden unless a same-date position exists.
- Reproducible runs before tuning: pass. Position imports record input SHA-256.
- No automatic trading: pass. The specification does not place orders or write to broker APIs.

## Implementation Notes

- Add position import tables and migration paths.
- Add a position ledger contract before parser code.
- Keep buy-side replay fixtures as regression coverage.
- Reuse `intraday_alerts` and `intraday_alert_locks` for sell-side alerts instead of creating a parallel alert system.
- Keep position import separate from `intraday_plans`; plans remain the buy-side machine truth.
- Treat `available_shares <= 0` as a risk warning, not an executable sell trigger.

## Complexity Tracking

No constitution violations are planned.
