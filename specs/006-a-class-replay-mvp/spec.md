# Feature Specification: A-Class Replay MVP

**Feature Branch**: `006-a-class-replay-mvp`
**Created**: 2026-07-07
**Status**: Draft
**Input**: User request to proceed with available A-class data without drifting the B-class Replay MVP.

## User Scenarios & Testing

### User Story 1 - Materialize A-Class Plans (Priority: P1)

As the trader, I want A-class candidates converted into explicit `intraday_plans`, so days with only A candidates can still be replayed without hand-writing a second plan source.

**Independent Test**: Seed an A-class structured candidate, run `plans materialize --strategy A_SPACE_LEADER`, and verify an A-class plan row is written.

**Acceptance Scenarios**:

1. **Given** an A-class candidate exists in structured candidate data, **When** A-class plans are materialized, **Then** one `intraday_plans` row is written with `strategy_type = A_SPACE_LEADER`.
2. **Given** B-class materialization runs without `--strategy`, **When** A-class rows already exist, **Then** default B behavior still ignores and preserves A rows.
3. **Given** latest `candidate_snapshots` exist for the date, **When** A-class plans are materialized, **Then** snapshots remain the source of candidate membership and daily quote/limit fields provide deterministic A execution prices.

### User Story 2 - Replay A-Class Plans Explicitly (Priority: P1)

As the trader, I want to replay A-class plans only when I explicitly ask for A-class strategy, so the locked B-class Replay MVP remains unchanged.

**Independent Test**: Insert an A-class plan, run replay with `strategy_type=A_SPACE_LEADER`, and verify `A_BUY_TRIGGERED` is written.

**Acceptance Scenarios**:

1. **Given** an A-class plan exists, **When** replay runs with `--strategy A_SPACE_LEADER`, **Then** A-class alerts are evaluated and persisted.
2. **Given** replay runs without `--strategy`, **When** only A-class plans exist, **Then** `plan_count = 0` and no A-class alerts are generated.
3. **Given** official pre-close is missing, **When** A-class replay sees an in-range price, **Then** replay may emit `WATCH / PRE_CLOSE_MISSING` but MUST NOT emit `BUY_TRIGGER`.

## Requirements

- **FR-001**: `plans materialize` MUST accept `--strategy A_SPACE_LEADER` while defaulting to `B_CAPACITY_LEADER`.
- **FR-002**: `replay` MUST accept `--strategy A_SPACE_LEADER` while defaulting to `B_CAPACITY_LEADER`.
- **FR-003**: A-class materialization MUST read structured candidate rows and daily quote/limit tables, not Markdown or free text.
- **FR-004**: A-class replay MUST write A-specific reason codes, starting with `A_BUY_TRIGGERED`.
- **FR-005**: Existing B-class default replay and materialization behavior MUST remain unchanged.
- **FR-006**: A-class replay MUST NOT introduce sell triggers, positions, T+1 sellability, realtime watch, A_STRONG execution semantics, or automatic orders.
- **FR-007**: `replay --materialize --strategy A_SPACE_LEADER` MUST materialize same-date A-class plans before replay evaluation.

## Out of Scope

- No realtime provider.
- No automatic trading.
- No positions or `SELL_TRIGGER`.
- No A_STRONG-specific L3盘口 rules.
- No manual long-term `intraday_plans` maintenance.
