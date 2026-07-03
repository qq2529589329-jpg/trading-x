# Trading X Constitution

## Core Principles

### I. Discipline Before Recommendation
The system is a trading discipline and research assistant, not a stock tip generator. It MUST NOT auto-place orders, auto-generate brokerage instructions, or present any output as investment advice. Every report MUST preserve the boundary: AI generates candidates, risks, and plans; the user confirms manually.

### II. Data Capability Before Signal
No strategy signal may assume a data interface is available. The system MUST run `python -m trading_x doctor` or use the latest `data_capabilities` state before producing a report. Missing permissions or failed APIs MUST degrade the report rather than crash, except when P0 data is missing.

### III. Confidence Is Part Of The Output
Any derived signal that depends on incomplete data MUST expose its confidence. Theme detection MUST include `theme_confidence`. Limit-up event analysis MUST include `event_confidence`. A-class space-leader candidates MUST be labeled `A_STRONG` only with high-quality limit event data; otherwise they MUST be labeled `A_LITE`.

### IV. JSON Is The Machine Truth
Every daily report MUST produce a structured JSON snapshot and a Markdown report. HTML is optional. SQLite `reports.report_snapshot_json` MUST match the JSON file content so later review, dashboards, and statistics do not parse Markdown.

### V. Simple Rules Before Complex Scores
V1 candidate selection MUST use hard filters and rule layering before any composite score. `DragonScore` or similar scores may appear only as explanatory assistance and MUST NOT be the sole source of truth.

### VI. Test The Failure Paths
Permission degradation and zero-candidate days are first-class behavior. Tests MUST cover missing token, partial Tushare permissions, P0/P1/P2 degradation, A_STRONG/A_LITE downgrade, theme confidence downgrade, and continuous no-candidate reports.

### VII. Structured Plans Before Alerts
Intraday replay or watch workflows MUST read machine-executable `intraday_plans` records. They MUST NOT infer entry price, stop price, breakout price, VWAP windows, or abandon conditions from Markdown or free text.

### VIII. Replay Before Live Watch
Intraday logic MUST be proven through replay before any live watch workflow is enabled. Live data providers are a later integration detail and MUST NOT change B-class discipline rules.

### IX. Reproducible Runs Before Tuning
Every replay run MUST record its input file path and SHA-256 hash before strategy thresholds are tuned. Alert counts and reason codes must be reproducible for a fixed fixture.

### X. No Sell Semantics Without Positions
The system MUST NOT emit `SELL_TRIGGER` or T+1 sell guidance unless a position model with cost, shares, available shares, and entry date exists. Before that, stop-loss failure is an entry cancellation, not a sell instruction.

## Governance

- Changes to strategy scope, data dependency tiering, report contract, or auto-trading boundary require updating this constitution and the affected spec-kit artifacts before implementation.
- New features MUST be added under `specs/` with a user-story spec, implementation plan, data model or contract changes, and tasks.
- Any implementation that violates a principle above MUST document the violation in the plan's Complexity Tracking section and explain why the simpler compliant alternative was rejected.
- This constitution is versioned by date in git once the project repository is initialized.
