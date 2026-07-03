# A股 Walk-Forward Research Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: use `executing-plans` or `subagent-driven-development` to implement this plan task by task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a research layer that uses A-share historical data to evaluate and improve the existing A/B 龙头战法 system with walk-forward, out-of-sample discipline.

**Architecture:** Keep the current local Python CLI and SQLite system. Add a research namespace beside the existing `daily`, `report`, `plans`, and `replay` flows; do not replace the existing production report path. Stage 1 is Daily Proxy Backtest only, Stage 2 is candidate-only minute replay, and Stage 3 is future live paper trading.

**Tech Stack:** Python 3.11, stdlib `argparse`, SQLite, existing Tushare dependency, existing report and candidate snapshot tables. No new database engine or heavy dependency in Stage 1.

---

## 防跑偏护栏

These rules are binding for follow-up implementation.

- Backfill starts at `20200101`; formal research starts at `20210101`. Year 2020 is warm-up data only and must not enter performance statistics.
- Tushare 2000 points are treated as the daily research backbone. Do not assume it provides complete five-year full-market minute replay.
- Split the research layers:
  - Research L1: Daily Proxy Backtest.
  - Research L2: minute replay only for selected candidates.
  - Research L3: order book, seal amount, and Level2-style replay.
- Stage 1 must only implement L1. L2/L3 must not be silently added.
- Every daily OHLC-derived trigger must carry `trigger_quality = DAILY_PROXY`. It is not a real intraday `BUY_TRIGGER`.
- A-share execution constraints are mandatory: T+1, limit-up unbuyable, one-word limit-up unbuyable, limit-down unsellable, suspension, 100-share lot size, fees, stamp duty, slippage.
- `stk_limit` is only the official limit-price reference. It is not a real limit-up event source.
- Daily-stage A-class candidates are `A_LITE` only. Do not claim first limit time, seal amount, limit break count, or re-seal strength from daily bars.
- Use unadjusted prices for entry, exit, stop, limit prices, and PnL. Adjusted prices may be used for technical indicators only if the implementation proves no future adjustment leakage.
- First version may disable breakout/platform signals around ex-right dates instead of solving full point-in-time adjusted-price reconstruction.
- Agent evolution may write proposals only. It must not modify active production parameters, enable new strategy rules, or place orders.
- Parameter search must stay small. Do not optimize stock-specific, theme-specific, month-specific, or year-specific rules.

## Current Repo Anchors

- Existing CLI entrypoint: `src/trading_x/cli.py`.
- Existing schema and idempotent init: `src/trading_x/schema.sql`, `src/trading_x/db.py`.
- Existing Tushare daily adapter: `src/trading_x/tushare_adapter.py`.
- Existing report and candidate flow: `src/trading_x/reports.py`, `src/trading_x/candidates.py`, `src/trading_x/candidate_snapshots.py`.
- Existing intraday replay flow: `src/trading_x/intraday_replay.py`, `src/trading_x/intraday_alerts.py`, `src/trading_x/intraday_models.py`.
- Existing tests follow `tests/test_*.py` with `uv run pytest`.

## Data And Schema Plan

Create only the Stage 1 schema needed for daily research.

Required tables:

- `stock_universe_history`: point-in-time universe state.
- `adj_factors`: raw adjustment factors for audit and future indicator work.
- `limit_events_daily_proxy`: daily-derived limit event approximation with `event_confidence = LOW`.
- `backtest_orders`: theoretical planned orders from candidate snapshots.
- `backtest_trades`: simulated fills and exits.
- `backtest_positions`: open and closed position states.
- `backtest_equity_curve`: daily account curve.
- `backtest_results`: aggregate run metrics.
- `agent_proposals`: Agent-generated parameter proposals.
- `parameter_approvals`: human approval records for parameter activation.

Do not remove or rewrite existing tables. Extend `schema.sql` with `CREATE TABLE IF NOT EXISTS` and add minimal `_ensure_*_columns` helpers in `db.py` only if backward-compatible migrations are needed.

Point-in-time universe rules:

- A stock is eligible only if it was listed by the trade date.
- A stock is excluded on dates when it was ST, delisting-risk, suspended, or outside the allowed board scope.
- If full historical ST/name-change data is unavailable in Stage 1, use the best available approximation and record the approximation in `data_status`.
- Never use today's stock universe to backtest past years.

## CLI Plan

Add a `research` namespace in `src/trading_x/cli.py` and route implementation to new focused modules.

Commands:

```powershell
uv run python -m trading_x research backfill --start 20200101 --end latest --warmup-start 20200101
uv run python -m trading_x research materialize-candidates --start 20210101 --end latest --config-version v1.0
uv run python -m trading_x research backtest --start 20210101 --end latest --strategy B_CAPACITY_LEADER --config-version v1.0
uv run python -m trading_x research walk-forward --start 20210101 --train-window 1y --test-window 1y
uv run python -m trading_x research walk-forward --start 20210101 --train-window 2y --test-window 1y
uv run python -m trading_x research evolve --mode propose --strategy B_CAPACITY_LEADER
```

Keep commands separate so failures are local and debuggable. Do not make one giant `walk-forward` command do backfill, candidate generation, backtest, optimization, and proposal writing in one step.

## Implementation Tasks

### Task 1: Research Schema

**Files:**
- Modify: `src/trading_x/schema.sql`
- Modify: `src/trading_x/db.py`
- Create: `tests/test_research_schema.py`

- [ ] Add Stage 1 research tables with primary keys that prevent duplicate rows on repeated runs.
- [ ] Add indexes for `(trade_date, ts_code)` and `(run_id, trade_date)` where the query path needs them.
- [ ] Test `init_db` creates all research tables in an empty database.
- [ ] Test repeated `init_db` is idempotent.
- [ ] Test existing V1 and replay tables still exist after the schema change.

Acceptance:

- `uv run pytest tests/test_research_schema.py -q` passes.
- `uv run python -m trading_x init-db --db data/qa_research_schema.db` initializes without touching production data.

### Task 2: Historical Backfill

**Files:**
- Create: `src/trading_x/research_backfill.py`
- Modify: `src/trading_x/tushare_adapter.py`
- Modify: `src/trading_x/cli.py`
- Create: `tests/test_research_backfill.py`

- [ ] Add date-range helpers that expand `latest` to the latest complete trade date.
- [ ] Fetch daily backbone data from Tushare for `20200101..end`: stock basic, trade calendar, daily quotes, daily basic, `stk_limit`, and adjustment factors.
- [ ] Store data idempotently with upserts.
- [ ] Record completeness in existing `data_status` and `data_completeness_summary` style.
- [ ] Treat missing optional data as degraded research capability, not as fake complete data.

Acceptance:

- Backfill can run on a fixture adapter without network.
- A 2020 warm-up date is stored but excluded from formal result windows.
- Missing Tushare token returns a clear error and never prints the token.

### Task 3: Point-In-Time Candidate Materialization

**Files:**
- Create: `src/trading_x/research_candidates.py`
- Modify: `src/trading_x/candidate_snapshots.py`
- Modify: `src/trading_x/cli.py`
- Create: `tests/test_research_candidates.py`

- [ ] Reuse the existing candidate selection and snapshot shape where possible.
- [ ] Generate one `candidate_runs` record per historical date and config version.
- [ ] Ensure every snapshot stores `config_hash`, `parameter_version`, data capability, theme coverage, include reasons, reject reasons, and `plan_json`.
- [ ] Ensure candidate generation for a date uses only data available on or before that date.
- [ ] Mark daily-derived A-class events as `A_LITE` and daily event confidence as `LOW`.

Acceptance:

- A stock listed after the tested date cannot appear in the historical candidate pool.
- An ST stock during a historical period is excluded for that period.
- Re-running the same date and config version does not create duplicate snapshots.

### Task 4: Daily Proxy Backtest Engine

**Files:**
- Create: `src/trading_x/research_backtest.py`
- Create: `src/trading_x/research_models.py`
- Modify: `src/trading_x/cli.py`
- Create: `tests/test_research_backtest.py`

- [ ] Convert candidate snapshots into planned `backtest_orders`.
- [ ] Use `trigger_quality = DAILY_PROXY` for every OHLC-derived trigger.
- [ ] Implement conservative B-class entry:
  - If next-day open is above `entry_high`, do not buy with `OPEN_ABOVE_ENTRY_HIGH`.
  - If next-day high is below `breakout_price`, do not buy with `NO_BREAKOUT_TOUCH`.
  - If one-word limit-up, do not buy with `ONE_WORD_LIMIT_UP`.
  - If both buy trigger and stop are touched in one daily bar, mark `AMBIGUOUS_INTRADAY_ORDER` and use the conservative outcome.
  - Entry price is `max(open, breakout_price) + slippage`; if it exceeds `entry_high`, do not buy.
- [ ] Implement T+1:
  - Buy on D+1.
  - Do not exit on D+1 even if stop is breached.
  - Record `intraday_stop_breached = 1`.
  - Earliest exit is D+2.
- [ ] Implement limit-down unsellable:
  - If exit day is one-word limit-down, keep position open and mark `LIMIT_DOWN_UNSELLABLE`.
- [ ] Apply 100-share lot rounding, commission, stamp duty, and slippage.

Acceptance:

- Tests cover T+1 stop breach, one-word limit-up buy rejection, one-word limit-down sell delay, ambiguous daily order, and normal fill/exit.
- No daily proxy test emits a real intraday `BUY_TRIGGER`.

### Task 5: Walk-Forward Evaluation

**Files:**
- Create: `src/trading_x/research_walk_forward.py`
- Create: `src/trading_x/research_parameters.py`
- Modify: `src/trading_x/cli.py`
- Create: `tests/test_research_walk_forward.py`

- [ ] Define a small parameter space for Stage 1 only.
- [ ] Support `--train-window 1y --test-window 1y`.
- [ ] Support `--train-window 2y --test-window 1y`.
- [ ] Score parameters with multi-objective constraints, not annual return alone.
- [ ] Compute out-of-sample expectancy, profit factor, max drawdown, win rate, average win/loss, trade count, exposure, turnover, consecutive losses, and tail loss.
- [ ] Reject parameter sets that depend on a single year for more than 50% of total profit.

Initial parameter space:

- B-class: `market_emotion_min`, `theme_strength_min`, `theme_confidence_min`, `entry_gap_min`, `entry_gap_max`, `breakout_buffer`, `volume_ratio_min`, `turnover_min`, `amount_min`, `max_stop_distance`, `holding_days_max`, `take_profit_r_multiple`.
- A-class daily proxy: `highest_board_min`, `limit_close_required`, `theme_follow_min`, `market_emotion_min`, `limit_up_count_min`, `limit_down_count_max`.

Acceptance:

- 2022 test folds cannot use 2023 or later data.
- The report contains both 1Y and 2Y rolling results.
- A parameter that only improves one year but worsens most folds is rejected.

### Task 6: Agent Proposal And Approval Gate

**Files:**
- Create: `src/trading_x/research_evolve.py`
- Modify: `src/trading_x/cli.py`
- Create: `tests/test_research_evolve.py`

- [ ] `research evolve --mode propose` writes to `agent_proposals`.
- [ ] Proposals include base version, proposed version, changed parameters, fold evidence, risks, and recommendation.
- [ ] Proposals never update active production parameters.
- [ ] Human approval is represented only by `parameter_approvals`.
- [ ] Approved parameters still must pass acceptance gates before becoming eligible for production activation.

Acceptance:

- A proposal can be written without changing existing report behavior.
- Rejected proposals remain auditable.
- No command in Stage 1 automatically activates a proposed parameter version.

### Task 7: Research Reports

**Files:**
- Create: `src/trading_x/research_reports.py`
- Modify: `src/trading_x/cli.py`
- Create: `tests/test_research_reports.py`

- [ ] Write `reports/research/walk_forward_summary.md`.
- [ ] Write `reports/research/agent_proposals/<proposal_id>.md`.
- [ ] Include per-year OOS metrics, fold results, accepted/rejected parameter reasons, and baseline comparison.
- [ ] Label Daily Proxy limitations clearly in every research report.

Acceptance:

- Report includes 1Y and 2Y rolling summaries.
- Report includes rejected parameter reasons.
- Report states that Daily Proxy Backtest is not a true intraday trigger replay.

### Task 8: Verification Gate

**Files:**
- Modify only tests needed by Tasks 1-7.

- [ ] Run focused tests for each task.
- [ ] Run `uv run pytest -q`.
- [ ] Run a fixture smoke path:

```powershell
uv run python -m trading_x init-db --db data/qa_research.db
uv run python -m trading_x research walk-forward --db data/qa_research.db --start 20210101 --train-window 1y --test-window 1y
```

Acceptance:

- Tests pass.
- Smoke path writes a research report or a clear fixture-data-missing error.
- No report, CLI output, or database row prints `TUSHARE_TOKEN`.

## Acceptance Gates For New Parameters

A proposed parameter version is eligible for approval only if all conditions hold:

- Out-of-sample profit factor is above baseline.
- Out-of-sample max drawdown is not worse than baseline, or return/drawdown improves materially.
- At least 3 of 5 yearly folds are not worse than baseline.
- No single year contributes more than 50% of total OOS profit.
- Trade count is above the configured minimum.
- Parameter changes are small and explainable.
- Strategy complexity does not increase materially.
- Human approval is recorded in `parameter_approvals`.

Otherwise the proposal remains rejected or review-only.

## Must Not Have

- No auto-trading.
- No broker integration.
- No automatic production parameter activation.
- No full-market five-year minute replay in Stage 1.
- No new heavy storage engine in Stage 1.
- No future-adjusted price leakage.
- No use of today's stock universe for historical tests.
- No treating `stk_limit` as first limit time, seal amount, or re-seal data.
- No optimizing rules by individual stock, theme, month, or special historical year.

## Minimal First Slice

If the executor wants the smallest useful implementation, build only this slice first:

1. Add schema for `stock_universe_history`, `limit_events_daily_proxy`, `backtest_orders`, `backtest_trades`, `backtest_results`, `agent_proposals`, and `parameter_approvals`.
2. Add `research backtest` against existing candidate snapshots.
3. Enforce T+1, limit-up unbuyable, limit-down unsellable, lot size, fees, and `DAILY_PROXY`.
4. Generate one markdown summary with baseline metrics.

This first slice is enough to validate the backtest engine before broad historical backfill and parameter search.
