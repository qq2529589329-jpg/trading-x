from pathlib import Path
import json
import sqlite3
import sys

import pytest

from trading_x import cli
from trading_x.db import init_db


def test_cli_provider_evaluate_writes_artifacts_only(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    db_path = tmp_path / "trading_x.db"
    sample_path = tmp_path / "sample.json"
    output_dir = tmp_path / "provider_eval"
    init_db(db_path)
    sample_path.write_text(
        json.dumps(
            [
                {
                    "trade_date": "20260704",
                    "quote_time": "09:35:00",
                    "ts_code": "300001.SZ",
                    "price": 10.5,
                    "amount_since_open": 1050000.0,
                    "volume_since_open": 100000.0,
                    "bar_high": 10.6,
                    "bar_low": 10.1,
                    "source": "mootdx",
                    "latency_ms": 25,
                    "validation_status": "accepted",
                    "reason_codes": [],
                }
            ],
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "trading_x",
            "--db",
            str(db_path),
            "provider-evaluate",
            "--source",
            "mootdx",
            "--date",
            "20260704",
            "--symbols",
            "300001.SZ",
            "--sample",
            str(sample_path),
            "--output-dir",
            str(output_dir),
            "--compliance-use-status",
            "approved",
        ],
    )

    exit_code = cli.main()

    output = capsys.readouterr().out
    payload = json.loads((output_dir / "20260704_mootdx_provider_evaluation.json").read_text(encoding="utf-8"))
    with sqlite3.connect(db_path) as conn:
        counts = {
            table: conn.execute(f"SELECT COUNT(*) FROM {table}").fetchone()[0]
            for table in ("intraday_alerts", "intraday_alert_locks", "intraday_plans")
        }
    assert exit_code == 0
    assert "provider_evaluation=candidate_only mootdx 20260704 samples=1" in output
    assert payload["decision"] == "candidate_only"
    assert counts == {"intraday_alerts": 0, "intraday_alert_locks": 0, "intraday_plans": 0}


def test_cli_provider_evaluate_fails_when_sample_lacks_volume(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    sample_path = tmp_path / "bad_sample.json"
    output_dir = tmp_path / "provider_eval"
    sample_path.write_text(
        json.dumps(
            [
                {
                    "trade_date": "20260704",
                    "quote_time": "09:35:00",
                    "ts_code": "300001.SZ",
                    "price": 10.5,
                    "amount_since_open": 1050000.0,
                    "bar_high": 10.6,
                    "bar_low": 10.1,
                    "source": "mootdx",
                    "latency_ms": 25,
                    "validation_status": "accepted",
                    "reason_codes": [],
                }
            ],
            ensure_ascii=False,
        ),
        encoding="utf-8",
    )
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "trading_x",
            "provider-evaluate",
            "--source",
            "mootdx",
            "--date",
            "20260704",
            "--symbols",
            "300001.SZ",
            "--sample",
            str(sample_path),
            "--output-dir",
            str(output_dir),
        ],
    )

    exit_code = cli.main()

    output = capsys.readouterr().out
    assert exit_code == 1
    assert "provider_evaluation=FAILED mootdx 20260704" in output
    assert "PROVIDER_SAMPLE_MISSING_REQUIRED_FIELDS: volume_since_open" in output
    assert not output_dir.exists()
