# Intraday Live Watch Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Build a read-only fake-provider live watch path that proves parity with Replay MVP before any real market source is connected.

**Architecture:** Watch loads same-date B-class `intraday_plans`, requests snapshots from an `IntradayDataProvider`, converts snapshots into the same rule input shape as replay, and writes alerts through existing alert/lock storage. The first implementation uses only a fake provider backed by replay fixture rows.

**Tech Stack:** Python 3.11, SQLite, pytest, pyright, ruff, existing `trading_x` CLI and intraday modules.

---

### Task 1: Provider Snapshot Contract

**Files:**
- Create: `src/trading_x/intraday_provider.py`
- Test: `tests/test_intraday_watch_provider.py`

- [ ] **Step 1: Write failing tests for required snapshot fields**

Create `tests/test_intraday_watch_provider.py` with tests that construct a snapshot row missing `volume_since_open` and expect rejection before rule evaluation.

- [ ] **Step 2: Run the failing test**

Run: `uv run pytest tests/test_intraday_watch_provider.py -q`

Expected: failure because `intraday_provider.py` does not exist.

- [ ] **Step 3: Implement the minimum provider contract**

Create `src/trading_x/intraday_provider.py` with `IntradaySnapshot` and `IntradayDataProvider`. Keep fields identical to the replay bar contract.

- [ ] **Step 4: Run provider tests**

Run: `uv run pytest tests/test_intraday_watch_provider.py -q`

Expected: pass.

### Task 2: Fake Provider

**Files:**
- Modify: `src/trading_x/intraday_provider.py`
- Test: `tests/test_intraday_watch_provider.py`

- [ ] **Step 1: Write failing tests for symbol filtering**

Add a test that seeds fake rows for two symbols, requests one symbol, and expects only that symbol's snapshots.

- [ ] **Step 2: Implement `FakeIntradayDataProvider`**

Add a small fake provider backed by a sequence of typed snapshots. Do not read real market data.

- [ ] **Step 3: Run provider tests**

Run: `uv run pytest tests/test_intraday_watch_provider.py -q`

Expected: pass.

### Task 3: Watch Evaluation Parity

**Files:**
- Create: `src/trading_x/intraday_watch.py`
- Test: `tests/test_intraday_watch.py`

- [ ] **Step 1: Write failing parity tests**

Add tests for `20260630`, `20260701`, `20260702`, and `20260703` fixture rows. Expected reason codes: `B_BUY_TRIGGERED`, `B_BREAKOUT_READY`, `ENTRY_CANCELLED_PRICE_OUT_OF_RANGE`, and `PRE_CLOSE_MISSING`.

- [ ] **Step 2: Implement minimal watch orchestration**

Load B-class plans, request provider snapshots for plan symbols, reuse existing B-class alert evaluation, and write alerts through existing insert logic.

- [ ] **Step 3: Run watch tests**

Run: `uv run pytest tests/test_intraday_watch.py -q`

Expected: pass.

### Task 4: Read-Only CLI

**Files:**
- Modify: `src/trading_x/cli.py`
- Test: `tests/test_intraday_watch_cli.py`

- [ ] **Step 1: Write failing CLI tests**

Assert fake-provider watch mode runs against a fixture file and does not expose order, sell, position, T+1, A-class, or L3 options.

- [ ] **Step 2: Implement minimal CLI**

Add only the fake-provider watch surface needed by tests. Do not connect mootdx or Tencent.

- [ ] **Step 3: Run CLI tests**

Run: `uv run pytest tests/test_intraday_watch_cli.py -q`

Expected: pass.

### Task 5: Verification

**Files:**
- Modify: `.github/workflows/ci.yml` only if the new watch tests need an explicit fixture command.

- [ ] **Step 1: Run full checks**

Run:

```bash
uv run pytest
uv run pyright
uv run ruff check
```

- [ ] **Step 2: Run replay fixture baseline**

Run:

```bash
uv run python -m trading_x replay --date 20260630 --input data/replay/20260630.csv
uv run python -m trading_x replay --date 20260701 --input data/replay/20260701.csv
uv run python -m trading_x replay --date 20260702 --input data/replay/20260702.csv
uv run python -m trading_x replay --date 20260703 --input data/replay/20260703.csv
```

- [ ] **Step 3: Commit**

Commit only after tests pass:

```bash
git add src/trading_x/intraday_provider.py src/trading_x/intraday_watch.py src/trading_x/cli.py tests/test_intraday_watch_provider.py tests/test_intraday_watch.py tests/test_intraday_watch_cli.py .github/workflows/ci.yml
git commit -m "Add fake intraday watch provider"
```
