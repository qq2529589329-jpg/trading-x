# Implementation Plan: AI 龙头选股系统 V1

**Branch**: `001-ai-stock-selection-v1` | **Date**: 2026-06-29 | **Spec**: `specs/001-ai-stock-selection-v1/spec.md`

**Input**: Feature specification from `specs/001-ai-stock-selection-v1/spec.md`

## Summary

Build a local Python CLI that generates post-market A-share discipline reports. The system uses Tushare as the primary data source, runs a capability doctor before report generation, stores normalized data in SQLite, and outputs JSON + Markdown reports with explicit confidence and downgrade reasons.

## Technical Context

**Language/Version**: Python 3.14 local runtime, code compatible with Python 3.11+

**Primary Dependencies**: `tushare`, `python-dotenv`, standard-library `sqlite3`, `argparse`, `json`, `dataclasses`

**Storage**: SQLite file at `data/trading_x.db`

**Testing**: `pytest`; Tushare calls are tested through a fake adapter, not live network calls

**Target Platform**: Local Windows workstation first; no server deployment in V1

**Project Type**: Single-project local CLI

**Performance Goals**: Generate one daily report for the main board + ChiNext universe within one normal post-market run; no real-time guarantees

**Constraints**: No brokerage integration, no automatic order placement, no external LLM call, no hard dependency on P1/P2 interfaces

**Scale/Scope**: V1 scans Shanghai/Shenzhen main board + ChiNext, outputs 0-5 candidates, and keeps historical report snapshots

## Constitution Check

- Discipline boundary: pass. No automatic order placement or brokerage integration.
- Data capability first: pass. `doctor` and `data_capabilities` are foundational tasks.
- Confidence in output: pass. `theme_confidence`, `event_confidence`, `A_STRONG/A_LITE`, and `data_capability` are required report fields.
- JSON as machine truth: pass. JSON report is mandatory and persisted in SQLite.
- Simple rules before scores: pass. Candidate ordering uses rule layers before optional score fields.
- Failure path tests: pass. Permission degradation and continuous no-candidate tests are explicit tasks.

## Project Structure

### Documentation

```text
specs/001-ai-stock-selection-v1/
├── contracts/
│   └── report-schema.json
├── data-model.md
├── plan.md
├── quickstart.md
├── research.md
├── spec.md
└── tasks.md
```

### Source Code

```text
pyproject.toml
src/trading_x/
├── __init__.py
├── __main__.py
├── capabilities.py
├── candidates.py
├── cli.py
├── config.py
├── db.py
├── market.py
├── reports.py
├── schema.sql
├── tushare_adapter.py
└── types.py

tests/
├── conftest.py
├── test_candidates.py
├── test_doctor.py
├── test_no_candidates.py
├── test_reports.py
└── test_schema.py
```

**Structure Decision**: Use a single Python package because V1 is a local CLI. Keep modules split by responsibility so each file stays small and directly testable.

## Phase 0 Research

See `research.md`.

## Phase 1 Design

See `data-model.md`, `contracts/report-schema.json`, and `quickstart.md`.

## Implementation Notes

- `TushareAdapter` is the only boundary that knows live Tushare method names.
- Tests use a fake adapter that returns fixed tables or raises permission errors.
- `doctor` writes one row per checked API into `data_capabilities`.
- Capability levels:
  - `FULL`: all P0 APIs and key P1 APIs are available.
  - `BASIC`: all P0 APIs are available, but one or more P1 APIs are unavailable.
  - `DEGRADED`: any P0 API is unavailable; candidate generation is blocked.
- `stk_limit_prices` stores only prices from `stk_limit`.
- `limit_events` stores event quality and MUST use `LOW` confidence when derived only from close price equality.
- `reports.report_snapshot_json` must be byte-equivalent after JSON normalization to the report JSON file.

## V1 Acceptance Gate

Final acceptance uses a 10-consecutive-trading-day fixture or dry-run window:

1. `update` refreshes P0 data for every day where P0 APIs are available.
2. `report` generates JSON and Markdown for every day.
3. SQLite remains idempotent: re-running the same date does not create duplicate dirty rows.
4. No token or token-like secret appears in CLI output, logs, SQLite, JSON, or Markdown.
5. P0 data gaps produce `DEGRADED` reports with no fake candidates.
6. Every report has market status.
7. Every report has allow / observe / prohibit decision.
8. Candidate count is always 0-5.
9. Every candidate has entry rationale, veto items, and next-day plan.
10. Zero-candidate reports explicitly state the no-buy reason.
11. Re-running the same date produces stable normalized JSON.
12. Missing P1/P2 interfaces degrade gracefully and do not crash.

## Complexity Tracking

No constitution violations are planned for V1.
