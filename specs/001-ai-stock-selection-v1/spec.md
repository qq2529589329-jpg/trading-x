# Feature Specification: AI 龙头选股系统 V1

**Feature Branch**: `001-ai-stock-selection-v1`
**Created**: 2026-06-29
**Status**: Draft
**Input**: User plan for a Tushare-backed A-share AI stock selection discipline system.

## User Scenarios & Testing

### User Story 1 - Run Data Capability Doctor (Priority: P1)

As the trader, I want to run a startup check before generating any report, so I know which Tushare interfaces are available and which signals will be downgraded.

**Why this priority**: Without capability checks, the system can silently rely on unavailable Tushare APIs and produce broken or misleading reports.

**Independent Test**: Run `python -m trading_x doctor` with missing and partially available Tushare permissions; verify the CLI output and `data_capabilities` table record available APIs, unavailable APIs, fallback modes, and report capability level.

**Acceptance Scenarios**:

1. **Given** `TUSHARE_TOKEN` is missing, **When** the user runs `python -m trading_x doctor`, **Then** the command fails with a clear token-missing message and does not print any secret value.
2. **Given** P0 APIs are available and P1/P2 APIs are partly unavailable, **When** doctor runs, **Then** it records each API result and returns a `BASIC` capability level with fallback explanations.
3. **Given** any P0 API is unavailable, **When** doctor runs, **Then** it records a `DEGRADED` capability level and states that candidates cannot be generated.

---

### User Story 2 - Generate Daily JSON And Markdown Report (Priority: P1)

As the trader, I want a daily post-market report, so I can see market state, whether new positions are allowed, and a structured candidate plan without parsing logs or raw data.

**Why this priority**: The report is the first usable product surface and the anchor for later review, dashboards, and statistics.

**Independent Test**: Run `python -m trading_x report --date YYYYMMDD` using fixture data and verify that JSON and Markdown are generated, SQLite stores the same JSON snapshot, and weak market days can output zero candidates without failure.

**Acceptance Scenarios**:

1. **Given** P0 data is available and market status is tradable, **When** the report is generated, **Then** the system writes `reports/YYYYMMDD_report.json` and `reports/YYYYMMDD_report.md`.
2. **Given** P0 data is unavailable, **When** the report is generated, **Then** the report is `DEGRADED`, contains no candidates, and states the missing P0 dependency.
3. **Given** 10 consecutive weak market trading days, **When** reports are generated, **Then** each report says "今日无符合纪律候选" and "禁止新开仓" without hard-filling candidates.

---

### User Story 3 - Select A/B Candidates With Confidence Labels (Priority: P2)

As the trader, I want the system to select only A-class space leaders and B-class capacity leaders, so the first version stays focused on the core 龙头战法 instead of becoming a broad stock screener.

**Why this priority**: Candidate quality and explicit confidence are more important than broad coverage in V1.

**Independent Test**: Run candidate selection against fixture data that includes strong limit event data, weak limit event data, missing theme data, and low-liquidity stocks; verify filtering, `A_STRONG/A_LITE`, `theme_confidence`, `event_confidence`, and maximum candidate count.

**Acceptance Scenarios**:

1. **Given** high-quality limit event data exists, **When** an A-class candidate passes filters, **Then** it may be labeled `A_STRONG`.
2. **Given** only `close == up_limit` approximation exists, **When** an A-class candidate passes filters, **Then** it MUST be labeled `A_LITE` with `event_confidence = LOW`.
3. **Given** `limit_cpt_list` is unavailable, **When** theme strength is calculated, **Then** `theme_confidence` is downgraded and the report explains why.
4. **Given** more than five candidates pass filters, **When** the report is generated, **Then** at most five candidates appear using rule-layered ordering.

---

### User Story 4 - Preserve Future Review Data (Priority: P3)

As the trader, I want the system to store report snapshots and prepare trade log storage, so V1 can evolve into V1+ performance review without reworking the data model.

**Why this priority**: V1 does not enable trade-log workflows, but the schema should avoid a later migration detour.

**Independent Test**: Initialize the database and verify `reports.report_snapshot_json` is identical to the JSON report file, and `trade_logs` exists but is not used by the V1 report command.

**Acceptance Scenarios**:

1. **Given** a report was generated, **When** the JSON file is loaded and compared with SQLite `reports.report_snapshot_json`, **Then** the content is identical.
2. **Given** V1 is installed, **When** the database schema is inspected, **Then** `trade_logs` exists but no V1 command requires trade-log input.

## Edge Cases

- Missing `TUSHARE_TOKEN` must not leak token values in errors or logs.
- Tushare API permissions may differ from documented point tiers; runtime doctor results are the source of truth.
- `stk_limit` only provides limit prices; it must not be treated as limit event quality.
- Missing P1 data must lower confidence rather than block reports.
- Missing P2 data must be displayed as unavailable but must not block report generation.
- Zero-candidate days are valid output and must not become errors.
- A/B candidate ranking must never include stocks that failed risk filters.

## Requirements

### Functional Requirements

- **FR-001**: System MUST provide `python -m trading_x doctor`.
- **FR-002**: Doctor MUST check `TUSHARE_TOKEN`, `daily`, `daily_basic`, `stk_limit`, `top_list`, `moneyflow`, `margin`, and `limit_cpt_list`.
- **FR-003**: Doctor MUST persist results to `data_capabilities`.
- **FR-004**: System MUST classify report capability as `FULL`, `BASIC`, or `DEGRADED`.
- **FR-005**: System MUST use P0/P1/P2 data dependency tiers; only missing P0 blocks candidate generation.
- **FR-006**: System MUST split limit price storage into `stk_limit_prices` and event storage into `limit_events`.
- **FR-007**: System MUST include `theme_confidence` in theme strength and report output.
- **FR-008**: System MUST label A-class candidates as `A_STRONG` or `A_LITE`.
- **FR-009**: System MUST generate JSON and Markdown reports; HTML MAY be generated later.
- **FR-010**: System MUST store report JSON snapshots in SQLite.
- **FR-011**: System MUST create `trade_logs` in V1 but MUST NOT require trade logs for V1 reports.
- **FR-012**: System MUST limit V1 strategies to `A_SPACE_LEADER` and `B_CAPACITY_LEADER`.
- **FR-013**: System MUST sort candidates by risk pass, strategy bucket, market status, theme strength, leader status, liquidity, then limit/breakout strength.
- **FR-014**: System MUST output at most five candidates and MAY output zero candidates.
- **FR-015**: Every candidate MUST include strategy type, candidate grade, buy observation conditions, abandon conditions, maximum chase limit, structural stop, suggested position, max loss, data confidence, `theme_confidence`, and `event_confidence`.
- **FR-016**: System MUST include tests for permission degradation and continuous no-candidate scenarios.

### Key Entities

- **DataCapability**: Runtime availability record for each required or optional data API.
- **StockUniverse**: Tradable stock set limited to Shanghai/Shenzhen main board and ChiNext after risk exclusions.
- **StkLimitPrice**: Daily limit-up and limit-down price reference from `stk_limit`.
- **LimitEvent**: Limit-up or limit-down event quality record with confidence and data source.
- **ThemeStrength**: Theme or concept strength with confidence and explanation.
- **Candidate**: A/B strategy candidate with risk state, confidence, and next-day plan.
- **Report**: JSON and Markdown daily output plus persisted JSON snapshot.
- **TradeLog**: Future V1+ trade record schema, not used by V1 workflows.

## Success Criteria

### Measurable Outcomes

- **SC-001**: Across 10 consecutive trading-day fixtures, `update` successfully refreshes P0 data for every day where P0 APIs are available.
- **SC-002**: Across the same 10 trading-day fixtures, `report` generates both JSON and Markdown reports for every day.
- **SC-003**: Re-running `update` and `report` for the same trading date does not create duplicate dirty SQLite rows.
- **SC-004**: No CLI output, logs, database rows, JSON reports, or Markdown reports expose `TUSHARE_TOKEN` or token-like secret values.
- **SC-005**: When P0 data is missing, the system generates a `DEGRADED` report and does not generate fake candidates.
- **SC-006**: Every daily report includes market status.
- **SC-007**: Every daily report includes a clear decision: allow new positions, observe only, or prohibit new positions.
- **SC-008**: Candidate count is always between 0 and 5.
- **SC-009**: Every candidate includes entry rationale, veto/risk items, and next-day plan.
- **SC-010**: When there are no candidates, the report explicitly states the no-buy reason.
- **SC-011**: Repeated runs for the same trading day produce stable report content after JSON normalization.
- **SC-012**: Missing P1 or P2 interfaces trigger downgrade/fallback behavior and do not crash report generation.

## Assumptions

- The user will provide `TUSHARE_TOKEN` through the local environment or `.env`, never in chat or report output.
- V1 uses Tushare as the primary market data source; free interfaces may be added later only as explicit fallbacks.
- V1 does not include real-time auction, VWAP, brokerage integration, or external LLM summary.
- The first implementation target is a local Python CLI with SQLite storage.
- This system is a discipline and research tool, not investment advice.
