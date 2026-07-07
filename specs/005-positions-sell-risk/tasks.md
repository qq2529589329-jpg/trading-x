# Tasks: Positions Sell Risk MVP

**Input**: `spec.md`, `plan.md`, `data-model.md`, `contracts/position-ledger-schema.json`

**Tests**: Required before production code.

## Phase 1: Position Ledger Contract

- [x] T001 Add contract coverage that a valid position ledger satisfies `position-ledger-schema.json`.
- [x] T002 Add contract coverage that missing `available_shares` fails validation.
- [x] T003 Add contract coverage that negative shares or cost fields fail validation.
- [x] T004 Implement the minimal position ledger parser.
- [x] T005 Run `uv run pytest tests/test_positions_contract.py -q`.

## Phase 2: Position Import Persistence

- [x] T006 Add schema coverage for `positions` and `position_import_runs`.
- [x] T007 Add import coverage that records `input_file`, `input_sha256`, counts, status, and timing.
- [x] T008 Implement the minimal SQLite schema and import run writer.
- [x] T009 Add CLI coverage for `positions import --date YYYYMMDD --input PATH`.
- [x] T010 Run `uv run pytest tests/test_positions_contract.py tests/test_positions_import.py -q`.

## Phase 3: Sell-Side Alert Semantics

- [x] T011 Add replay coverage that no-position stop breaks still emit `ENTRY_CANCELLED`, not sell-side alerts.
- [x] T012 Add replay coverage that a held position stop break emits a sell-side alert.
- [x] T013 Add replay coverage that `available_shares = 0` emits risk-only T+1 warning, not executable sell trigger.
- [x] T014 Implement the minimal position-aware stop evaluation.
- [x] T015 Run `uv run pytest tests/test_intraday_replay.py tests/test_positions_sell_alerts.py -q`.

## Phase 4: Locking And Regression

- [x] T016 Add coverage that same-day `SELL_TRIGGER` locks after the first terminal alert.
- [x] T017 Add coverage that buy-side Replay MVP fixture reason codes remain stable.
- [x] T018 Implement the minimal sell-side lock path through `intraday_alert_locks`.
- [x] T019 Run `uv run pytest`.
- [x] T020 Run `uv run pyright`.
- [x] T021 Run `uv run ruff check`.

## Phase 5: Documentation And Verification

- [x] T022 Update `analyze.md` with the completed consistency check.
- [x] T023 Run the Replay MVP fixture commands.
- [x] T024 Run one position import fixture and one stop-break sell fixture.
- [x] T025 Commit the positions sell-risk MVP implementation.
