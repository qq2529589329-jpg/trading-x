from dataclasses import dataclass
from pathlib import Path
import sqlite3

from trading_x.capabilities import ApiCheckResult, run_doctor
from trading_x.db import init_db
from trading_x.types import DataCapabilityLevel


@dataclass(frozen=True, slots=True)
class FakeAdapter:
    available: frozenset[str]

    def check_api(self, api_name: str) -> ApiCheckResult:
        if api_name in self.available:
            return ApiCheckResult(api_name=api_name, available=True)
        return ApiCheckResult(
            api_name=api_name,
            available=False,
            error_code="permission_denied",
            error_msg=f"{api_name} unavailable",
        )


def test_doctor_reports_degraded_when_token_missing(tmp_path: Path) -> None:
    db_path = tmp_path / "trading_x.db"
    init_db(db_path)

    summary = run_doctor(db_path, FakeAdapter(frozenset()), token=None)

    assert summary.level == DataCapabilityLevel.DEGRADED
    assert "TUSHARE_TOKEN" in summary.messages[0]


def test_doctor_records_partial_permissions_without_crashing(tmp_path: Path) -> None:
    db_path = tmp_path / "trading_x.db"
    init_db(db_path)

    summary = run_doctor(
        db_path,
        FakeAdapter(frozenset({"stock_basic", "trade_cal", "daily", "stk_limit"})),
        token="secret-token",
    )

    with sqlite3.connect(db_path) as conn:
        rows = conn.execute(
            "SELECT api_name, available, fallback_mode FROM data_capabilities"
        ).fetchall()

    capabilities = {row[0]: (row[1], row[2]) for row in rows}
    assert summary.level == DataCapabilityLevel.DEGRADED
    assert capabilities["daily"] == (1, "none")
    assert capabilities["daily_basic"] == (0, "block_candidates")
    assert capabilities["limit_cpt_list"] == (0, "theme_confidence_down")
    assert "secret-token" not in "\n".join(summary.messages)

