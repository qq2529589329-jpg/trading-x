# Implementation Plan: Real Provider Evaluation

**Branch**: `004-real-provider-evaluation` | **Date**: 2026-07-04 | **Spec**: `specs/004-real-provider-evaluation/spec.md`

## Summary

Add an evaluation-only specification line for mootdx and Tencent snapshot sources. The work proves whether real intraday sources provide the fields required by the existing `IntradayDataProvider` contract, while keeping replay and fake watch as the rule baseline.

## Technical Context

**Language/Version**: Python 3.11+

**Primary Dependencies**: Standard library for schema-shaped records and local reports. Candidate provider libraries or HTTP calls remain optional and disabled unless explicitly evaluated.

**Storage**: Evaluation artifacts under provider-evaluation output paths. Existing SQLite trading tables remain read-only for this feature except tests that verify they are not modified.

**Testing**: `pytest`, existing replay fixture checks, existing fake watch parity tests, `pyright`, `ruff`.

**Input**: Candidate source name, trade date, requested symbols, and real provider snapshots when network/source access is available.

**Output**: Provider evaluation JSON/Markdown artifacts. No alerts, locks, plans, orders, or positions.

## Constitution Check

- Discipline boundary: pass. Evaluation cannot place orders or create brokerage instructions.
- Structured plans before alerts: pass. This feature does not produce alerts.
- Replay before live watch: pass. Real sources are evaluated only after replay and fake watch are green.
- Reproducible runs before tuning: pass. Evaluation records evidence before thresholds or provider choices change.
- No sell semantics without positions: pass. No sell or position semantics are introduced.

## Implementation Notes

- Reuse the existing `IntradaySnapshot` field shape for normalized samples.
- Keep source-specific adapters as thin as possible and behind the evaluation command.
- Do not add retries, caching, dashboards, or background daemons in this specification.
- Do not enable `watch` to call real providers in this specification.

## Complexity Tracking

No constitution violations are planned.
