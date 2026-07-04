# Feature Specification: Intraday Live Watch

**Feature Branch**: `003-intraday-live-watch`
**Created**: 2026-07-03
**Status**: Draft
**Input**: User-approved next step after Replay MVP fixtures and CI.

## User Scenarios & Testing

### User Story 1 - Define A Read-Only Intraday Provider Contract (Priority: P1)

As the trader, I want live watch data behind one provider contract, so rule logic can be tested with fake snapshots before any real market source is connected.

**Independent Test**: Run a fake provider built from fixed snapshot rows and verify it returns only requested B-class symbols with price, amount, volume, high, low, and quote time.

**Acceptance Scenarios**:

1. **Given** same-date B-class `intraday_plans` exist, **When** watch starts, **Then** it requests snapshots only for those plan symbols.
2. **Given** a provider snapshot lacks `volume_since_open`, **When** watch parses it, **Then** the snapshot is rejected before B-class rules run.
3. **Given** a fake provider emits the same rows as a replay CSV fixture, **When** watch evaluates them, **Then** inserted alerts match replay alert types and reason codes.
4. **Given** a provider returns a symbol that is not in `intraday_plans`, **When** watch runs, **Then** that symbol is ignored and cannot create a new plan.

---

### User Story 2 - Run Read-Only Watch Against Existing Intraday Plans (Priority: P1)

As the trader, I want a watch command that evaluates existing machine plans without creating orders, so I can observe live discipline alerts safely.

**Independent Test**: Start watch with a fake provider and one B-class plan, then verify `WATCH / BUY_READY / BUY_TRIGGER / ENTRY_CANCELLED` behavior matches the Replay MVP rule flow.

**Acceptance Scenarios**:

1. **Given** a valid B-class plan and above-VWAP, volume-passing snapshots, **When** watch runs, **Then** it may write `WATCH`, `BUY_READY`, or `BUY_TRIGGER` to `intraday_alerts`.
2. **Given** price breaks `stop_price` before any position model exists, **When** watch runs, **Then** it writes `ENTRY_CANCELLED`, not `SELL_TRIGGER`.
3. **Given** `BUY_TRIGGER` already locked for the same trade date, stock, and strategy, **When** watch receives another breakout snapshot, **Then** it does not write a second `BUY_TRIGGER`.
4. **Given** no same-date B-class `intraday_plans` exist, **When** watch starts, **Then** it exits without requesting provider data and reports no plans.

---

### User Story 3 - Evaluate Real Data Sources Without Coupling Rules (Priority: P2)

As the trader, I want mootdx and Tencent snapshot sources evaluated behind the provider contract, so source choice does not change B-class discipline rules.

**Independent Test**: Run source evaluation checks that document whether a candidate provider can supply timestamp, current price, cumulative amount, cumulative volume, high, low, previous close, and limit prices for all requested symbols.

**Acceptance Scenarios**:

1. **Given** a candidate real provider lacks cumulative volume, **When** source evaluation runs, **Then** the provider is marked unsuitable for BUY-trigger watch.
2. **Given** a candidate real provider has no trustworthy timestamp, **When** source evaluation runs, **Then** the provider is marked unsuitable for live watch.
3. **Given** a provider source is evaluated, **When** documentation is generated, **Then** it records stability, latency, field completeness, and compliance-use notes.

## Edge Cases

- Watch MUST read `intraday_plans`; it MUST NOT parse Markdown or free text for execution values.
- Watch MUST NOT add symbols during the session.
- Watch MUST NOT place orders or emit brokerage instructions.
- Watch MUST NOT emit `SELL_TRIGGER`, T+1 sell guidance, available-share guidance, or position sizing based on held shares.
- Watch MUST NOT implement A-class, L3 order-book, or all-market scanning behavior in this specification line.
- Fake provider snapshots must use the same amount/volume VWAP semantics as replay.
- Missing or zero cumulative volume keeps VWAP unavailable and cannot produce `BUY_TRIGGER`.
- Missing official pre-close allows observation alerts but blocks `BUY_TRIGGER`, matching replay semantics.
- Alert locks remain shared with replay for same-date B-class alerts.
- Real providers are candidates until they prove field completeness; evaluation does not make them default sources.

## Requirements

- **FR-001**: System MUST define an `IntradayDataProvider` contract that returns typed intraday snapshots for requested symbols.
- **FR-002**: Watch MUST load same-date `B_CAPACITY_LEADER` rows from `intraday_plans` and MUST NOT create plans.
- **FR-003**: Watch MUST reuse Replay MVP B-class rule semantics for `WATCH`, `BUY_READY`, `BUY_TRIGGER`, and `ENTRY_CANCELLED`.
- **FR-004**: Watch MUST NOT emit `SELL_TRIGGER` or any position/T+1 sell semantics.
- **FR-005**: Watch MUST NOT expose automatic order placement.
- **FR-006**: Fake provider tests MUST prove watch output matches replay output for the same fixed fixture rows.
- **FR-007**: Provider snapshots MUST include `trade_date`, `quote_time`, `ts_code`, `price`, `amount_since_open`, `volume_since_open`, `bar_high`, and `bar_low`.
- **FR-008**: Watch MUST reject provider snapshots missing cumulative volume before VWAP or buy-trigger evaluation.
- **FR-009**: Watch MUST ignore provider symbols not present in same-date `intraday_plans`.
- **FR-010**: Source evaluation MUST document field completeness for mootdx, Tencent snapshot, or any later provider before live use.
- **FR-011**: CLI watch entrypoint, when implemented, MUST be read-only and MUST support fake-provider execution before real-provider execution.
- **FR-012**: Watch MUST write alerts through the existing `intraday_alerts` and `intraday_alert_locks` surfaces.

## Success Criteria

- **SC-001**: A fake provider built from `20260630` fixture rows produces the same `WATCH / B_VWAP_CONFIRMING` and `BUY_TRIGGER / B_BUY_TRIGGERED` alerts as replay.
- **SC-002**: A fake provider built from `20260701` fixture rows produces the same `BUY_READY / B_BREAKOUT_READY` result as replay.
- **SC-003**: A fake provider built from `20260702` fixture rows produces `ENTRY_CANCELLED_PRICE_OUT_OF_RANGE` and no `SELL_TRIGGER`.
- **SC-004**: A fake provider built from `20260703` fixture rows produces `PRE_CLOSE_MISSING` observation and no `BUY_TRIGGER`.
- **SC-005**: A provider snapshot without `volume_since_open` is rejected before rule evaluation.
- **SC-006**: A no-plan watch run exits without provider calls.
- **SC-007**: CI continues to pass replay fixtures while live watch tests are added.

## Assumptions

- The first implementation uses a fake provider only.
- Real provider work is evaluation-first; mootdx and Tencent are not committed default sources in this specification.
- Replay remains the baseline for correctness.
- Existing SQLite tables are sufficient for initial watch alerts; new watch-run persistence can be proposed only after fake-provider behavior is proven.
