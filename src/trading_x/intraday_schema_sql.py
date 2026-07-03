CREATE_INTRADAY_PLANS_SQL = (
    "CREATE TABLE intraday_plans ("
    "trade_date TEXT NOT NULL, ts_code TEXT NOT NULL, name TEXT, strategy_type TEXT NOT NULL, "
    "allow_trade INTEGER, plan_status TEXT, entry_low REAL, entry_high REAL, breakout_price REAL, "
    "stop_price REAL, max_stop_distance REAL, max_position_cash REAL, max_loss REAL, "
    "official_pre_close REAL, pre_close_source TEXT, vwap_active_after TEXT, "
    "vwap_above_confirm_seconds INTEGER, volume_gate_enabled INTEGER, volume_min_abs_amount REAL, "
    "volume_same_window_multiplier REAL, volume_ratio_0935 REAL, volume_ratio_0945 REAL, "
    "volume_ratio_1000 REAL, theme_name TEXT, theme_confidence TEXT, theme_strength_score REAL, "
    "source_candidate_id TEXT, source_report_date TEXT, plan_json TEXT, system_version TEXT, "
    "created_at TEXT, PRIMARY KEY (trade_date, ts_code, strategy_type))"
)

COPY_INTRADAY_PLANS_SQL = (
    "INSERT OR IGNORE INTO intraday_plans ("
    "trade_date, ts_code, name, strategy_type, allow_trade, plan_status, entry_low, entry_high, "
    "breakout_price, stop_price, max_stop_distance, max_position_cash, max_loss, official_pre_close, "
    "pre_close_source, vwap_active_after, vwap_above_confirm_seconds, volume_gate_enabled, "
    "volume_min_abs_amount, volume_same_window_multiplier, volume_ratio_0935, volume_ratio_0945, "
    "volume_ratio_1000, theme_name, theme_confidence, theme_strength_score, source_candidate_id, "
    "source_report_date, plan_json, system_version, created_at"
    ") SELECT trade_date, ts_code, name, strategy_type, allow_trade, plan_status, entry_low, entry_high, "
    "breakout_price, stop_price, max_stop_distance, max_position_cash, max_loss, official_pre_close, "
    "pre_close_source, vwap_active_after, vwap_above_confirm_seconds, volume_gate_enabled, "
    "volume_min_abs_amount, volume_same_window_multiplier, volume_ratio_0935, volume_ratio_0945, "
    "volume_ratio_1000, theme_name, theme_confidence, theme_strength_score, source_candidate_id, "
    "source_report_date, plan_json, system_version, created_at FROM intraday_plans_old "
    "WHERE trade_date IS NOT NULL AND TRIM(trade_date) != '' "
    "AND ts_code IS NOT NULL AND TRIM(ts_code) != '' "
    "AND strategy_type IS NOT NULL AND TRIM(strategy_type) != ''"
)

CREATE_INTRADAY_ALERTS_SQL = (
    "CREATE TABLE intraday_alerts ("
    "id INTEGER PRIMARY KEY AUTOINCREMENT, trade_date TEXT NOT NULL, ts_code TEXT NOT NULL, "
    "strategy_type TEXT NOT NULL, alert_time TEXT NOT NULL, alert_type TEXT NOT NULL, severity TEXT, rule_id TEXT, "
    "title TEXT, message TEXT, reason_code TEXT NOT NULL, state_before TEXT, state_after TEXT, "
    "snapshot_json TEXT, plan_json TEXT, created_at TEXT)"
)

COPY_INTRADAY_ALERTS_SQL = (
    "INSERT INTO intraday_alerts ("
    "trade_date, ts_code, strategy_type, alert_time, alert_type, severity, rule_id, "
    "title, message, reason_code, state_before, state_after, snapshot_json, plan_json, created_at"
    ") SELECT trade_date, ts_code, strategy_type, alert_time, alert_type, severity, rule_id, "
    "title, message, reason_code, state_before, state_after, snapshot_json, plan_json, created_at "
    "FROM intraday_alerts_old WHERE trade_date IS NOT NULL AND TRIM(trade_date) != '' "
    "AND ts_code IS NOT NULL AND TRIM(ts_code) != '' "
    "AND strategy_type IS NOT NULL AND TRIM(strategy_type) != '' "
    "AND alert_time IS NOT NULL AND TRIM(alert_time) != '' "
    "AND alert_type IS NOT NULL AND TRIM(alert_type) != '' "
    "AND reason_code IS NOT NULL AND TRIM(reason_code) != ''"
)

CREATE_INTRADAY_ALERT_LOCKS_SQL = (
    "CREATE TABLE intraday_alert_locks ("
    "trade_date TEXT NOT NULL, ts_code TEXT NOT NULL, strategy_type TEXT NOT NULL, "
    "alert_type TEXT NOT NULL, locked INTEGER, "
    "locked_at TEXT, rule_id TEXT, reset_count INTEGER DEFAULT 0, reset_reason TEXT, "
    "PRIMARY KEY (trade_date, ts_code, strategy_type, alert_type))"
)

COPY_INTRADAY_ALERT_LOCKS_SQL = (
    "INSERT OR IGNORE INTO intraday_alert_locks ("
    "trade_date, ts_code, strategy_type, alert_type, locked, locked_at, rule_id, reset_count, reset_reason"
    ") SELECT trade_date, ts_code, strategy_type, alert_type, locked, locked_at, rule_id, "
    "reset_count, reset_reason FROM intraday_alert_locks_old "
    "WHERE trade_date IS NOT NULL AND TRIM(trade_date) != '' "
    "AND ts_code IS NOT NULL AND TRIM(ts_code) != '' "
    "AND strategy_type IS NOT NULL AND TRIM(strategy_type) != '' "
    "AND alert_type IS NOT NULL AND TRIM(alert_type) != ''"
)

CREATE_INTRADAY_REPLAY_RUNS_SQL = (
    "CREATE TABLE intraday_replay_runs ("
    "id INTEGER PRIMARY KEY AUTOINCREMENT, trade_date TEXT NOT NULL, input_file TEXT NOT NULL, "
    "input_sha256 TEXT NOT NULL, plan_count INTEGER NOT NULL, alert_count INTEGER NOT NULL, "
    "status TEXT NOT NULL, started_at TEXT NOT NULL, ended_at TEXT NOT NULL, "
    "error_message TEXT)"
)

COPY_INTRADAY_REPLAY_RUNS_SQL = (
    "INSERT INTO intraday_replay_runs ("
    "trade_date, input_file, input_sha256, plan_count, alert_count, status, started_at, ended_at, error_message"
    ") SELECT trade_date, input_file, input_sha256, plan_count, alert_count, status, started_at, ended_at, "
    "error_message FROM intraday_replay_runs_old WHERE trade_date IS NOT NULL AND TRIM(trade_date) != '' "
    "AND input_file IS NOT NULL AND TRIM(input_file) != '' AND input_sha256 IS NOT NULL "
    "AND plan_count IS NOT NULL AND alert_count IS NOT NULL "
    "AND status IN ('SUCCESS', 'FAILED') "
    "AND started_at IS NOT NULL AND TRIM(started_at) != '' "
    "AND ended_at IS NOT NULL AND TRIM(ended_at) != ''"
)
