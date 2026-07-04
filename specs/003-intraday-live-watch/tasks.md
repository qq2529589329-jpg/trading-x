# Tasks: Intraday Live Watch

**Input**: `spec.md`, `plan.md`, `data-model.md`, `contracts/intraday-snapshot-schema.json`

**Tests**: Required before production code.

## Phase 1: Provider Contract And Fake Snapshots

- [x] T001 Add failing tests for `IntradaySnapshot` parsing from replay-style rows.
- [x] T002 Add failing tests that snapshots missing `volume_since_open` are rejected before rule evaluation.
- [x] T003 Implement the minimal snapshot value object and provider protocol.
- [x] T004 Implement a fake provider that returns only requested symbols.
- [x] T005 Run `uv run pytest tests/test_intraday_watch_provider.py -q`.

## Phase 2: Fake Watch Parity With Replay

- [x] T006 Add failing parity tests for `20260630` fixture: `WATCH / B_VWAP_CONFIRMING` then `BUY_TRIGGER / B_BUY_TRIGGERED`.
- [x] T007 Add failing parity tests for `20260701` fixture: `BUY_READY / B_BREAKOUT_READY`.
- [x] T008 Add failing parity tests for `20260702` fixture: `ENTRY_CANCELLED_PRICE_OUT_OF_RANGE` and no `SELL_TRIGGER`.
- [x] T009 Add failing parity tests for `20260703` fixture: `PRE_CLOSE_MISSING` and no `BUY_TRIGGER`.
- [x] T010 Implement the minimal watch orchestration that reuses same-date B-class plans and alert evaluation.

## Phase 3: Read-Only CLI Boundary

- [x] T011 Add failing CLI test for fake-provider watch mode.
- [x] T012 Add failing CLI boundary test that watch does not expose order, sell, position, T+1, A-class, or L3 options.
- [x] T013 Implement the minimal read-only watch command for fake-provider execution.
- [x] T014 Run `uv run pytest tests/test_intraday_watch_cli.py -q`.

## Phase 4: Provider Source Evaluation

- [x] T015 Add a provider-evaluation checklist document for mootdx and Tencent snapshot fields.
- [x] T016 Record timestamp, price, cumulative amount, cumulative volume, high/low, previous close, limit-price, coverage, latency, stability, and compliance-use notes.
- [x] T017 Keep real providers disabled until field completeness is proven.

## Phase 5: Full Verification

- [x] T018 Run `uv run pytest`.
- [x] T019 Run `uv run pyright`.
- [x] T020 Run `uv run ruff check`.
- [x] T021 Run all four replay fixture commands from CI.
- [ ] T022 Confirm GitHub Actions remains green after the implementation commit.
