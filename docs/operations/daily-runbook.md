# Trading X Daily Runbook

This runbook is the operator path after the Spec Kit lines `001` through `006` are implemented. It keeps the system rule-driven, replayable, and non-trading: no broker API, no automatic order placement, no free-text plan guessing.

## Safety Boundaries

- Do not put `TUSHARE_TOKEN` in reports, screenshots, logs, commits, or chat.
- Do not edit generated `intraday_plans` by hand for a real trading day. Generate them from structured `candidates` / report data.
- Do not treat `watch` or `replay` output as an order. Alerts are discipline signals only.
- Do not use Markdown reports as machine input for buy, stop, breakout, VWAP, or sell fields.
- Keep real provider data disabled for buying until provider evaluation proves timestamp, amount, volume, coverage, stability, and compliance boundaries.

## One-Time Setup

```powershell
Copy-Item .env.example .env
uv run python -m trading_x init-db
uv run python -m trading_x doctor --date YYYYMMDD
```

Then edit `.env` locally and set your own `TUSHARE_TOKEN`. If `doctor` fails because the token is missing, fix `.env` or the process environment first.

## Daily Smoke

```powershell
.\scripts\daily-smoke.ps1 -Date YYYYMMDD
```

This runs the daily operational path. If `data/replay/YYYYMMDD.csv` exists, it also runs replay and fake watch.

## Daily After-Close Flow

Run the daily pipeline for the trade date after close:

```powershell
uv run python -m trading_x daily --date YYYYMMDD
```

This runs the data capability check, P0 update, report generation, and daily summary. Expected outputs:

```text
reports/YYYYMMDD_report.json
reports/YYYYMMDD_report.md
data/trading_x.db
```

Use acceptance on complete days only:

```powershell
uv run python -m trading_x acceptance --last-complete-n 10
uv run python -m trading_x acceptance --list-incomplete
```

## Intraday Plan Materialization

Generate structured plans before replay or watch:

```powershell
uv run python -m trading_x plans materialize --date YYYYMMDD
uv run python -m trading_x plans symbols --date YYYYMMDD
```

For A-class explicit replay work:

```powershell
uv run python -m trading_x plans materialize --date YYYYMMDD --strategy A_SPACE_LEADER
```

`intraday_plans` is the machine execution snapshot. If no plan exists, replay exits normally and writes a replay report saying no plans were available.

## Replay MVP

Replay uses a CSV with this minimum schema:

```text
trade_date,quote_time,ts_code,price,amount_since_open,volume_since_open,bar_high,bar_low
```

Default replay path:

```powershell
uv run python -m trading_x replay --date YYYYMMDD
```

Explicit replay path:

```powershell
uv run python -m trading_x replay --date YYYYMMDD --input data/replay/YYYYMMDD.csv
```

A-class smoke fixture:

```powershell
uv run python -m trading_x replay --date 20260630 --strategy A_SPACE_LEADER --materialize --input data/replay/20260630_a_space_leader.csv
```

For real dates, the replay CSV must cover every symbol in `plans symbols` for that strategy.

Expected outputs:

```text
reports/YYYYMMDD_replay_report.md
intraday_alerts
intraday_alert_locks
intraday_replay_runs
```

`intraday_replay_runs.input_sha256` is the replay reproducibility key. If a CSV changes, a new run row should preserve the new hash.

## Fake Watch

Fake watch reuses replay-style rows through the provider abstraction. It is read-only and does not submit orders.

```powershell
uv run python -m trading_x watch --date YYYYMMDD --input data/replay/YYYYMMDD.csv
```

Use this for parity checks before any real provider is trusted.

## Provider Offline Smoke

```powershell
.\scripts\provider-offline.ps1 -Date YYYYMMDD -Source tencent_snapshot
```

This consumes `data/provider_samples/YYYYMMDD_tencent_snapshot.json`. If the sample is missing, it writes a template and stops without fetching live data.

## Provider Evaluation

Generate a fill-in template from current plans:

```powershell
uv run python -m trading_x provider-sample-template --source mootdx --date YYYYMMDD --output data/provider_samples/YYYYMMDD_mootdx_template.json
```

After filling real sampled fields, evaluate offline:

```powershell
uv run python -m trading_x provider-evaluate --source mootdx --date YYYYMMDD --symbols 300001.SZ --sample data/provider_samples/YYYYMMDD_mootdx.json --output-dir reports/provider_eval --compliance-use-status approved
```

Export a validated provider sample to replay CSV:

```powershell
uv run python -m trading_x provider-export-replay --source mootdx --date YYYYMMDD --sample data/provider_samples/YYYYMMDD_mootdx.json --output data/replay/YYYYMMDD.csv
```

Provider status must remain evaluation-only until the source proves field completeness and compliance.

## Positions And Sell Risk

Import structured positions before sell-side replay checks:

```powershell
uv run python -m trading_x positions import --date YYYYMMDD --input data/positions/YYYYMMDD_positions.json
```

Required position fields:

```text
trade_date,ts_code,total_shares,available_shares,avg_cost,market_value
```

Sell-side semantics:

- No same-date position row: stop break remains `ENTRY_CANCELLED`.
- `available_shares > 0`: stop break can emit `SELL_TRIGGER / SELL_TRIGGER_STOP_BREAK` and locks the same-day terminal sell alert.
- `available_shares = 0`: stop break emits risk-only `RISK_ALERT / SELL_BLOCKED_T1_NO_AVAILABLE_SHARES`, not executable sell trigger.

## Verification Gates

Run before trusting a code or rule change:

```powershell
uv run pytest -q
uv run pyright
uv run ruff check
```

Useful targeted smoke paths:

```powershell
uv run pytest tests/test_intraday_replay.py tests/test_positions_sell_alerts.py -q
uv run pytest tests/test_intraday_watch_parity.py tests/test_provider_evaluation.py -q
uv run pytest tests/test_a_class_replay_mvp.py -q
```

## Troubleshooting

- `REPLAY_CSV_MISSING_REQUIRED_COLUMNS`: check the replay CSV header, especially `volume_since_open`.
- `REPLAY_CSV_MISSING_PLAN_SYMBOLS`: plans exist for symbols not present in the replay CSV.
- `PLAN_INVALID`: inspect `intraday_plans` required fields and ranges; do not repair by editing Markdown.
- `PRE_CLOSE_MISSING`: watch alerts may appear, but buy triggers must remain blocked.
- `POSITION_LEDGER_MISSING_REQUIRED_FIELDS`: the positions file is not complete enough for sell-risk semantics.
- `PROVIDER_SAMPLE_*`: the provider sample is not fit for evaluation or replay export.
- Windows `uv` cache access denied: rerun from a shell with access to `%LOCALAPPDATA%\uv\cache`.

## Current System Boundary

Implemented lines:

- `001-ai-stock-selection-v1`: daily stock selection and reports.
- `002-intraday-replay-mvp`: B-class replay discipline.
- `003-intraday-live-watch`: fake provider watch parity, read-only.
- `004-real-provider-evaluation`: offline provider evaluation and replay export.
- `005-positions-sell-risk`: structured positions and sell-risk alerts.
- `006-a-class-replay-mvp`: explicit A-class replay path.

Still intentionally out of scope:

- Broker integration.
- Automatic order placement.
- Free-text plan parsing.
- Unproven real-time provider buy triggers.
- UI dashboard.