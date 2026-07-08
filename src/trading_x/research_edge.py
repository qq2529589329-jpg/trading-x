from dataclasses import dataclass
from pathlib import Path
import sqlite3
from typing import Final, Literal, assert_never

from trading_x.research_backtest_audit import BacktestAuditUnavailableError
from trading_x.research_models import ResearchEdgeRequest, ResearchEdgeResult

HORIZONS: Final = (1, 3, 5, 10)
Source = Literal["trade", "benchmark"]
Segment = Literal["overall", "year", "regime", "reason", "reason_year", "reason_month", "reason_regime"]

TRADE_SEGMENT_EXPR: Final = {
    "overall": "'ALL'",
    "year": "substr(t.signal_date, 1, 4)",
    "regime": "COALESCE(mr.market_regime, 'UNKNOWN')",
    "reason": "t.reason_code",
    "reason_year": "t.reason_code || ' / ' || substr(t.signal_date, 1, 4)",
    "reason_month": "t.reason_code || ' / ' || substr(t.signal_date, 1, 6)",
    "reason_regime": "t.reason_code || ' / ' || COALESCE(mr.market_regime, 'UNKNOWN')",
}
BENCHMARK_SEGMENT_EXPR: Final = {
    "overall": "'ALL'",
    "year": "substr(o.signal_date, 1, 4)",
    "regime": "COALESCE(mr.market_regime, 'UNKNOWN')",
    "reason": "o.reason_code",
    "reason_year": "o.reason_code || ' / ' || substr(o.signal_date, 1, 4)",
    "reason_month": "o.reason_code || ' / ' || substr(o.signal_date, 1, 6)",
    "reason_regime": "o.reason_code || ' / ' || COALESCE(mr.market_regime, 'UNKNOWN')",
}


@dataclass(frozen=True, slots=True)
class _EdgeQuery:
    run_id: str
    source: Source
    horizon: int
    segment: Segment


@dataclass(frozen=True, slots=True)
class _ReturnStat:
    bucket: str
    horizon: int
    sample_count: int
    avg_return: float
    median_return: float
    win_rate: float


@dataclass(frozen=True, slots=True)
class _EdgeReport:
    run_id: str
    trade_overall: list[_ReturnStat]
    benchmark_overall: list[_ReturnStat]
    by_year: tuple[_ReturnStat, ...]
    by_regime: tuple[_ReturnStat, ...]
    benchmark_by_reason: tuple[_ReturnStat, ...]
    benchmark_by_reason_year: tuple[_ReturnStat, ...]
    benchmark_by_reason_month: tuple[_ReturnStat, ...]
    benchmark_by_reason_regime: tuple[_ReturnStat, ...]


def analyze_research_edge(db_path: Path, request: ResearchEdgeRequest) -> ResearchEdgeResult:
    with sqlite3.connect(db_path) as conn:
        run_id = request.run_id if request.run_id is not None else _latest_run_id(conn)
        trade_overall = [_single_stat(conn, _EdgeQuery(run_id, "trade", horizon, "overall")) for horizon in HORIZONS]
        benchmark_overall = [
            _single_stat(conn, _EdgeQuery(run_id, "benchmark", horizon, "overall")) for horizon in HORIZONS
        ]
        report = _EdgeReport(
            run_id,
            trade_overall,
            benchmark_overall,
            _segmented_stats(conn, run_id, "year"),
            _segmented_stats(conn, run_id, "regime"),
            _benchmark_stats(conn, run_id, "reason"),
            _benchmark_stats(conn, run_id, "reason_year"),
            _benchmark_stats(conn, run_id, "reason_month"),
            _benchmark_stats(conn, run_id, "reason_regime"),
        )
    report_path = request.report_dir / "edge_report.md"
    _write_report(report_path, report)
    return ResearchEdgeResult(
        run_id,
        report_path,
        trade_overall[0].sample_count,
        benchmark_overall[0].sample_count,
    )


def _latest_run_id(conn: sqlite3.Connection) -> str:
    row = conn.execute("SELECT run_id FROM backtest_results ORDER BY created_at DESC LIMIT 1").fetchone()
    if row is None:
        raise BacktestAuditUnavailableError("no backtest_results run found")
    return str(row[0])


def _single_stat(conn: sqlite3.Connection, query: _EdgeQuery) -> _ReturnStat:
    stats = _stats(conn, query)
    if stats:
        return stats[0]
    return _ReturnStat("ALL", query.horizon, 0, 0.0, 0.0, 0.0)


def _segmented_stats(conn: sqlite3.Connection, run_id: str, segment: Segment) -> tuple[_ReturnStat, ...]:
    rows: list[_ReturnStat] = []
    for horizon in HORIZONS:
        rows.extend(_stats(conn, _EdgeQuery(run_id, "trade", horizon, segment)))
    return tuple(rows)


def _benchmark_stats(conn: sqlite3.Connection, run_id: str, segment: Segment) -> tuple[_ReturnStat, ...]:
    rows: list[_ReturnStat] = []
    for horizon in HORIZONS:
        rows.extend(_stats(conn, _EdgeQuery(run_id, "benchmark", horizon, segment)))
    return tuple(rows)


def _stats(conn: sqlite3.Connection, query: _EdgeQuery) -> tuple[_ReturnStat, ...]:
    values_by_bucket: dict[str, list[float]] = {}
    for bucket, value in _return_rows(conn, query):
        values_by_bucket.setdefault(bucket, []).append(value)
    return tuple(_stat(bucket, query.horizon, values) for bucket, values in sorted(values_by_bucket.items()))


def _return_rows(conn: sqlite3.Connection, query: _EdgeQuery) -> list[tuple[str, float]]:
    match query.source:
        case "trade":
            return _trade_return_rows(conn, query)
        case "benchmark":
            return _benchmark_return_rows(conn, query)
        case unreachable:
            assert_never(unreachable)


def _trade_return_rows(conn: sqlite3.Connection, query: _EdgeQuery) -> list[tuple[str, float]]:
    bucket_expr = TRADE_SEGMENT_EXPR[query.segment]
    return [
        (str(row[0]), float(row[1]))
        for row in conn.execute(
            f"SELECT {bucket_expr} AS bucket, (future.close - t.price) / t.price AS return_value "
            "FROM backtest_trades t "
            "LEFT JOIN market_regimes mr ON mr.trade_date = t.signal_date "
            "JOIN daily_quotes future ON future.ts_code = t.ts_code AND future.trade_date = ("
            "SELECT q.trade_date FROM daily_quotes q WHERE q.ts_code = t.ts_code "
            "AND q.trade_date > t.trade_date ORDER BY q.trade_date LIMIT 1 OFFSET ?) "
            "WHERE t.run_id = ? AND t.reason_code = 'BUY_FILLED' AND t.price > 0",
            (query.horizon - 1, query.run_id),
        ).fetchall()
    ]


def _benchmark_return_rows(conn: sqlite3.Connection, query: _EdgeQuery) -> list[tuple[str, float]]:
    bucket_expr = BENCHMARK_SEGMENT_EXPR[query.segment]
    return [
        (str(row[0]), float(row[1]))
        for row in conn.execute(
            f"SELECT {bucket_expr} AS bucket, (future.close - entry.close) / entry.close AS return_value "
            "FROM backtest_orders o "
            "LEFT JOIN market_regimes mr ON mr.trade_date = o.signal_date "
            "JOIN daily_quotes entry ON entry.trade_date = o.trade_date AND entry.ts_code = o.ts_code "
            "JOIN daily_quotes future ON future.ts_code = o.ts_code AND future.trade_date = ("
            "SELECT q.trade_date FROM daily_quotes q WHERE q.ts_code = o.ts_code "
            "AND q.trade_date > o.trade_date ORDER BY q.trade_date LIMIT 1 OFFSET ?) "
            "WHERE o.run_id = ? AND entry.close > 0",
            (query.horizon - 1, query.run_id),
        ).fetchall()
    ]


def _stat(bucket: str, horizon: int, values: list[float]) -> _ReturnStat:
    return _ReturnStat(
        bucket,
        horizon,
        len(values),
        sum(values) / len(values),
        _median(values),
        sum(1 for value in values if value > 0) / len(values),
    )


def _median(values: list[float]) -> float:
    sorted_values = sorted(values)
    middle = len(sorted_values) // 2
    if len(sorted_values) % 2 == 1:
        return sorted_values[middle]
    return (sorted_values[middle - 1] + sorted_values[middle]) / 2


def _write_report(report_path: Path, report: _EdgeReport) -> None:
    report_path.parent.mkdir(parents=True, exist_ok=True)
    lines = [
        "# Research Edge Report",
        "",
        f"- run_id: {report.run_id}",
        "- buy_filled_return: fill price to future close",
        "- benchmark_return: all backtest orders, entry close to future close",
        "",
        "## Overall",
        "",
        "| horizon | buy_n | buy_avg | buy_median | benchmark_n | benchmark_avg | excess_avg |",
        "|---:|---:|---:|---:|---:|---:|---:|",
    ]
    lines.extend(_overall_lines(report.trade_overall, report.benchmark_overall))
    lines.extend(_stats_section("BUY_FILLED by year", report.by_year))
    lines.extend(_stats_section("BUY_FILLED by regime", report.by_regime))
    lines.extend(_stats_section("Benchmark by reason", report.benchmark_by_reason))
    lines.extend(_stats_section("Benchmark by reason/year", report.benchmark_by_reason_year))
    lines.extend(_stats_section("Benchmark by reason/month", report.benchmark_by_reason_month))
    lines.extend(_stats_section("Benchmark by reason/regime", report.benchmark_by_reason_regime))
    report_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _overall_lines(trade_overall: list[_ReturnStat], benchmark_overall: list[_ReturnStat]) -> list[str]:
    lines: list[str] = []
    for trade, benchmark in zip(trade_overall, benchmark_overall, strict=True):
        lines.append(
            f"| {trade.horizon} | {trade.sample_count} | {_pct(trade.avg_return)} | "
            f"{_pct(trade.median_return)} | {benchmark.sample_count} | {_pct(benchmark.avg_return)} | "
            f"{_pct(trade.avg_return - benchmark.avg_return)} |"
        )
    return lines


def _stats_section(title: str, rows: tuple[_ReturnStat, ...]) -> list[str]:
    lines = [
        "",
        f"## {title}",
        "",
        "| horizon | bucket | n | avg | median | win_rate |",
        "|---:|---|---:|---:|---:|---:|",
    ]
    lines.extend(
        f"| {row.horizon} | {row.bucket} | {row.sample_count} | {_pct(row.avg_return)} | "
        f"{_pct(row.median_return)} | {_pct(row.win_rate)} |"
        for row in rows
    )
    return lines


def _pct(value: float) -> str:
    return f"{value:.4%}"