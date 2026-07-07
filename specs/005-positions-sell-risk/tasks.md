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

- [ ] T006 Add schema coverage for `positions` and `position_import_runs`.
- [ ] T007 Add import coverage that records `input_file`, `input_sha256`, counts, status, and timing.
- [ ] T008 Implement the minimal SQLite schema and import run writer.
- [ ] T009 Add CLI coverage for `positions import --date YYYYMMDD --input PATH`.
- [ ] T010 Run `uv run pytest tests/test_positions_import.py tests/test_cli.py -q`.

## Phase 3: Sell-Side Alert Semantics

- [ ] T011 Add replay coverage that no-position stop breaks still emit `ENTRY_CANCELLED`, not sell-side alerts.
- [ ] T012 Add replay coverage that a held position stop break emits a sell-side alert.
- [ ] T013 Add replay coverage that `available_shares = 0` emits risk-only T+1 warning, not executable sell trigger.
- [ ] T014 Implement the minimal position-aware stop evaluation.
- [ ] T015 Run `uv run pytest tests/test_intraday_replay.py tests/test_positions_sell_alerts.py -q`.

## Phase 4: Locking And Regression

- [ ] T016 Add coverage that same-day `SELL_TRIGGER` locks after the first terminal alert.
- [ ] T017 Add coverage that buy-side Replay MVP fixture reason codes remain stable.
- [ ] T018 Implement the minimal sell-side lock path through `intraday_alert_locks`.
- [ ] T019 Run `uv run pytest`.
- [ ] T020 Run `uv run pyright`.
- [ ] T021 Run `uv run ruff check`.

## Phase 5: Documentation And Verification

- [ ] T022 Update `analyze.md` with the completed consistency check.
- [ ] T023 Run the Replay MVP fixture commands.
- [ ] T024 Run one position import fixture and one stop-break sell fixture.
- [ ] T025 Commit the positions sell-risk MVP implementation.
