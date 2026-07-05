# Tasks: Real Provider Evaluation

**Input**: `spec.md`, `plan.md`, `data-model.md`, `contracts/provider-snapshot-sample-schema.json`

**Tests**: Required before production code.

## Phase 1: Contract And Validation

- [x] T001 Add tests that valid provider sample rows satisfy `provider-snapshot-sample-schema.json`.
- [x] T002 Add tests that missing `volume_since_open` fails validation.
- [x] T003 Add tests that missing or empty `quote_time` fails validation.
- [x] T004 Implement the minimal provider sample validation helper.
- [x] T005 Run `uv run pytest tests/test_provider_evaluation_contract.py -q`.

## Phase 2: Evaluation Decision Rules

- [x] T006 Add tests for `PROVIDER_VOLUME_MISSING` producing `disabled_for_buy_trigger`.
- [x] T007 Add tests for `PROVIDER_TIMESTAMP_UNTRUSTED` producing `disabled_for_live_watch`.
- [x] T008 Add tests for partial coverage producing `PROVIDER_COVERAGE_PARTIAL`.
- [x] T009 Add tests that unknown compliance status keeps the source disabled.
- [x] T010 Implement the minimal evaluation decision function.

## Phase 3: Evaluation Artifacts

- [x] T011 Add tests that evaluation writes JSON/Markdown artifacts only.
- [x] T012 Add tests that evaluation does not write `intraday_alerts`, `intraday_alert_locks`, or `intraday_plans`.
- [x] T013 Implement the minimal evaluation report writer.
- [x] T014 Run `uv run pytest tests/test_provider_evaluation.py -q`.

## Phase 4: Optional Source Adapters Kept Disabled

- [x] T015 Add a disabled mootdx adapter boundary with tests that it is never used by `watch`.
- [x] T016 Add a disabled Tencent snapshot adapter boundary with tests that it is never used by `watch`.
- [x] T017 Document the command required to run evaluation when network/source access is available.

## Phase 5: Full Verification

- [x] T018 Run `uv run pytest`.
- [x] T019 Run `uv run pyright`.
- [x] T020 Run `uv run ruff check`.
- [x] T021 Run all replay fixture commands from CI.
- [x] T022 Confirm fake watch parity tests still pass.
- [x] T023 Confirm GitHub Actions remains green after the implementation commit.

## Phase 6: CLI Evaluation Surface

- [x] T024 Add CLI tests for `provider-evaluate` normalized sample files.
- [x] T025 Implement `provider-evaluate` to write evaluation artifacts only.
- [x] T026 Require `--sample` in the runbook so evaluation stays offline and explicit.
- [x] T027 Run provider evaluation CLI, provider decision, pyright, and ruff checks.
