# Feature Specification: Real Provider Evaluation

**Feature Branch**: `004-real-provider-evaluation`
**Created**: 2026-07-04
**Status**: Draft
**Input**: Next step after fake-provider watch parity and green CI.

## User Scenarios & Testing

### User Story 1 - Evaluate A Candidate Intraday Source Without Enabling Watch (Priority: P1)

As the trader, I want mootdx or Tencent snapshot data evaluated against the existing intraday provider contract, so I can know whether a real source is safe enough before it influences alerts.

**Independent Test**: Run a provider evaluation command for one candidate source and fixed symbols, then verify it writes only evaluation artifacts and does not write `intraday_alerts`.

**Acceptance Scenarios**:

1. **Given** a candidate source is selected, **When** evaluation runs, **Then** it records field completeness for timestamp, price, cumulative amount, cumulative volume, high, low, previous close, limit price, coverage, latency, stability, and compliance-use notes.
2. **Given** the candidate source lacks `volume_since_open`, **When** evaluation finishes, **Then** the source is marked `disabled_for_buy_trigger`.
3. **Given** the candidate source lacks trustworthy timestamp ordering, **When** evaluation finishes, **Then** the source is marked `disabled_for_live_watch`.
4. **Given** evaluation samples real provider data, **When** it writes results, **Then** it writes provider evaluation JSON/Markdown only and does not insert alerts, locks, plans, orders, or positions.

---

### User Story 2 - Preserve Replay And Fake Watch As The Rule Baseline (Priority: P1)

As the trader, I want real provider work isolated from B-class rule semantics, so sampling data cannot silently change replay or fake-watch behavior.

**Independent Test**: Run existing replay and fake-watch parity tests after adding provider evaluation code and verify alert types and reason codes are unchanged.

**Acceptance Scenarios**:

1. **Given** provider evaluation code exists, **When** replay fixtures run, **Then** alert counts and reason codes stay stable.
2. **Given** provider evaluation code exists, **When** fake watch parity tests run, **Then** they still match replay behavior.
3. **Given** a provider is marked suitable, **When** this specification finishes, **Then** `watch` still does not default to that provider.

---

### User Story 3 - Compare mootdx And Tencent With The Same Evidence Shape (Priority: P2)

As the trader, I want every candidate source scored with the same sample schema, so provider choice is based on comparable evidence instead of preference.

**Independent Test**: Validate provider sample rows against `contracts/provider-snapshot-sample-schema.json` and verify missing required fields fail validation.

**Acceptance Scenarios**:

1. **Given** mootdx and Tencent samples exist, **When** comparison runs, **Then** both sources use the same normalized sample schema.
2. **Given** a source has partial symbol coverage, **When** comparison runs, **Then** the report records covered and missing symbols.
3. **Given** source latency or stability is unmeasured, **When** comparison runs, **Then** the source remains disabled.

## Edge Cases

- Evaluation MUST NOT enable real-provider `watch`.
- Evaluation MUST NOT create or modify `intraday_plans`.
- Evaluation MUST NOT write `intraday_alerts` or `intraday_alert_locks`.
- Evaluation MUST NOT emit `BUY_TRIGGER`, `SELL_TRIGGER`, orders, position guidance, or T+1 guidance.
- Evaluation MUST NOT parse Markdown reports for execution values.
- Exporting replay CSV from provider samples is offline normalization only; it MUST NOT enable live watch.
- Missing or zero cumulative volume disqualifies a source for buy-trigger watch.
- Missing or unordered timestamps disqualify a source for live watch.
- Missing previous close or limit price keeps the source disabled for rules that depend on those fields.
- Partial symbol coverage keeps the source disabled until the missing symbols are documented and handled.
- Compliance-use status of `unknown` keeps the source disabled.

## Requirements

- **FR-001**: System MUST provide a provider evaluation flow separate from replay and watch execution.
- **FR-002**: Evaluation MUST support candidate source names `mootdx` and `tencent_snapshot` without making either a default live source.
- **FR-003**: Evaluation MUST normalize samples to the schema in `contracts/provider-snapshot-sample-schema.json`.
- **FR-004**: Evaluation MUST record timestamp, price, cumulative amount, cumulative volume, high, low, previous close, limit price, coverage, latency, stability, and compliance-use evidence.
- **FR-005**: Evaluation MUST mark a source disabled when `volume_since_open` is missing or non-positive for required snapshots.
- **FR-006**: Evaluation MUST mark a source disabled when timestamp ordering cannot be trusted.
- **FR-007**: Evaluation MUST write provider evaluation artifacts without writing alerts, locks, plans, orders, or positions.
- **FR-008**: Existing replay fixture behavior MUST remain unchanged.
- **FR-009**: Existing fake watch parity behavior MUST remain unchanged.
- **FR-010**: Real-provider watch enablement MUST be deferred to a later specification after field completeness, compliance-use status, and fake parity remain green.
- **FR-011**: System MUST provide an offline command to export validated provider samples to the Replay MVP CSV schema.

## Success Criteria

- **SC-001**: A normalized sample missing `volume_since_open` fails contract validation.
- **SC-002**: An evaluation run with missing timestamp evidence reports `disabled_for_live_watch`.
- **SC-003**: An evaluation run with missing cumulative volume reports `disabled_for_buy_trigger`.
- **SC-004**: Evaluation writes no rows to `intraday_alerts`, `intraday_alert_locks`, or `intraday_plans`.
- **SC-005**: Existing replay fixture commands still pass with stable alert counts and reason codes.
- **SC-006**: Existing fake watch parity tests still pass.
- **SC-007**: GitHub Actions remains green after the evaluation specification and implementation commits.
- **SC-008**: A validated provider sample can be exported to `trade_date,quote_time,ts_code,price,amount_since_open,volume_since_open,bar_high,bar_low` replay CSV.

## Assumptions

- Provider evaluation may use network access only when the user explicitly runs it in an environment that permits those data sources.
- Captured raw provider payloads should be hashed or minimized before persistence unless the user explicitly chooses to save full raw samples.
- This specification does not approve any real source for live trading alerts.
