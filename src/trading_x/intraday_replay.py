from collections.abc import Sequence
from pathlib import Path
import hashlib
import sqlite3

from trading_x.intraday_alerts import disable_invalid_plans, evaluate_replay, load_plans
from trading_x.intraday_replay_csv import load_replay_bars
from trading_x.intraday_models import (
    IntradayAlert,
    ReplayResult,
    utc_now_text,
)
from trading_x.types import StrategyType


def run_replay(
    db_path: Path,
    trade_date: str,
    input_path: Path,
    report_dir: Path,
) -> ReplayResult:
    started_at = utc_now_text()
    input_sha256 = _sha256(input_path)

    def failed(plan_total: int, error_message: str) -> ReplayResult:
        return ReplayResult(
            trade_date,
            str(input_path),
            input_sha256,
            plan_total,
            0,
            "FAILED",
            error_message,
            started_at,
            utc_now_text(),
        )

    with sqlite3.connect(db_path) as conn:
        conn.execute(
            "DELETE FROM intraday_alerts WHERE trade_date = ? AND strategy_type = ?",
            (trade_date, StrategyType.B_CAPACITY_LEADER),
        )
        conn.execute(
            "DELETE FROM intraday_alert_locks WHERE trade_date = ? AND strategy_type = ?",
            (trade_date, StrategyType.B_CAPACITY_LEADER),
        )
        plan_count = conn.execute(
            "SELECT COUNT(*) FROM intraday_plans WHERE trade_date = ? AND strategy_type = ?",
            (trade_date, StrategyType.B_CAPACITY_LEADER),
        ).fetchone()[0]
    if plan_count == 0:
        if input_path.exists():
            _, error = load_replay_bars(input_path, trade_date)
            if error is not None:
                result = failed(0, error)
                _write_replay_report(report_dir, result, [], [])
                _record_replay_run(db_path, result)
                return result
        elif len(trade_date) != 8 or not trade_date.isdigit():
            result = failed(0, "REPLAY_DATE_INVALID")
            _write_replay_report(report_dir, result, [], [])
            _record_replay_run(db_path, result)
            return result
        result = ReplayResult(
            trade_date,
            str(input_path),
            input_sha256,
            0,
            0,
            "SUCCESS",
            None,
            started_at,
            utc_now_text(),
        )
        _write_replay_report(report_dir, result, [], [])
        _record_replay_run(db_path, result)
        return result
    bars, error = load_replay_bars(input_path, trade_date)
    if error is not None:
        result = failed(plan_count, error)
        _write_replay_report(report_dir, result, [], [])
        _record_replay_run(db_path, result)
        return result
    with sqlite3.connect(db_path) as conn:
        conn.row_factory = sqlite3.Row
        plans = load_plans(conn, trade_date)
        invalid_reasons = disable_invalid_plans(conn, plans)
        if plans and not bars:
            result = failed(len(plans), "REPLAY_CSV_NO_ROWS")
            conn.commit()
            _write_replay_report(report_dir, result, [], invalid_reasons)
            _record_replay_run(db_path, result)
            return result
        active_plans = [plan for plan in plans if plan.is_valid]
        missing_symbols = sorted({plan.ts_code for plan in active_plans} - {bar.ts_code for bar in bars})
        if missing_symbols:
            result = failed(len(plans), "REPLAY_CSV_MISSING_PLAN_SYMBOLS: " + ",".join(missing_symbols))
            conn.commit()
            _write_replay_report(report_dir, result, [], invalid_reasons)
            _record_replay_run(db_path, result)
            return result
        alerts = evaluate_replay(conn, active_plans, bars)
    result = ReplayResult(
        trade_date,
        str(input_path),
        input_sha256,
        len(plans),
        len(alerts),
        "SUCCESS",
        None,
        started_at,
        utc_now_text(),
    )
    _write_replay_report(report_dir, result, alerts, invalid_reasons)
    _record_replay_run(db_path, result)
    return result


def _record_replay_run(db_path: Path, result: ReplayResult) -> None:
    with sqlite3.connect(db_path) as conn:
        conn.execute(
            "INSERT INTO intraday_replay_runs ("
            "trade_date, input_file, input_sha256, plan_count, alert_count, status, "
            "started_at, ended_at, error_message"
            ") VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (
                result.trade_date,
                result.input_file,
                result.input_sha256,
                result.plan_count,
                result.alert_count,
                result.status,
                result.started_at,
                result.ended_at,
                result.error_message,
            ),
        )


def _write_replay_report(
    report_dir: Path,
    result: ReplayResult,
    alerts: Sequence[IntradayAlert],
    invalid_reasons: Sequence[str],
) -> None:
    report_dir.mkdir(parents=True, exist_ok=True)
    lines = [
        f"# Intraday Replay {result.trade_date}",
        "",
        f"- status: {result.status}",
        f"- input_file: {result.input_file}",
        f"- input_sha256: {result.input_sha256}",
        f"- plan_count: {result.plan_count}",
        f"- alert_count: {result.alert_count}",
        "",
    ]
    if result.error_message:
        lines.append(f"error_message: {result.error_message}")
    if result.status == "SUCCESS" and result.plan_count == 0:
        lines.append("今日无 intraday_plans，未执行回放")
    for reason in invalid_reasons:
        lines.append(reason)
    for alert in alerts:
        lines.append(f"- {alert.alert_time} {alert.ts_code} {alert.alert_type} {alert.reason_code}")
    (report_dir / f"{result.trade_date}_replay_report.md").write_text(
        "\n".join(lines) + "\n",
        encoding="utf-8",
    )


def _sha256(path: Path) -> str:
    try:
        return hashlib.sha256(path.read_bytes()).hexdigest()
    except OSError:
        return ""
