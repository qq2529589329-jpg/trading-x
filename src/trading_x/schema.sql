CREATE TABLE IF NOT EXISTS data_capabilities (
    api_name TEXT PRIMARY KEY,
    available INTEGER NOT NULL,
    min_points_required INTEGER,
    last_checked_at TEXT,
    last_error_code TEXT,
    last_error_msg TEXT,
    fallback_mode TEXT
);

CREATE TABLE IF NOT EXISTS data_status (
    trade_date TEXT,
    api_name TEXT,
    status TEXT,
    row_count INTEGER,
    expected_min_rows INTEGER,
    coverage_ratio REAL,
    max_trade_date TEXT,
    checked_at TEXT,
    error_message TEXT,
    source TEXT,
    PRIMARY KEY (trade_date, api_name)
);

CREATE TABLE IF NOT EXISTS data_completeness_summary (
    trade_date TEXT PRIMARY KEY,
    p0_complete INTEGER,
    p1_complete INTEGER,
    data_capability TEXT,
    latest_complete_date TEXT,
    partial_reason TEXT,
    checked_at TEXT
);

CREATE TABLE IF NOT EXISTS stock_universe (
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

CREATE TABLE IF NOT EXISTS daily_quotes (
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
    regular_amount REAL,
    post_close_amount REAL,
    total_amount REAL,
    post_close_amount_ratio REAL,
    post_close_data_available INTEGER,
    PRIMARY KEY (trade_date, ts_code)
);

CREATE TABLE IF NOT EXISTS daily_basic (
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

CREATE TABLE IF NOT EXISTS stk_limit_prices (
    trade_date TEXT,
    ts_code TEXT,
    pre_close REAL,
    up_limit REAL,
    down_limit REAL,
    PRIMARY KEY (trade_date, ts_code)
);

CREATE TABLE IF NOT EXISTS limit_events (
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

CREATE TABLE IF NOT EXISTS theme_strength (
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

CREATE TABLE IF NOT EXISTS theme_members (
    ts_code TEXT PRIMARY KEY,
    name TEXT,
    industry TEXT,
    theme_primary TEXT,
    theme_tags TEXT,
    theme_tier TEXT DEFAULT 'IMPORTANT',
    theme_weight REAL DEFAULT 0.7,
    theme_source TEXT,
    confidence TEXT,
    updated_at TEXT,
    notes TEXT
);

CREATE TABLE IF NOT EXISTS theme_daily_strength (
    trade_date TEXT,
    theme_name TEXT,
    theme_member_count INTEGER,
    theme_up_count INTEGER,
    theme_limit_up_count INTEGER,
    theme_avg_pct_chg REAL,
    theme_total_amount REAL,
    theme_candidate_count INTEGER,
    theme_strength_score REAL,
    theme_confidence TEXT,
    core_symbols TEXT,
    weighted_limit_up_count REAL,
    weighted_avg_pct_chg REAL,
    weighted_total_amount REAL,
    PRIMARY KEY (trade_date, theme_name)
);

CREATE TABLE IF NOT EXISTS candidates (
    trade_date TEXT,
    ts_code TEXT,
    strategy_type TEXT,
    candidate_grade TEXT,
    risk_pass INTEGER NOT NULL,
    market_status TEXT,
    theme_name TEXT,
    theme_tags TEXT,
    theme_rank_today INTEGER,
    theme_strength_score REAL,
    theme_position TEXT,
    theme_confidence TEXT,
    event_confidence TEXT,
    liquidity_rank REAL,
    leader_rank REAL,
    breakout_rank REAL,
    entry_reason TEXT,
    veto_items TEXT,
    buy_observation TEXT,
    abandon_conditions TEXT,
    max_chase_limit TEXT,
    structural_stop TEXT,
    suggested_position TEXT,
    max_loss TEXT,
    data_confidence TEXT,
    PRIMARY KEY (trade_date, ts_code, strategy_type)
);

CREATE TABLE IF NOT EXISTS candidate_runs (
    run_id TEXT PRIMARY KEY,
    trade_date TEXT,
    system_version TEXT,
    strategy_version TEXT,
    threshold_version TEXT,
    config_hash TEXT,
    data_capability TEXT,
    p0_complete INTEGER,
    theme_coverage_ratio REAL,
    generated_at TEXT,
    report_json_path TEXT,
    report_md_path TEXT,
    notes TEXT
);

CREATE TABLE IF NOT EXISTS candidate_snapshots (
    run_id TEXT,
    trade_date TEXT,
    rank INTEGER,
    ts_code TEXT,
    name TEXT,
    strategy_type TEXT,
    leader_status TEXT,
    theme_name TEXT,
    theme_confidence TEXT,
    theme_strength_score REAL,
    data_capability TEXT,
    rule_version_at_signal TEXT,
    rule_regime_at_signal TEXT,
    entry_low REAL,
    entry_high REAL,
    stop_price REAL,
    breakout_price REAL,
    max_position_cash REAL,
    max_loss REAL,
    include_reasons_json TEXT,
    reject_reasons_json TEXT,
    plan_json TEXT,
    created_at TEXT,
    PRIMARY KEY (run_id, ts_code, strategy_type)
);

DROP VIEW IF EXISTS candidates_latest;

CREATE VIEW candidates_latest AS
SELECT cs.*
FROM candidate_snapshots cs
JOIN (
    SELECT cr.trade_date, cr.run_id
    FROM candidate_runs cr
    WHERE cr.run_id = (
        SELECT latest_run.run_id
        FROM candidate_runs latest_run
        WHERE latest_run.trade_date = cr.trade_date
        ORDER BY latest_run.generated_at DESC, latest_run.run_id DESC
        LIMIT 1
    )
) latest
ON cs.trade_date = latest.trade_date
AND cs.run_id = latest.run_id;

CREATE TABLE IF NOT EXISTS reports (
    trade_date TEXT PRIMARY KEY,
    system_version TEXT,
    report_md_path TEXT,
    report_html_path TEXT,
    report_json_path TEXT,
    report_snapshot_json TEXT,
    data_capability TEXT,
    generated_at TEXT
);

CREATE TABLE IF NOT EXISTS trade_logs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    trade_date TEXT,
    ts_code TEXT,
    side TEXT,
    price REAL,
    shares INTEGER,
    strategy_type TEXT,
    rule_version_at_entry TEXT,
    rule_version_at_exit TEXT,
    note TEXT,
    created_at TEXT
);

CREATE TABLE IF NOT EXISTS position_import_runs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    trade_date TEXT NOT NULL,
    input_file TEXT NOT NULL,
    input_sha256 TEXT NOT NULL,
    position_count INTEGER NOT NULL,
    status TEXT NOT NULL,
    started_at TEXT NOT NULL,
    ended_at TEXT NOT NULL,
    error_message TEXT
);

CREATE TABLE IF NOT EXISTS positions (
    trade_date TEXT NOT NULL,
    ts_code TEXT NOT NULL,
    name TEXT,
    total_shares REAL NOT NULL,
    available_shares REAL NOT NULL,
    avg_cost REAL NOT NULL,
    market_value REAL NOT NULL,
    source TEXT NOT NULL,
    source_run_id INTEGER NOT NULL,
    created_at TEXT NOT NULL,
    PRIMARY KEY (trade_date, ts_code)
);

CREATE TABLE IF NOT EXISTS post_close_activity (
    trade_date TEXT,
    ts_code TEXT,
    close_price REAL,
    post_close_amount REAL,
    post_close_volume REAL,
    post_close_amount_ratio REAL,
    data_available INTEGER,
    source TEXT,
    created_at TEXT,
    PRIMARY KEY (trade_date, ts_code)
);

CREATE TABLE IF NOT EXISTS intraday_plans (
    trade_date TEXT NOT NULL,
    ts_code TEXT NOT NULL,
    name TEXT,
    strategy_type TEXT NOT NULL,
    allow_trade INTEGER,
    plan_status TEXT,
    entry_low REAL,
    entry_high REAL,
    breakout_price REAL,
    stop_price REAL,
    max_stop_distance REAL,
    max_position_cash REAL,
    max_loss REAL,
    official_pre_close REAL,
    pre_close_source TEXT,
    vwap_active_after TEXT,
    vwap_above_confirm_seconds INTEGER,
    volume_gate_enabled INTEGER,
    volume_min_abs_amount REAL,
    volume_same_window_multiplier REAL,
    volume_ratio_0935 REAL,
    volume_ratio_0945 REAL,
    volume_ratio_1000 REAL,
    theme_name TEXT,
    theme_confidence TEXT,
    theme_strength_score REAL,
    source_candidate_id TEXT,
    source_report_date TEXT,
    rule_version_at_signal TEXT,
    rule_regime_at_signal TEXT,
    plan_json TEXT,
    system_version TEXT,
    created_at TEXT,
    PRIMARY KEY (trade_date, ts_code, strategy_type)
);

CREATE TABLE IF NOT EXISTS intraday_alerts (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    trade_date TEXT NOT NULL,
    ts_code TEXT NOT NULL,
    strategy_type TEXT NOT NULL,
    alert_time TEXT NOT NULL,
    alert_type TEXT NOT NULL,
    severity TEXT,
    rule_id TEXT,
    title TEXT,
    message TEXT,
    reason_code TEXT NOT NULL,
    state_before TEXT,
    state_after TEXT,
    snapshot_json TEXT,
    plan_json TEXT,
    created_at TEXT
);

CREATE TABLE IF NOT EXISTS intraday_alert_locks (
    trade_date TEXT NOT NULL,
    ts_code TEXT NOT NULL,
    strategy_type TEXT NOT NULL,
    alert_type TEXT NOT NULL,
    locked INTEGER,
    locked_at TEXT,
    rule_id TEXT,
    reset_count INTEGER DEFAULT 0,
    reset_reason TEXT,
    PRIMARY KEY (trade_date, ts_code, strategy_type, alert_type)
);

CREATE TABLE IF NOT EXISTS intraday_replay_runs (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    trade_date TEXT NOT NULL,
    input_file TEXT NOT NULL,
    input_sha256 TEXT NOT NULL,
    plan_count INTEGER NOT NULL,
    alert_count INTEGER NOT NULL,
    status TEXT NOT NULL,
    started_at TEXT NOT NULL,
    ended_at TEXT NOT NULL,
    error_message TEXT
);
