from pathlib import Path
import json
import sqlite3

from trading_x.db import init_db
from trading_x.provider_decision import (
    ComplianceUseStatus,
    ProviderEvaluationEvidence,
    decide_provider_evaluation,
)
from trading_x.provider_evaluation import (
    ProviderSnapshotSample,
    ProviderSource,
    ValidationStatus,
)
from trading_x.provider_report import write_provider_evaluation_report


def _sample(ts_code: str = "300001.SZ") -> ProviderSnapshotSample:
    return ProviderSnapshotSample(
        trade_date="20260704",
        quote_time="09:35:00",
        ts_code=ts_code,
        price=10.5,
        amount_since_open=1050000.0,
        volume_since_open=100000.0,
        bar_high=10.6,
        bar_low=10.1,
        source=ProviderSource.MOOTDX,
        latency_ms=25,
        validation_status=ValidationStatus.ACCEPTED,
        reason_codes=(),
    )


def _evidence() -> ProviderEvaluationEvidence:
    return ProviderEvaluationEvidence(
        requested_symbols=("300001.SZ", "600001.SH"),
        samples=(_sample("300001.SZ"),),
        compliance_use_status=ComplianceUseStatus.APPROVED,
    )


def test_provider_evaluation_writes_json_and_markdown_artifacts_only(
    tmp_path: Path,
) -> None:
    output_dir = tmp_path / "provider_eval"
    evidence = _evidence()
    decision = decide_provider_evaluation(evidence)

    artifacts = write_provider_evaluation_report(output_dir, evidence, decision)

    assert sorted(path.name for path in output_dir.iterdir()) == [
        "20260704_mootdx_provider_evaluation.json",
        "20260704_mootdx_provider_evaluation.md",
    ]
    assert artifacts.json_path == output_dir / "20260704_mootdx_provider_evaluation.json"
    assert artifacts.markdown_path == output_dir / "20260704_mootdx_provider_evaluation.md"
    payload = json.loads(artifacts.json_path.read_text(encoding="utf-8"))
    assert payload["decision"] == "disabled_for_live_watch"
    assert payload["reason_codes"] == ["PROVIDER_COVERAGE_PARTIAL"]
    assert payload["symbols_missing"] == ["600001.SH"]
    markdown = artifacts.markdown_path.read_text(encoding="utf-8")
    assert "# Provider Evaluation: mootdx 20260704" in markdown
    assert "- decision: disabled_for_live_watch" in markdown


def test_provider_evaluation_report_does_not_write_intraday_tables(
    tmp_path: Path,
) -> None:
    db_path = tmp_path / "trading_x.db"
    init_db(db_path)
    output_dir = tmp_path / "provider_eval"
    evidence = _evidence()
    decision = decide_provider_evaluation(evidence)

    write_provider_evaluation_report(output_dir, evidence, decision)

    with sqlite3.connect(db_path) as conn:
        counts = {
            table: conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
            for table in (
                "intraday_alerts",
                "intraday_alert_locks",
                "intraday_plans",
            )
        }
    assert counts == {
        "intraday_alerts": 0,
        "intraday_alert_locks": 0,
        "intraday_plans": 0,
    }
