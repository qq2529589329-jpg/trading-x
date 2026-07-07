# Feature Specification: Positions Sell Risk MVP

**Feature Branch**: `005-positions-sell-risk`
**Created**: 2026-07-07
**Status**: Draft
**Input**: Next specification line after replay, fake watch, and provider evaluation.

## User Scenarios & Testing

### User Story 1 - Load Structured Positions (Priority: P1)

As the trader, I want held positions loaded from a structured ledger, so sell-side alerts never guess cost, shares, or T+1 availability.

**Independent Test**: Import a fixed position ledger file and verify positions include trade date, stock code, total shares, available shares, average cost, and input SHA-256.

**Acceptance Scenarios**:

1. **Given** a valid position ledger exists, **When** positions are imported, **Then** the system records one current position row per trade date and stock.
2. **Given** a position ledger is missing `available_shares`, **When** import runs, **Then** the import fails before sell alerts can run.
3. **Given** a position ledger changes after import, **When** the same date is imported again, **Then** the new run records a different input SHA-256.
4. **Given** no position row exists for a stock, **When** intraday rules evaluate a stop break, **Then** the system may emit `ENTRY_CANCELLED` only and must not emit `SELL_TRIGGER`.

---

### User Story 2 - Emit Sell Alerts Only With Positions (Priority: P1)

As the trader, I want sell warnings based on recorded positions, so stop-loss semantics are not confused with pre-buy plan cancellation.

**Independent Test**: Seed a position and a B-class plan, replay a stop-break fixture, and verify the alert type is sell-side only when a position exists.

**Acceptance Scenarios**:

1. **Given** a position exists and price breaks the structural stop, **When** replay or watch evaluates the stock, **Then** it writes `SELL_WARN` or `SELL_TRIGGER` according to available-share rules.
2. **Given** a position exists but `available_shares = 0`, **When** price breaks the stop, **Then** it writes a T+1 risk warning and not an executable sell trigger.
3. **Given** a `SELL_TRIGGER` is already locked for the same date, stock, and strategy, **When** price remains below stop, **Then** no duplicate sell trigger is written.
4. **Given** no position exists, **When** price breaks the stop, **Then** sell-side alert types remain forbidden.

---

### User Story 3 - Preserve Buy-Side Replay Boundaries (Priority: P2)

As the trader, I want sell-side work isolated from Replay MVP buy-side rules, so adding positions cannot change historical buy-trigger validation.

**Independent Test**: Run the existing replay fixture suite after positions work and verify buy-side alert counts and reason codes stay stable.

**Acceptance Scenarios**:

1. **Given** positions tables exist, **When** Replay MVP fixtures run without positions, **Then** `WATCH`, `BUY_READY`, `BUY_TRIGGER`, and `ENTRY_CANCELLED` results stay unchanged.
2. **Given** positions tables exist, **When** `intraday_plans` are materialized, **Then** plan materialization still ignores positions.
3. **Given** sell-side alerts are implemented, **When** an alert is written, **Then** it includes `reason_code`, `snapshot_json`, `plan_json`, and position context.

## Edge Cases

- Sell-side alert types are forbidden unless a structured position exists.
- `available_shares = 0` blocks executable sell triggers and emits risk-only guidance.
- Position import must record `input_file`, `input_sha256`, status, start/end time, and error message.
- Position import must not parse broker screenshots, Markdown reports, or free text.
- This specification still does not approve automatic order placement.
- This specification still does not approve broker API writes.
- Existing Replay MVP behavior remains the baseline for no-position stocks.

## Requirements

- **FR-001**: System MUST provide a structured position import path before any sell-side alert can run.
- **FR-002**: Position input MUST require `trade_date`, `ts_code`, `total_shares`, `available_shares`, `avg_cost`, and `market_value`.
- **FR-003**: Position import MUST record input SHA-256 and import status for reproducibility.
- **FR-004**: System MUST NOT emit `SELL_TRIGGER` when no same-date position exists for the stock.
- **FR-005**: System MUST distinguish pre-buy `ENTRY_CANCELLED` from held-position `SELL_WARN` and `SELL_TRIGGER`.
- **FR-006**: System MUST block executable sell triggers when `available_shares <= 0`.
- **FR-007**: Sell-side alerts MUST include stable `reason_code` values for later statistics.
- **FR-008**: Sell-side alert locks MUST prevent duplicate same-day `SELL_TRIGGER` alerts.
- **FR-009**: Adding positions MUST NOT change Replay MVP buy-side fixture results.
- **FR-010**: System MUST NOT place orders or call broker write APIs in this specification.

## Success Criteria

- **SC-001**: A valid position ledger import writes positions and an import run record with SHA-256.
- **SC-002**: A missing `available_shares` field fails import before alerts run.
- **SC-003**: Stop-break replay without positions emits `ENTRY_CANCELLED` and no sell-side alert.
- **SC-004**: Stop-break replay with positions emits a sell-side alert with position context.
- **SC-005**: Stop-break replay with zero available shares emits a T+1 risk warning and no executable sell trigger.
- **SC-006**: Existing Replay MVP fixture reason codes remain stable.

## Assumptions

- The first position source is a structured CSV or JSON ledger exported by the user.
- Broker API writes remain out of scope.
- Lot-level tax and fee optimization are out of scope.
- The position ledger is the machine truth for sell-side semantics.
