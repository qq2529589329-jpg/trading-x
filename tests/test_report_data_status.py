from pathlib import Path
import sqlite3

from trading_x import reports
from trading_x.capabilities import API_DEFINITIONS, ApiCheckResult, persist_capabilities
from trading_x.db import init_db
from trading_x.types import DataCapabilityLevel


def test_report_blocks_candidates_when_p0_data_is_incomplete(
    tmp_path: Path,
    monkeypatch,
) -> None:
    db_path = tmp_path / "trading_x.db"
    report_dir = tmp_path / "reports"
    init_db(db_path)
    persist_capabilities(
        db_path,
        [ApiCheckResult(api_name=definition.name, available=True) for definition in API_DEFINITIONS],
    )
    with sqlite3.connect(db_path) as conn:
        conn.execute(
            "INSERT INTO data_completeness_summary ("
            "trade_date, p0_complete, p1_complete, data_capability, latest_complete_date, "
            "partial_reason, checked_at"
            ") VALUES (?, ?, ?, ?, ?, ?, ?)",
            (
                "20260630",
                0,
                0,
                "P0_INCOMPLETE",
                "20260629",
                "HALF_UPDATED: daily,daily_basic missing",
                "2026-06-30T15:00:00+00:00",
            ),
        )
    monkeypatch.setattr(reports, "select_candidates", _fail_if_called)

    snapshot = reports.generate_report(db_path, "20260630", report_dir)

    assert snapshot.data_capability == DataCapabilityLevel.DEGRADED
    assert snapshot.allow_new_position is False
    assert snapshot.candidates == []
    assert snapshot.risk_blocks == (
        "P0 数据不完整：HALF_UPDATED: daily,daily_basic missing；禁止新开仓。",
    )


def test_report_blocks_candidates_when_p0_summary_is_missing(
    tmp_path: Path,
    monkeypatch,
) -> None:
    db_path = tmp_path / "trading_x.db"
    report_dir = tmp_path / "reports"
    init_db(db_path)
    persist_capabilities(
        db_path,
        [ApiCheckResult(api_name=definition.name, available=True) for definition in API_DEFINITIONS],
    )
    monkeypatch.setattr(reports, "select_candidates", _fail_if_called)

    snapshot = reports.generate_report(db_path, "20260630", report_dir)

    assert snapshot.data_capability == DataCapabilityLevel.DEGRADED
    assert snapshot.candidates == []
    assert snapshot.risk_blocks == (
        "P0 数据不完整：P0_INCOMPLETE: stock_basic,daily,daily_basic,stk_limit missing；禁止新开仓。",
    )


def _fail_if_called(*args) -> None:
    raise AssertionError("should not generate candidates when P0 is incomplete")
