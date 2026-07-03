from collections.abc import Mapping
from collections.abc import Sequence
from pathlib import Path
import csv
import sqlite3

from trading_x.theme_models import (
    REQUIRED_COLUMNS,
    THEME_TIER_WEIGHTS,
    ThemeAggregate,
    ThemeCsvError,
    ThemeImportResult,
    ThemeMember,
    ThemeMissingExportRequest,
)
from trading_x.theme_coverage import export_missing_theme_candidates, theme_coverage
from trading_x.theme_scoring import strength_scores
from trading_x.theme_storage import persist_theme_members
from trading_x.types import Confidence


__all__ = (
    "ThemeCsvError",
    "ThemeMissingExportRequest",
    "export_missing_theme_candidates",
    "import_theme_members",
    "refresh_theme_daily_strength",
    "theme_coverage",
)


def import_theme_members(db_path: Path, csv_path: Path) -> ThemeImportResult:
    members: list[ThemeMember] = []
    seen: set[str] = set()
    duplicates = 0
    with csv_path.open(encoding="utf-8", newline="") as file:
        reader = csv.DictReader(file)
        _ensure_columns(reader.fieldnames)
        for row_number, row in enumerate(reader, start=2):
            member = _parse_member(row_number, row)
            duplicates += int(member.ts_code in seen)
            seen.add(member.ts_code)
            members.append(member)
    persist_theme_members(db_path, members)
    return ThemeImportResult(
        imported_count=len(members),
        failed_count=0,
        duplicate_count=duplicates,
    )


def refresh_theme_daily_strength(db_path: Path, trade_date: str) -> int:
    with sqlite3.connect(db_path) as conn:
        aggregates = _load_aggregates(conn, trade_date)
        scores = strength_scores(aggregates)
        conn.execute("DELETE FROM theme_daily_strength WHERE trade_date = ?", (trade_date,))
        conn.executemany(
            "INSERT INTO theme_daily_strength ("
            "trade_date, theme_name, theme_member_count, theme_up_count, "
            "theme_limit_up_count, theme_avg_pct_chg, theme_total_amount, "
            "theme_candidate_count, theme_strength_score, theme_confidence, core_symbols, "
            "weighted_limit_up_count, weighted_avg_pct_chg, weighted_total_amount"
            ") VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            [
                (
                    trade_date,
                    item.theme_name,
                    item.member_count,
                    item.up_count,
                    item.limit_up_count,
                    item.avg_pct_chg,
                    item.total_amount,
                    item.candidate_count,
                    scores[item.theme_name],
                    item.confidence,
                    item.core_symbols,
                    item.weighted_limit_up_count,
                    item.weighted_avg_pct_chg,
                    item.weighted_total_amount,
                )
                for item in aggregates
            ],
        )
    return len(aggregates)


def _ensure_columns(fieldnames: Sequence[str] | None) -> None:
    fields = set(fieldnames or [])
    for column in REQUIRED_COLUMNS:
        if column not in fields:
            raise ThemeCsvError(row_number=1, field=column, reason="missing")


def _parse_member(row_number: int, row: Mapping[str, str]) -> ThemeMember:
    ts_code = row["ts_code"].strip()
    theme_primary = row["theme_primary"].strip()
    confidence = row["confidence"].strip() or Confidence.LOW
    theme_tier = (row.get("theme_tier") or "IMPORTANT").strip() or "IMPORTANT"
    if ts_code == "":
        raise ThemeCsvError(row_number=row_number, field="ts_code", reason="is empty")
    if theme_primary == "":
        raise ThemeCsvError(row_number=row_number, field="theme_primary", reason="is empty")
    if theme_tier not in THEME_TIER_WEIGHTS:
        raise ThemeCsvError(row_number=row_number, field="theme_tier", reason=f"{theme_tier} is invalid")
    try:
        parsed_confidence = Confidence(confidence)
    except ValueError as exc:
        raise ThemeCsvError(
            row_number=row_number,
            field="confidence",
            reason=f"{confidence} is invalid",
        ) from exc
    theme_weight = _theme_weight(row_number, row, theme_tier)
    return ThemeMember(
        ts_code=ts_code,
        name=row["name"].strip(),
        industry=row["industry"].strip(),
        theme_primary=theme_primary,
        theme_tags=row["theme_tags"].strip(),
        theme_tier=theme_tier,
        theme_weight=theme_weight,
        theme_source=row["theme_source"].strip() or "manual",
        confidence=parsed_confidence,
        updated_at=row["updated_at"].strip(),
        notes=row["notes"].strip(),
    )


def _theme_weight(row_number: int, row: Mapping[str, str], theme_tier: str) -> float:
    raw_weight = (row.get("theme_weight") or "").strip()
    if raw_weight == "":
        return THEME_TIER_WEIGHTS[theme_tier]
    try:
        weight = float(raw_weight)
    except ValueError as exc:
        raise ThemeCsvError(row_number=row_number, field="theme_weight", reason=f"{raw_weight} is invalid") from exc
    if weight <= 0:
        raise ThemeCsvError(row_number=row_number, field="theme_weight", reason="must be positive")
    return weight


def _load_aggregates(conn: sqlite3.Connection, trade_date: str) -> list[ThemeAggregate]:
    rows = conn.execute(
        "SELECT m.theme_primary, COUNT(*), "
        "SUM(CASE WHEN d.pct_chg > 0 THEN 1 ELSE 0 END), "
        "SUM(CASE WHEN l.up_limit > 0 AND d.close >= l.up_limit - 0.001 THEN 1 ELSE 0 END), "
        "AVG(d.pct_chg), SUM(d.amount), "
        "SUM(CASE WHEN c.ts_code IS NULL THEN 0 ELSE 1 END), "
        "MAX(CASE m.confidence WHEN 'HIGH' THEN 3 WHEN 'MEDIUM' THEN 2 ELSE 1 END), "
        "SUM(CASE WHEN l.up_limit > 0 AND d.close >= l.up_limit - 0.001 THEN m.theme_weight ELSE 0 END), "
        "SUM(d.pct_chg * m.theme_weight) / NULLIF(SUM(m.theme_weight), 0), "
        "SUM(d.amount * m.theme_weight) "
        "FROM theme_members m "
        "JOIN stock_universe s ON s.ts_code = m.ts_code "
        "JOIN daily_quotes d ON d.ts_code = m.ts_code AND d.trade_date = ? "
        "LEFT JOIN stk_limit_prices l ON l.ts_code = m.ts_code AND l.trade_date = ? "
        "LEFT JOIN (SELECT DISTINCT ts_code FROM candidates WHERE trade_date = ?) c "
        "ON c.ts_code = m.ts_code "
        "WHERE s.included = 1 "
        "GROUP BY m.theme_primary",
        (trade_date, trade_date, trade_date),
    ).fetchall()
    return [
        ThemeAggregate(
            theme_name=row[0],
            member_count=row[1],
            up_count=row[2] or 0,
            limit_up_count=row[3] or 0,
            avg_pct_chg=row[4] or 0.0,
            total_amount=row[5] or 0.0,
            candidate_count=row[6] or 0,
            confidence=_theme_confidence(row[1], row[7] or 1),
            core_symbols=_core_symbols(conn, trade_date, row[0]),
            weighted_limit_up_count=row[8] or 0.0,
            weighted_avg_pct_chg=row[9] or 0.0,
            weighted_total_amount=row[10] or 0.0,
        )
        for row in rows
    ]


def _core_symbols(conn: sqlite3.Connection, trade_date: str, theme_name: str) -> str:
    rows = conn.execute(
        "SELECT m.ts_code FROM theme_members m "
        "JOIN daily_quotes d ON d.ts_code = m.ts_code AND d.trade_date = ? "
        "WHERE m.theme_primary = ? "
        "ORDER BY m.theme_weight DESC, d.amount DESC, d.pct_chg DESC LIMIT 5",
        (trade_date, theme_name),
    ).fetchall()
    return ";".join(row[0] for row in rows)


def _theme_confidence(member_count: int, confidence_rank: int) -> str:
    if confidence_rank >= 3:
        return Confidence.HIGH
    if confidence_rank >= 2:
        return Confidence.MEDIUM
    return Confidence.LOW
