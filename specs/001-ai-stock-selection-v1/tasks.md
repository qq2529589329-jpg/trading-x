# Tasks: AI 龙头选股系统 V1

**Input**: Design documents from `specs/001-ai-stock-selection-v1/`

**Prerequisites**: `plan.md`, `spec.md`, `research.md`, `data-model.md`, `contracts/report-schema.json`

**Tests**: Tests are required. Write failing tests before implementation.

## Format: `[ID] [P?] [Story] Description`

- **[P]**: Can run in parallel.
- **[Story]**: User story label from `spec.md`.

## Phase 1: Setup

**Purpose**: Create the Python CLI project skeleton.

- [x] T001 Create `pyproject.toml` with package metadata, pytest configuration, and dependencies.
- [x] T002 Create package skeleton under `src/trading_x/`.
- [x] T003 [P] Create test skeleton under `tests/`.
- [x] T004 Create `src/trading_x/__main__.py` that delegates to CLI entrypoint.

---

## Phase 2: Foundational Schema And Types

**Purpose**: Database schema and shared domain types required by all stories.

- [x] T005 [P] Write failing schema test in `tests/test_schema.py` asserting required tables exist.
- [x] T006 Implement `src/trading_x/schema.sql` with `data_capabilities`, `stock_universe`, `daily_quotes`, `daily_basic`, `stk_limit_prices`, `limit_events`, `theme_strength`, `candidates`, `reports`, and `trade_logs`.
- [x] T007 Implement `src/trading_x/db.py` to initialize SQLite from `schema.sql`.
- [x] T008 Write failing enum/type tests for capability, confidence, strategy type, and candidate grade in `tests/test_types.py`.
- [x] T009 Implement `src/trading_x/types.py` with typed constants or enums.
- [x] T010 Add `python -m trading_x init-db` CLI command.

**Checkpoint**: Database can initialize locally and contains V1 tables, including inactive `trade_logs`.

---

## Phase 3: User Story 1 - Run Data Capability Doctor (Priority: P1)

**Goal**: Detect Tushare permissions and write `data_capabilities`.

**Independent Test**: Run doctor against fake adapter fixtures and inspect CLI result plus SQLite rows.

### Tests

- [x] T011 [P] [US1] Write failing test for missing `TUSHARE_TOKEN` in `tests/test_doctor.py`.
- [x] T012 [P] [US1] Write failing test for partial API availability writing `data_capabilities`.
- [x] T013 [P] [US1] Write failing test that missing P0 returns `DEGRADED`.

### Implementation

- [x] T014 [US1] Implement `src/trading_x/config.py` to load environment without printing secrets.
- [x] T015 [US1] Implement `src/trading_x/tushare_adapter.py` with a narrow adapter interface for checked APIs.
- [x] T016 [US1] Implement `src/trading_x/capabilities.py` with P0/P1/P2 tier definitions and capability calculation.
- [x] T017 [US1] Add `python -m trading_x doctor` CLI command.

**Checkpoint**: Doctor works independently and never leaks the token.

---

## Phase 4: User Story 2 - Generate Daily JSON And Markdown Report (Priority: P1)

**Goal**: Generate daily report files and persist a matching JSON snapshot.

**Independent Test**: Generate a report from fixtures and verify JSON, Markdown, and SQLite snapshot.

### Tests

- [x] T018 [P] [US2] Write failing test that report generates JSON and Markdown files.
- [x] T019 [P] [US2] Write failing test that `reports.report_snapshot_json` matches the JSON file.
- [x] T020 [P] [US2] Write failing test that P0 missing produces a `DEGRADED` zero-candidate report.

### Implementation

- [x] T021 [US2] Implement `src/trading_x/reports.py` for report snapshot assembly and file writing.
- [x] T022 [US2] Implement Markdown rendering from the JSON snapshot.
- [x] T023 [US2] Add `python -m trading_x report --date YYYYMMDD` CLI command.
- [x] T024 [US2] Validate generated JSON against `contracts/report-schema.json` in tests.

**Checkpoint**: Reports are useful even when no candidates are generated.

---

## Phase 5: User Story 3 - Select A/B Candidates With Confidence Labels (Priority: P2)

**Goal**: Generate focused A/B candidates with explicit confidence labels.

**Independent Test**: Run candidate logic against fixtures covering A_STRONG, A_LITE, B candidates, low confidence theme data, and risk failures.

### Tests

- [x] T025 [P] [US3] Write failing test that high-quality limit events can produce `A_STRONG`.
- [x] T026 [P] [US3] Write failing test that close-at-limit approximation only produces `A_LITE`.
- [x] T027 [P] [US3] Write failing test that missing `limit_cpt_list` downgrades `theme_confidence`.
- [x] T028 [P] [US3] Write failing test that risk-failed stocks never appear in candidates.
- [x] T029 [P] [US3] Write failing test that candidate output is capped at five.

### Implementation

- [x] T030 [US3] Implement `src/trading_x/market.py` for market status and theme strength derivation.
- [x] T031 [US3] Implement `src/trading_x/candidates.py` with A/B rule-layered candidate generation.
- [x] T032 [US3] Store selected candidates in `candidates`.
- [x] T033 [US3] Add candidate details to report JSON and Markdown.

**Checkpoint**: Candidate logic can be tested without live Tushare.

---

## Phase 6: User Story 4 - Preserve Future Review Data (Priority: P3)

**Goal**: Keep report snapshots and prepare V1+ trade log storage without enabling trade-log workflows.

**Independent Test**: Verify `trade_logs` exists and report commands do not require it.

### Tests

- [x] T034 [P] [US4] Write failing test that `trade_logs` exists after init.
- [x] T035 [P] [US4] Write failing test that report generation succeeds with empty `trade_logs`.

### Implementation

- [x] T036 [US4] Confirm `schema.sql` includes `trade_logs` and no V1 command reads it.
- [x] T037 [US4] Document V1+ trade-log import as deferred in `README.md`.

---

## Phase 7: Required Failure Scenarios

**Purpose**: Lock the behavior most likely to regress.

- [x] T038 Write failing test for partial permissions: `daily` available, `daily_basic`, `top_list`, `moneyflow`, and `limit_cpt_list` unavailable.
- [x] T039 Implement fallback modes so the partial-permission test passes.
- [x] T040 Write failing test for 10 consecutive no-candidate weak-market trading-day reports.
- [x] T041 Implement stable zero-candidate report behavior.

---

## Phase 8: Polish And Verification

**Purpose**: Final consistency check before implementation is considered ready.

- [x] T042 Run `pytest`.
- [x] T043 Run `python -m trading_x doctor` with no token and verify no token leak.
- [x] T044 Run `python -m trading_x init-db` against a temporary database.
- [x] T045 Run fixture-backed report generation for a weak-market date.
- [x] T046 Review generated JSON and Markdown for required fields.
- [x] T047 Confirm no implementation introduces automatic order placement or brokerage integration.
- [x] T048 Run a 10-consecutive-trading-day acceptance fixture and verify update/report success, SQLite idempotency, no token leakage, no fake P0-missing candidates, market status, allow/observe/prohibit decisions, 0-5 candidates, candidate rationale/veto/next-day plan fields, explicit no-buy reason on zero-candidate days, stable same-day reruns, and P1/P2 graceful degradation.

## Dependencies & Execution Order

- Phase 1 blocks all other work.
- Phase 2 blocks all user stories.
- US1 and US2 are MVP and should be implemented before US3.
- US3 can proceed after US1/US2 foundations are in place.
- US4 can run after schema work is complete.
- Phase 7 and Phase 8 are final gates.

## Parallel Opportunities

- T003 can run with T001/T002.
- T005 and T008 can be written in parallel.
- US1 tests T011-T013 can be written in parallel.
- US2 tests T018-T020 can be written in parallel.
- US3 tests T025-T029 can be written in parallel.

## MVP Cut

The smallest useful implementation is:

1. T001-T017 for doctor and schema.
2. T018-T024 for degraded/basic report generation.
3. T038-T041 for permission downgrade and no-candidate behavior.

Candidate richness can improve after this MVP without changing the core direction.
