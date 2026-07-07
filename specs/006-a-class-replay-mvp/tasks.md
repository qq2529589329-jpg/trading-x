# Tasks: A-Class Replay MVP

**Input**: `spec.md`, `plan.md`, `data-model.md`

**Tests**: Required before production code.

## Phase 1: Explicit Strategy Path

- [x] T001 Add failing tests for A-class materialization, explicit A-class replay, and CLI `--strategy`.
- [x] T002 Add strategy-scoped plan materialization with default B behavior unchanged.
- [x] T003 Add strategy-scoped replay cleanup, plan counting, and plan loading.
- [x] T004 Add A-class alert reason `A_BUY_TRIGGERED`.
- [x] T005 Add CLI `--strategy` for `plans materialize` and `replay`.
- [x] T006 Run full verification: targeted pytest, full pytest, pyright, ruff.
- [x] T007 Smoke test `20260706` A-class materialize/replay after generating a suitable replay CSV.
