# Data Model: AI 龙头选股系统 V1

## Enums

### DataCapabilityLevel

- `FULL`: P0 available and key P1 data available.
- `BASIC`: P0 available and at least one P1 dependency unavailable.
- `DEGRADED`: at least one P0 dependency unavailable; candidates are blocked.

### Confidence

- `HIGH`: direct high-quality source supports the signal.
- `MEDIUM`: source supports the signal but lacks some detail.
- `LOW`: signal is approximated from weaker data.
- `UNAVAILABLE`: signal could not be calculated.

### StrategyType

- `A_SPACE_LEADER`
- `B_CAPACITY_LEADER`

### CandidateGrade

- `A_STRONG`: A-class candidate with high-quality limit event data.
- `A_LITE`: A-class candidate using close-at-limit and streak approximation.
- `B_CORE`: B-class capacity leader passing core filters.
- `B_WATCH`: B-class candidate with lower confidence or weaker trend confirmation.

## Tables

### data_capabilities

Records the latest observed availability of each checked Tushare API.

```sql
CREATE TABLE data_capabilities (
    api_name TEXT PRIMARY KEY,
    available INTEGER NOT NULL,
    min_points_required INTEGER,
    last_checked_at TEXT,
    last_error_code TEXT,
    last_error_msg TEXT,
    fallback_mode TEXT
);
```

### stock_universe

V1 tradable universe after board and basic risk filters.

```sql
CREATE TABLE stock_universe (
    ts_code TEXT PRIMARY KEY,
    symbol TEXT,
    name TEXT,
    exchange TEXT,
    market TEXT,
    list_date TEXT,
    is_st INTEGER NOT NULL,
    is_delisting_risk INTEGER NOT NULL,
    included INTEGER NOT NULL,
    excluded_reason TEXT
);
```

### daily_quotes

Daily OHLCV and amount data.

```sql
CREATE TABLE daily_quotes (
    trade_date TEXT,
    ts_code TEXT,
    open REAL,
    high REAL,
    low REAL,
    close REAL,
    pre_close REAL,
    pct_chg REAL,
    vol REAL,
    amount REAL,
    PRIMARY KEY (trade_date, ts_code)
);
```

### daily_basic

Liquidity and valuation snapshot used for filters and B-class selection.

```sql
CREATE TABLE daily_basic (
    trade_date TEXT,
    ts_code TEXT,
    turnover_rate REAL,
    volume_ratio REAL,
    pe_ttm REAL,
    pb REAL,
    total_mv REAL,
    circ_mv REAL,
    PRIMARY KEY (trade_date, ts_code)
);
```

### stk_limit_prices

Stores only daily limit-up and limit-down prices.

```sql
CREATE TABLE stk_limit_prices (
    trade_date TEXT,
    ts_code TEXT,
    pre_close REAL,
    up_limit REAL,
    down_limit REAL,
    PRIMARY KEY (trade_date, ts_code)
);
```

### limit_events

Stores interpreted limit-up or limit-down event quality.

```sql
CREATE TABLE limit_events (
    trade_date TEXT,
    ts_code TEXT,
    limit_type TEXT,
    is_limit_close INTEGER,
    first_limit_time TEXT,
    last_limit_time TEXT,
    open_times INTEGER,
    limit_break_count INTEGER,
    seal_amount REAL,
    event_confidence TEXT,
    data_source TEXT,
    PRIMARY KEY (trade_date, ts_code, limit_type)
);
```

Rules:

- `stk_limit_prices` MUST NOT populate event fields.
- If only `close == up_limit` is known, `event_confidence = LOW`.
- `A_STRONG` requires `event_confidence = HIGH`.

### theme_strength

Theme or concept strength used for main-line judgment.

```sql
CREATE TABLE theme_strength (
    trade_date TEXT,
    theme_name TEXT,
    strength_level TEXT,
    theme_confidence TEXT,
    limit_count INTEGER,
    candidate_count INTEGER,
    leading_stock TEXT,
    data_source TEXT,
    reason TEXT,
    PRIMARY KEY (trade_date, theme_name)
);
```

Rules:

- `HIGH`: `limit_cpt_list` or equivalent strong board source available.
- `MEDIUM`: derived from limit count plus industry or concept mapping.
- `LOW`: only free concept tags available.
- `UNAVAILABLE`: no reliable theme data.

### candidates

Daily candidate output before report rendering.

```sql
CREATE TABLE candidates (
    trade_date TEXT,
    ts_code TEXT,
    strategy_type TEXT,
    candidate_grade TEXT,
    risk_pass INTEGER NOT NULL,
    market_status TEXT,
    theme_name TEXT,
    theme_confidence TEXT,
    event_confidence TEXT,
    liquidity_rank REAL,
    leader_rank REAL,
    breakout_rank REAL,
    buy_observation TEXT,
    abandon_conditions TEXT,
    max_chase_limit TEXT,
    structural_stop TEXT,
    suggested_position TEXT,
    max_loss TEXT,
    data_confidence TEXT,
    PRIMARY KEY (trade_date, ts_code, strategy_type)
);
```

### reports

Report file locations and machine-truth snapshot.

```sql
CREATE TABLE reports (
    trade_date TEXT PRIMARY KEY,
    system_version TEXT,
    report_md_path TEXT,
    report_html_path TEXT,
    report_json_path TEXT,
    report_snapshot_json TEXT,
    data_capability TEXT,
    generated_at TEXT
);
```

### trade_logs

Prepared for V1+ CSV import but not used by V1.

```sql
CREATE TABLE trade_logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    trade_date TEXT,
    ts_code TEXT,
    side TEXT,
    price REAL,
    shares INTEGER,
    strategy_type TEXT,
    note TEXT,
    created_at TEXT
);
```

## Report Capability Rules

- Missing `stock_basic`, `trade_cal`, `daily`, `daily_basic`, or `stk_limit` sets capability to `DEGRADED`.
- Missing `limit_events`, theme mapping, `top_list`, or `limit_cpt_list` sets capability to `BASIC` if P0 is complete.
- Missing `moneyflow`, `margin`, pledge, float, forecast, or financial detail data does not change candidate eligibility.

## Candidate Ordering

1. Exclude all `risk_pass = 0`.
2. Rank A and B candidates in separate buckets.
3. Prefer stronger market status.
4. Prefer stronger `theme_strength`.
5. Prefer stronger leader rank.
6. Prefer higher liquidity.
7. Prefer stronger limit or breakout signal.
8. Output at most five total candidates.
