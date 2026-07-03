# Research: AI 龙头选股系统 V1

## Decision: Use Python CLI For V1

**Decision**: Build V1 as a local Python CLI invoked by `python -m trading_x ...`.

**Rationale**: Tushare is Python-native, SQLite is available through the standard library, and report generation is a batch workflow rather than a web workflow. A CLI keeps V1 focused on data correctness and report discipline.

**Alternatives considered**:

- Local web dashboard: deferred to V2 because it adds UI surface before the data contract is stable.
- Node/TypeScript: rejected for V1 because Tushare and data processing are more direct in Python.

## Decision: SQLite Is System Memory

**Decision**: Store capabilities, market data, derived signals, candidates, reports, and the inactive V1 `trade_logs` table in SQLite.

**Rationale**: SQLite is a single local file, supports reliable snapshots, and is enough for daily batch reports. It also supports the later V1+ performance review without requiring a database server.

**Alternatives considered**:

- CSV-only: rejected because report snapshots, capability history, and candidate relationships become brittle.
- PostgreSQL: rejected as unnecessary infrastructure for a single-user local V1.

## Decision: Doctor-First Data Access

**Decision**: Data access starts with `python -m trading_x doctor`, and reports use the last capability state.

**Rationale**: Tushare permissions vary by points and independent interface rights. Runtime capability is more reliable than assumptions from documentation.

**Alternatives considered**:

- Fail during report generation: rejected because partial reports should degrade predictably.
- Assume 2000-point access: rejected because some interfaces are independently permissioned.

## Decision: P0/P1/P2 Dependency Tiers

**Decision**: Classify dependencies by impact:

- P0 blocks candidate generation when missing.
- P1 lowers confidence when missing.
- P2 only removes explanatory enrichment.

**Rationale**: The first version should generate useful reports when non-core APIs are unavailable while refusing to fabricate core signals.

## Decision: Limit Price And Limit Event Are Separate

**Decision**: Store `stk_limit` output in `stk_limit_prices`; store event-level interpretation in `limit_events`.

**Rationale**: `stk_limit` gives price boundaries, not first seal time, break count, or seal quality. Combining them would create false precision.

## Decision: Rule-Layered Candidate Ordering

**Decision**: Sort candidates by risk pass, strategy bucket, market status, theme strength, leader status, liquidity, then limit/breakout strength.

**Rationale**: V1 should avoid an overfit composite score. Scores can explain, but rules decide.

## Deferred Decisions

- Real-time auction and VWAP signals are deferred until data availability is proven.
- External LLM summaries are deferred to V2 and may only explain outputs.
- Trade log import is deferred to V1+ even though `trade_logs` exists in V1.
- HTML reports are optional and may be skipped if JSON + Markdown are complete.
