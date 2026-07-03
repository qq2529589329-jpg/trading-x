from dataclasses import dataclass
from datetime import UTC, datetime
from pathlib import Path
from typing import Protocol
import sqlite3

from trading_x.types import DataCapabilityLevel


@dataclass(frozen=True, slots=True)
class ApiDefinition:
    name: str
    tier: str
    min_points_required: int
    fallback_mode: str


@dataclass(frozen=True, slots=True)
class ApiCheckResult:
    api_name: str
    available: bool
    error_code: str | None = None
    error_msg: str | None = None


@dataclass(frozen=True, slots=True)
class DoctorSummary:
    level: DataCapabilityLevel
    available_apis: tuple[str, ...]
    unavailable_apis: tuple[str, ...]
    messages: tuple[str, ...]


class CapabilityAdapter(Protocol):
    def check_api(self, api_name: str) -> ApiCheckResult: ...


API_DEFINITIONS: tuple[ApiDefinition, ...] = (
    ApiDefinition("stock_basic", "P0", 0, "block_candidates"),
    ApiDefinition("trade_cal", "P0", 0, "block_candidates"),
    ApiDefinition("daily", "P0", 120, "block_candidates"),
    ApiDefinition("daily_basic", "P0", 2000, "block_candidates"),
    ApiDefinition("stk_limit", "P0", 0, "block_candidates"),
    ApiDefinition("top_list", "P1", 2000, "explain_unavailable"),
    ApiDefinition("limit_cpt_list", "P1", 0, "theme_confidence_down"),
    ApiDefinition("moneyflow", "P2", 2000, "optional_unavailable"),
    ApiDefinition("margin", "P2", 2000, "optional_unavailable"),
)


def persist_capabilities(db_path: Path, results: list[ApiCheckResult]) -> None:
    checked_at = datetime.now(UTC).isoformat()
    definitions = {definition.name: definition for definition in API_DEFINITIONS}
    with sqlite3.connect(db_path) as conn:
        conn.executemany(
            "INSERT INTO data_capabilities ("
            "api_name, available, min_points_required, last_checked_at, "
            "last_error_code, last_error_msg, fallback_mode"
            ") VALUES (?, ?, ?, ?, ?, ?, ?) "
            "ON CONFLICT(api_name) DO UPDATE SET "
            "available = excluded.available, "
            "min_points_required = excluded.min_points_required, "
            "last_checked_at = excluded.last_checked_at, "
            "last_error_code = excluded.last_error_code, "
            "last_error_msg = excluded.last_error_msg, "
            "fallback_mode = excluded.fallback_mode",
            [
                (
                    result.api_name,
                    int(result.available),
                    definitions.get(result.api_name, API_DEFINITIONS[0]).min_points_required,
                    checked_at,
                    result.error_code,
                    result.error_msg,
                    "none" if result.available else _fallback_for(result.api_name),
                )
                for result in results
            ],
        )


def run_doctor(db_path: Path, adapter: CapabilityAdapter, token: str | None) -> DoctorSummary:
    if token is None or token.strip() == "":
        results = [
            ApiCheckResult(
                api_name=definition.name,
                available=False,
                error_code="missing_token",
                error_msg="TUSHARE_TOKEN is required",
            )
            for definition in API_DEFINITIONS
        ]
        persist_capabilities(db_path, results)
        return DoctorSummary(
            level=DataCapabilityLevel.DEGRADED,
            available_apis=(),
            unavailable_apis=tuple(result.api_name for result in results),
            messages=("TUSHARE_TOKEN is required; reports will be DEGRADED.",),
        )

    results = [adapter.check_api(definition.name) for definition in API_DEFINITIONS]
    persist_capabilities(db_path, results)
    level = capability_level(results)
    return DoctorSummary(
        level=level,
        available_apis=tuple(result.api_name for result in results if result.available),
        unavailable_apis=tuple(result.api_name for result in results if not result.available),
        messages=(f"Data capability: {level}",),
    )


def capability_level(results: list[ApiCheckResult]) -> DataCapabilityLevel:
    unavailable = {result.api_name for result in results if not result.available}
    p0 = {definition.name for definition in API_DEFINITIONS if definition.tier == "P0"}
    p1 = {definition.name for definition in API_DEFINITIONS if definition.tier == "P1"}
    if unavailable & p0:
        return DataCapabilityLevel.DEGRADED
    if unavailable & p1:
        return DataCapabilityLevel.BASIC
    return DataCapabilityLevel.FULL


def _fallback_for(api_name: str) -> str:
    for definition in API_DEFINITIONS:
        if definition.name == api_name:
            return definition.fallback_mode
    return "optional_unavailable"
