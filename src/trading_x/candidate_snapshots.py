from dataclasses import dataclass
from pathlib import Path
from typing import Final, Sequence
from uuid import uuid4
import hashlib
import json
import sqlite3

from trading_x.candidate_models import CandidateReport


STRATEGY_VERSION: Final = "rules-v1"
THRESHOLD_VERSION: Final = "threshold-v1"
CONFIG_HASH: Final = hashlib.sha256(
    f"{STRATEGY_VERSION}|{THRESHOLD_VERSION}".encode()
).hexdigest()[:16]


@dataclass(frozen=True, slots=True)
class CandidateRunRecord:
    run_id: str
    trade_date: str
    system_version: str
    strategy_version: str
    threshold_version: str
    config_hash: str
    data_capability: str
    p0_complete: bool
    theme_coverage_ratio: float | None
    generated_at: str
    report_json_path: Path
    report_md_path: Path
    notes: str | None


def new_run_id() -> str:
    return uuid4().hex


def persist_candidate_run(
    db_path: Path,
    run: CandidateRunRecord,
    candidates: Sequence[CandidateReport],
) -> None:
    with sqlite3.connect(db_path) as conn:
        conn.execute(
            "INSERT INTO candidate_runs ("
            "run_id, trade_date, system_version, strategy_version, threshold_version, "
            "config_hash, data_capability, p0_complete, theme_coverage_ratio, generated_at, "
            "report_json_path, report_md_path, notes"
            ") VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            (
                run.run_id,
                run.trade_date,
                run.system_version,
                run.strategy_version,
                run.threshold_version,
                run.config_hash,
                run.data_capability,
                int(run.p0_complete),
                run.theme_coverage_ratio,
                run.generated_at,
                str(run.report_json_path),
                str(run.report_md_path),
                run.notes,
            ),
        )
        conn.executemany(
            "INSERT INTO candidate_snapshots ("
            "run_id, trade_date, rank, ts_code, name, strategy_type, leader_status, "
            "theme_name, theme_confidence, theme_strength_score, data_capability, "
            "entry_low, entry_high, stop_price, breakout_price, max_position_cash, max_loss, "
            "include_reasons_json, reject_reasons_json, plan_json, created_at"
            ") VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            [
                (
                    run.run_id,
                    run.trade_date,
                    rank,
                    candidate.ts_code,
                    candidate.name,
                    candidate.strategy_type,
                    candidate.candidate_grade,
                    candidate.theme_name,
                    candidate.theme_confidence,
                    candidate.theme_strength_score,
                    run.data_capability,
                    candidate.plan_entry_low,
                    candidate.plan_entry_high,
                    candidate.plan_stop_price,
                    candidate.plan_breakout_price,
                    candidate.plan_max_position_cash,
                    candidate.plan_max_loss,
                    json.dumps([candidate.entry_reason], ensure_ascii=False),
                    json.dumps([candidate.veto_items], ensure_ascii=False),
                    json.dumps(
                        {
                            "entry_low": candidate.plan_entry_low,
                            "entry_high": candidate.plan_entry_high,
                            "breakout_price": candidate.plan_breakout_price,
                            "stop_price": candidate.plan_stop_price,
                            "max_position_cash": candidate.plan_max_position_cash,
                            "max_loss": candidate.plan_max_loss,
                            "buy_observation": candidate.buy_observation,
                            "abandon_conditions": candidate.abandon_conditions,
                            "max_chase_limit": candidate.max_chase_limit,
                            "structural_stop": candidate.structural_stop,
                            "suggested_position": candidate.suggested_position,
                            "max_loss_text": candidate.max_loss,
                            "theme_position": candidate.theme_position,
                            "theme_rank_today": candidate.theme_rank_today,
                            "event_confidence": candidate.event_confidence,
                        },
                        ensure_ascii=False,
                        sort_keys=True,
                    ),
                    run.generated_at,
                )
                for rank, candidate in enumerate(candidates, start=1)
            ],
        )
