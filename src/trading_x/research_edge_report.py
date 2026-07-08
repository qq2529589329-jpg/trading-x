from dataclasses import dataclass
from pathlib import Path
from typing import Final

HORIZONS: Final = (1, 3, 5, 10)
A_GAP_REASON: Final = "A_GAP_CONTINUATION_CANDIDATE"
STABLE_MONTH_MIN_SAMPLES: Final = 5


@dataclass(frozen=True, slots=True)
class ReturnStat:
    bucket: str
    horizon: int
    sample_count: int
    avg_return: float
    median_return: float
    win_rate: float


@dataclass(frozen=True, slots=True)
class EdgeReport:
    run_id: str
    trade_overall: list[ReturnStat]
    benchmark_overall: list[ReturnStat]
    by_year: tuple[ReturnStat, ...]
    by_regime: tuple[ReturnStat, ...]
    benchmark_by_reason: tuple[ReturnStat, ...]
    benchmark_by_reason_year: tuple[ReturnStat, ...]
    benchmark_by_reason_month: tuple[ReturnStat, ...]
    benchmark_by_reason_regime: tuple[ReturnStat, ...]


def write_edge_report(report_path: Path, report: EdgeReport) -> None:
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
    lines.extend(_gap_month_stability_section(report.benchmark_by_reason_month))
    report_path.write_text("\n".join(lines) + "\n", encoding="utf-8")


def _overall_lines(trade_overall: list[ReturnStat], benchmark_overall: list[ReturnStat]) -> list[str]:
    lines: list[str] = []
    for trade, benchmark in zip(trade_overall, benchmark_overall, strict=True):
        lines.append(
            f"| {trade.horizon} | {trade.sample_count} | {_pct(trade.avg_return)} | "
            f"{_pct(trade.median_return)} | {benchmark.sample_count} | {_pct(benchmark.avg_return)} | "
            f"{_pct(trade.avg_return - benchmark.avg_return)} |"
        )
    return lines


def _stats_section(title: str, rows: tuple[ReturnStat, ...]) -> list[str]:
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


def _gap_month_stability_section(rows: tuple[ReturnStat, ...]) -> list[str]:
    prefix = f"{A_GAP_REASON} / "
    by_month: dict[str, dict[int, ReturnStat]] = {}
    for row in rows:
        if not row.bucket.startswith(prefix):
            continue
        month = row.bucket.removeprefix(prefix)
        by_month.setdefault(month, {})[row.horizon] = row
    lines = [
        "",
        "## A_GAP month stability",
        "",
        "| month | horizons | min_n | avg_pos | median_pos | sampled | stable |",
        "|---|---|---:|---:|---:|---:|---:|",
    ]
    for month, stats in sorted(by_month.items()):
        present = tuple(horizon for horizon in HORIZONS if horizon in stats)
        min_n = min(stats[horizon].sample_count for horizon in present) if present else 0
        avg_pos = bool(present) and all(stats[horizon].avg_return > 0 for horizon in present)
        median_pos = bool(present) and all(stats[horizon].median_return > 0 for horizon in present)
        sampled = len(present) == len(HORIZONS) and min_n >= STABLE_MONTH_MIN_SAMPLES
        stable = sampled and avg_pos and median_pos
        lines.append(
            f"| {month} | {'/'.join(str(horizon) for horizon in present)} | {min_n} | "
            f"{int(avg_pos)} | {int(median_pos)} | {int(sampled)} | {int(stable)} |"
        )
    return lines


def _pct(value: float) -> str:
    return f"{value:.4%}"
