from dataclasses import dataclass
from pathlib import Path
from typing import Final
import json
import os
import sqlite3

from trading_x.config import load_tushare_token


MIN_ACCEPTANCE_DAYS: Final = 10
P0_TABLES: Final = ("daily_quotes", "daily_basic", "stk_limit_prices")
REQUIRED_CANDIDATE_FIELDS: Final = (
    "strategy_type",
    "candidate_grade",
    "entry_reason",
    "veto_items",
    "buy_observation",
    "abandon_conditions",
    "max_chase_limit",
    "structural_stop",
    "suggested_position",
    "max_loss",
    "data_confidence",
    "theme_confidence",
    "event_confidence",
)
DUPLICATE_CHECKS: Final = (
    ("daily_quotes", "trade_date, ts_code"),
    ("daily_basic", "trade_date, ts_code"),
    ("stk_limit_prices", "trade_date, ts_code"),
    ("candidates", "trade_date, ts_code, strategy_type"),
    ("reports", "trade_date"),
)


@dataclass(frozen=True, slots=True)
class AcceptanceResult:
    checked_days: int
    failures: tuple[str, ...]

    @property
    def passed(self) -> bool:
        return not self.failures


@dataclass(frozen=True, slots=True)
class AcceptanceContext:
    conn: sqlite3.Connection
    report_dir: Path
    token: str | None


@dataclass(frozen=True, slots=True)
class IncompleteReport:
    trade_date: str
    reasons: tuple[str, ...]


def run_acceptance(db_path: Path, report_dir: Path, dates: list[str]) -> AcceptanceResult:
    failures: list[str] = []
    if len(dates) < MIN_ACCEPTANCE_DAYS:
        failures.append("至少需要 10 个交易日。")
    token = load_tushare_token(env_value=os.environ.get("TUSHARE_TOKEN"))
    with sqlite3.connect(db_path) as conn:
        context = AcceptanceContext(conn=conn, report_dir=report_dir, token=token)
        if _count(conn, "stock_universe") == 0:
            failures.append("stock_universe 为空。")
        for table, columns in DUPLICATE_CHECKS:
            if _duplicate_count(conn, table, columns) > 0:
                failures.append(f"{table} 存在重复脏数据。")
        for trade_date in dates:
            _check_trade_date(context, trade_date, failures)
    return AcceptanceResult(checked_days=len(dates), failures=tuple(failures))


def recent_report_dates(db_path: Path, limit: int) -> list[str]:
    with sqlite3.connect(db_path) as conn:
        rows = conn.execute(
            "SELECT trade_date FROM reports ORDER BY trade_date DESC LIMIT ?",
            (limit,),
        ).fetchall()
    return [row[0] for row in reversed(rows)]


def recent_complete_report_dates(db_path: Path, report_dir: Path, limit: int) -> list[str]:
    if limit <= 0:
        return []
    dates: list[str] = []
    with sqlite3.connect(db_path) as conn:
        rows = conn.execute("SELECT trade_date FROM reports ORDER BY trade_date DESC").fetchall()
        for row in rows:
            trade_date = row[0]
            if _has_complete_report_date(conn, report_dir, trade_date):
                dates.append(trade_date)
            if len(dates) == limit:
                break
    return list(reversed(dates))


def incomplete_reports(db_path: Path, report_dir: Path) -> list[IncompleteReport]:
    reports: list[IncompleteReport] = []
    with sqlite3.connect(db_path) as conn:
        rows = conn.execute("SELECT trade_date FROM reports ORDER BY trade_date").fetchall()
        for row in rows:
            trade_date = row[0]
            reasons = _incomplete_report_reasons(conn, report_dir, trade_date)
            if reasons:
                reports.append(IncompleteReport(trade_date=trade_date, reasons=tuple(reasons)))
    return reports


def _check_trade_date(
    context: AcceptanceContext,
    trade_date: str,
    failures: list[str],
) -> None:
    for table in P0_TABLES:
        if _date_count(context.conn, table, trade_date) == 0:
            failures.append(f"{trade_date}: {table} 缺失。")
    row = context.conn.execute(
        "SELECT report_snapshot_json FROM reports WHERE trade_date = ?",
        (trade_date,),
    ).fetchone()
    if row is None:
        failures.append(f"{trade_date}: reports 快照缺失。")
        return
    json_path = context.report_dir / f"{trade_date}_report.json"
    md_path = context.report_dir / f"{trade_date}_report.md"
    if not json_path.exists():
        failures.append(f"{trade_date}: JSON 报告缺失。")
        return
    if not md_path.exists():
        failures.append(f"{trade_date}: Markdown 报告缺失。")
        return
    json_text = json_path.read_text(encoding="utf-8")
    markdown = md_path.read_text(encoding="utf-8")
    token_leak = _token_leak_failure(trade_date, context.token, json_text + markdown + (row[0] or ""))
    if token_leak is not None:
        failures.append(token_leak)
    try:
        payload = json.loads(json_text)
        snapshot = json.loads(row[0])
    except json.JSONDecodeError as exc:
        failures.append(f"{trade_date}: JSON 无法解析：{exc.msg}。")
        return
    if snapshot != payload:
        failures.append(f"{trade_date}: reports.report_snapshot_json 与 JSON 文件不一致。")
    if not isinstance(payload, dict):
        failures.append(f"{trade_date}: JSON 顶层结构不是对象。")
        return
    failures.extend(_payload_failures(trade_date, payload, markdown))


def _payload_failures(
    trade_date: str,
    payload,
    markdown: str,
) -> tuple[str, ...]:
    failures: list[str] = []
    if not payload.get("market_status"):
        failures.append(f"{trade_date}: 缺少市场状态。")
    if "allow_new_position" not in payload:
        failures.append(f"{trade_date}: 缺少允许/禁止结论。")
    candidates = payload.get("candidates")
    if not isinstance(candidates, list):
        failures.append(f"{trade_date}: candidates 不是列表。")
        return tuple(failures)
    if len(candidates) > 5:
        failures.append(f"{trade_date}: 候选数量超过 5。")
    if payload.get("data_capability") == "DEGRADED" and candidates:
        failures.append(f"{trade_date}: P0 缺失时生成了候选。")
    if not candidates and "今日无符合纪律候选" not in markdown:
        failures.append(f"{trade_date}: 无候选时未说明禁买原因。")
    if "交易结论：" not in markdown:
        failures.append(f"{trade_date}: Markdown 缺少交易结论。")
    for candidate in candidates:
        if not isinstance(candidate, dict):
            failures.append(f"{trade_date}: candidate 结构不是对象。")
            continue
        for field in REQUIRED_CANDIDATE_FIELDS:
            if not candidate.get(field):
                failures.append(f"{trade_date}: 候选缺少 {field}。")
    return tuple(failures)


def _token_leak_failure(
    trade_date: str,
    token: str | None,
    report_text: str,
) -> str | None:
    if token and token in report_text:
        return f"{trade_date}: 报告疑似泄露 TUSHARE_TOKEN。"
    return None


def _has_complete_report_date(conn: sqlite3.Connection, report_dir: Path, trade_date: str) -> bool:
    return not _incomplete_report_reasons(conn, report_dir, trade_date)


def _incomplete_report_reasons(conn: sqlite3.Connection, report_dir: Path, trade_date: str) -> list[str]:
    reasons = [table for table in P0_TABLES if _date_count(conn, table, trade_date) == 0]
    if not (report_dir / f"{trade_date}_report.json").exists():
        reasons.append("report_json")
    if not (report_dir / f"{trade_date}_report.md").exists():
        reasons.append("report_markdown")
    return reasons


def _count(conn: sqlite3.Connection, table: str) -> int:
    return int(conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0])


def _date_count(conn: sqlite3.Connection, table: str, trade_date: str) -> int:
    return int(
        conn.execute(
            f"SELECT COUNT(*) FROM {table} WHERE trade_date = ?",
            (trade_date,),
        ).fetchone()[0]
    )


def _duplicate_count(conn: sqlite3.Connection, table: str, columns: str) -> int:
    return int(
        conn.execute(
            f"SELECT COUNT(*) FROM ("
            f"SELECT {columns}, COUNT(*) AS row_count FROM {table} "
            f"GROUP BY {columns} HAVING row_count > 1"
            ")"
        ).fetchone()[0]
    )
