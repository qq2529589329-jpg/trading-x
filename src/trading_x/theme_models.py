from dataclasses import dataclass
from pathlib import Path
from typing import Final


REQUIRED_COLUMNS: Final[tuple[str, ...]] = (
    "ts_code",
    "name",
    "industry",
    "theme_primary",
    "theme_tags",
    "theme_source",
    "confidence",
    "updated_at",
    "notes",
)

THEME_TIER_WEIGHTS: Final[dict[str, float]] = {
    "CORE": 1.0,
    "IMPORTANT": 0.7,
    "RELATED": 0.4,
}

THEME_MEMBER_EXPORT_COLUMNS: Final[tuple[str, ...]] = (
    "ts_code",
    "name",
    "industry",
    "theme_primary",
    "theme_tags",
    "theme_tier",
    "theme_weight",
    "theme_source",
    "confidence",
    "updated_at",
    "notes",
    "reason",
)


@dataclass(frozen=True, slots=True)
class ThemeCsvError(Exception):
    row_number: int
    field: str
    reason: str

    def __str__(self) -> str:
        return f"theme csv row {self.row_number}: {self.field} {self.reason}"


@dataclass(frozen=True, slots=True)
class ThemeMember:
    ts_code: str
    name: str
    industry: str
    theme_primary: str
    theme_tags: str
    theme_tier: str = "IMPORTANT"
    theme_weight: float = 0.7
    theme_source: str = "manual"
    confidence: str = "LOW"
    updated_at: str = ""
    notes: str = ""


@dataclass(frozen=True, slots=True)
class ThemeImportResult:
    imported_count: int
    failed_count: int
    duplicate_count: int


@dataclass(frozen=True, slots=True)
class ThemeAggregate:
    theme_name: str
    member_count: int
    up_count: int
    limit_up_count: int
    avg_pct_chg: float
    total_amount: float
    candidate_count: int
    confidence: str
    core_symbols: str
    weighted_limit_up_count: float = 0.0
    weighted_avg_pct_chg: float = 0.0
    weighted_total_amount: float = 0.0


@dataclass(frozen=True, slots=True)
class ThemeCoverage:
    stock_total: int
    mapped_stock_count: int
    candidate_total: int
    candidate_mapped_count: int
    limit_up_total: int = 0
    limit_up_mapped_count: int = 0
    top_amount_total: int = 0
    top_amount_mapped_count: int = 0
    limit_active_total: int = 0
    limit_active_mapped_count: int = 0
    unmapped_candidates: tuple[str, ...] = ()
    missing_suggestions: tuple[str, ...] = ()


@dataclass(frozen=True, slots=True)
class ThemeMissingCandidate:
    ts_code: str
    name: str
    industry: str
    reason: str


@dataclass(frozen=True, slots=True)
class ThemeMissingExportRequest:
    trade_date: str
    top_amount: int
    top_limit_active: int
    output_path: Path
