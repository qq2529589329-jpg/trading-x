from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import TypedDict
import json
import sqlite3

from trading_x.capabilities import API_DEFINITIONS
from trading_x.candidate_models import CandidateReport
from trading_x.candidate_snapshots import (
    CONFIG_HASH,
    STRATEGY_VERSION,
    THRESHOLD_VERSION,
    CandidateRunRecord,
    new_run_id,
    persist_candidate_run,
)
from trading_x.candidates import select_candidates
from trading_x.data_status import p0_incomplete_reason
from trading_x.market import market_status, report_theme_confidence
from trading_x.report_markdown import render_markdown
from trading_x.report_storage import ReportRecord, persist_report_snapshot
from trading_x.types import Confidence, DataCapabilityLevel


SYSTEM_VERSION = "v1.0"


class CandidateJson(TypedDict):
    ts_code: str
    name: str
    strategy_type: str
    candidate_grade: str
    theme_name: str | None
    theme_tags: str | None
    theme_rank_today: int | None
    theme_strength_score: float | None
    theme_position: str | None
    entry_reason: str
    veto_items: str
    buy_observation: str
    abandon_conditions: str
    max_chase_limit: str
    structural_stop: str
    suggested_position: str
    max_loss: str
    data_confidence: str
    theme_confidence: str
    event_confidence: str
    plan_entry_low: float | None
    plan_entry_high: float | None
    plan_breakout_price: float | None
    plan_stop_price: float | None
    plan_max_position_cash: float | None
    plan_max_loss: float | None


@dataclass(frozen=True, slots=True)
class ReportSnapshot:
    trade_date: str
    system_version: str
    market_status: str
    allow_new_position: bool
    data_capability: DataCapabilityLevel
    available_apis: tuple[str, ...]
    unavailable_apis: tuple[str, ...]
    risk_blocks: tuple[str, ...]
    candidates: list[CandidateReport]
    theme_confidence: Confidence

    def to_json_text(self) -> str:
        return json.dumps(
            {
                "trade_date": self.trade_date,
                "system_version": self.system_version,
                "market_status": self.market_status,
                "allow_new_position": self.allow_new_position,
                "data_capability": self.data_capability,
                "available_apis": list(self.available_apis),
                "unavailable_apis": [
                    {"api_name": api_name, "fallback_mode": _fallback_for(api_name)}
                    for api_name in self.unavailable_apis
                ],
                "theme_confidence": self.theme_confidence,
                "risk_blocks": list(self.risk_blocks),
                "candidates": [_candidate_json(candidate) for candidate in self.candidates],
            },
            ensure_ascii=False,
            sort_keys=True,
            indent=2,
        )


def generate_report(db_path: Path, trade_date: str, report_dir: Path) -> ReportSnapshot:
    report_dir.mkdir(parents=True, exist_ok=True)
    snapshot = _build_snapshot(db_path, trade_date)
    json_text = snapshot.to_json_text()
    json_path = report_dir / f"{trade_date}_report.json"
    md_path = report_dir / f"{trade_date}_report.md"
    json_path.write_text(json_text + "\n", encoding="utf-8")
    md_path.write_text(render_markdown(snapshot), encoding="utf-8")
    persist_report_snapshot(
        db_path,
        ReportRecord(
            trade_date=snapshot.trade_date,
            system_version=snapshot.system_version,
            report_md_path=md_path,
            report_html_path=None,
            report_json_path=json_path,
            report_snapshot_json=json_text,
            data_capability=snapshot.data_capability,
        ),
    )
    theme_coverage_ratio = None
    if snapshot.candidates:
        mapped_count = sum(1 for candidate in snapshot.candidates if candidate.theme_name)
        theme_coverage_ratio = mapped_count / len(snapshot.candidates)
    persist_candidate_run(
        db_path,
        CandidateRunRecord(
            run_id=new_run_id(),
            trade_date=snapshot.trade_date,
            system_version=snapshot.system_version,
            strategy_version=STRATEGY_VERSION,
            threshold_version=THRESHOLD_VERSION,
            config_hash=CONFIG_HASH,
            data_capability=snapshot.data_capability.value,
            p0_complete=snapshot.data_capability != DataCapabilityLevel.DEGRADED,
            theme_coverage_ratio=theme_coverage_ratio,
            generated_at=datetime.now(UTC).isoformat(),
            report_json_path=json_path,
            report_md_path=md_path,
            notes=None,
        ),
        snapshot.candidates,
    )
    return snapshot


def _build_snapshot(db_path: Path, trade_date: str) -> ReportSnapshot:
    available, unavailable = _capability_sets(db_path)
    incomplete_reason = p0_incomplete_reason(db_path, trade_date)
    if incomplete_reason is not None:
        return ReportSnapshot(
            trade_date=trade_date,
            system_version=SYSTEM_VERSION,
            market_status=market_status(DataCapabilityLevel.DEGRADED, []),
            allow_new_position=False,
            data_capability=DataCapabilityLevel.DEGRADED,
            available_apis=tuple(sorted(available)),
            unavailable_apis=tuple(sorted(unavailable)),
            risk_blocks=(f"P0 数据不完整：{incomplete_reason}；禁止新开仓。",),
            candidates=[],
            theme_confidence=Confidence.UNAVAILABLE,
        )
    level = _level_from_sets(unavailable)
    if (
        level == DataCapabilityLevel.BASIC
        and "limit_cpt_list" in unavailable
        and _has_theme_fallback(db_path, trade_date)
    ):
        level = DataCapabilityLevel.BASIC_WITH_THEME_FALLBACK
    candidates = select_candidates(db_path, trade_date, level, unavailable)
    risk_blocks = _risk_blocks(level, unavailable)
    return ReportSnapshot(
        trade_date=trade_date,
        system_version=SYSTEM_VERSION,
        market_status=market_status(level, candidates),
        allow_new_position=bool(candidates) and level != DataCapabilityLevel.DEGRADED,
        data_capability=level,
        available_apis=tuple(sorted(available)),
        unavailable_apis=tuple(sorted(unavailable)),
        risk_blocks=tuple(risk_blocks),
        candidates=candidates,
        theme_confidence=report_theme_confidence(candidates, unavailable),
    )


def _capability_sets(db_path: Path) -> tuple[set[str], set[str]]:
    with sqlite3.connect(db_path) as conn:
        rows = conn.execute("SELECT api_name, available FROM data_capabilities").fetchall()
    if not rows:
        return set(), {definition.name for definition in API_DEFINITIONS}
    available = {row[0] for row in rows if row[1] == 1}
    unavailable = {row[0] for row in rows if row[1] == 0}
    return available, unavailable


def _level_from_sets(unavailable: set[str]) -> DataCapabilityLevel:
    p0 = {definition.name for definition in API_DEFINITIONS if definition.tier == "P0"}
    p1 = {definition.name for definition in API_DEFINITIONS if definition.tier == "P1"}
    if unavailable & p0:
        return DataCapabilityLevel.DEGRADED
    if unavailable & p1:
        return DataCapabilityLevel.BASIC
    return DataCapabilityLevel.FULL


def _risk_blocks(level: DataCapabilityLevel, unavailable: set[str]) -> list[str]:
    if level == DataCapabilityLevel.DEGRADED:
        missing = ", ".join(sorted(unavailable)) if unavailable else "P0"
        return [f"P0 数据缺失：{missing}；禁止新开仓。"]
    p1_missing = sorted(
        definition.name
        for definition in API_DEFINITIONS
        if definition.tier == "P1" and definition.name in unavailable
    )
    if p1_missing:
        if level == DataCapabilityLevel.BASIC_WITH_THEME_FALLBACK:
            return [f"P1 数据缺失：{', '.join(p1_missing)}；使用本地题材 fallback。"]
        return [f"P1 数据缺失：{', '.join(p1_missing)}；候选置信度降低。"]
    return []


def _fallback_for(api_name: str) -> str:
    for definition in API_DEFINITIONS:
        if definition.name == api_name:
            return definition.fallback_mode
    return "optional_unavailable"


def _candidate_json(candidate: CandidateReport) -> CandidateJson:
    return {
        "ts_code": candidate.ts_code,
        "name": candidate.name,
        "strategy_type": candidate.strategy_type,
        "candidate_grade": candidate.candidate_grade,
        "theme_name": candidate.theme_name,
        "theme_tags": candidate.theme_tags,
        "theme_rank_today": candidate.theme_rank_today,
        "theme_strength_score": candidate.theme_strength_score,
        "theme_position": candidate.theme_position,
        "entry_reason": candidate.entry_reason,
        "veto_items": candidate.veto_items,
        "buy_observation": candidate.buy_observation,
        "abandon_conditions": candidate.abandon_conditions,
        "max_chase_limit": candidate.max_chase_limit,
        "structural_stop": candidate.structural_stop,
        "suggested_position": candidate.suggested_position,
        "max_loss": candidate.max_loss,
        "data_confidence": candidate.data_confidence,
        "theme_confidence": candidate.theme_confidence,
        "event_confidence": candidate.event_confidence,
        "plan_entry_low": candidate.plan_entry_low,
        "plan_entry_high": candidate.plan_entry_high,
        "plan_breakout_price": candidate.plan_breakout_price,
        "plan_stop_price": candidate.plan_stop_price,
        "plan_max_position_cash": candidate.plan_max_position_cash,
        "plan_max_loss": candidate.plan_max_loss,
    }


def _has_theme_fallback(db_path: Path, trade_date: str) -> bool:
    with sqlite3.connect(db_path) as conn:
        row = conn.execute(
            "SELECT 1 FROM theme_daily_strength WHERE trade_date = ? LIMIT 1",
            (trade_date,),
        ).fetchone()
    return row is not None
