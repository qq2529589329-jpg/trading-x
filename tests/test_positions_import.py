from pathlib import Path
import hashlib
import json
import sqlite3
import sys

import pytest

from trading_x import cli
from trading_x.db import init_db
from trading_x.positions import import_positions


def _ledger_text(available_shares: float = 500.0) -> str:
    return json.dumps(
        [
            {
                "trade_date": "20260706",
                "ts_code": "300001.SZ",
                "name": "容量龙",
                "total_shares": 1000.0,
                "available_shares": available_shares,
                "avg_cost": 10.2,
                "market_value": 10500.0,
            }
        ],
        ensure_ascii=False,
    )


def test_init_db_creates_position_tables(tmp_path: Path) -> None:
    # Given
    db_path = tmp_path / "trading_x.db"

    # When
    init_db(db_path)

    # Then
    with sqlite3.connect(db_path) as conn:
        position_columns = {row[1] for row in conn.execute("PRAGMA table_info(positions)")}
        run_columns = {row[1] for row in conn.execute("PRAGMA table_info(position_import_runs)")}
    assert {
        "trade_date",
        "ts_code",
        "total_shares",
        "available_shares",
        "avg_cost",
        "market_value",
        "source",
        "source_run_id",
    } <= position_columns
    assert {
        "trade_date",
        "input_file",
        "input_sha256",
        "position_count",
        "status",
        "started_at",
        "ended_at",
        "error_message",
    } <= run_columns


def test_import_positions_records_rows_and_success_run(tmp_path: Path) -> None:
    # Given
    db_path = tmp_path / "trading_x.db"
    input_path = tmp_path / "positions.json"
    input_text = _ledger_text()
    input_path.write_text(input_text, encoding="utf-8")
    init_db(db_path)

    # When
    result = import_positions(db_path, "20260706", input_path)

    # Then
    input_sha256 = hashlib.sha256(input_text.encode("utf-8")).hexdigest()
    with sqlite3.connect(db_path) as conn:
        position_row = conn.execute(
            "SELECT trade_date, ts_code, total_shares, available_shares, avg_cost, market_value, source "
            "FROM positions"
        ).fetchone()
        run_row = conn.execute(
            "SELECT trade_date, input_file, input_sha256, position_count, status, error_message "
            "FROM position_import_runs"
        ).fetchone()
    assert result.status == "SUCCESS"
    assert result.position_count == 1
    assert position_row == ("20260706", "300001.SZ", 1000.0, 500.0, 10.2, 10500.0, "json")
    assert run_row == ("20260706", str(input_path), input_sha256, 1, "SUCCESS", None)


def test_import_positions_accepts_utf8_bom_json(tmp_path: Path) -> None:
    # Given
    db_path = tmp_path / "trading_x.db"
    input_path = tmp_path / "positions.json"
    input_path.write_bytes(b"\xef\xbb\xbf" + _ledger_text().encode("utf-8"))
    init_db(db_path)

    # When
    result = import_positions(db_path, "20260706", input_path)

    # Then
    with sqlite3.connect(db_path) as conn:
        count = conn.execute("SELECT COUNT(*) FROM positions").fetchone()[0]
    assert result.status == "SUCCESS"
    assert count == 1

def test_import_positions_records_failed_run_when_ledger_is_invalid(tmp_path: Path) -> None:
    # Given
    db_path = tmp_path / "trading_x.db"
    input_path = tmp_path / "positions.json"
    row = json.loads(_ledger_text())[0]
    del row["available_shares"]
    input_text = json.dumps([row], ensure_ascii=False)
    input_path.write_text(input_text, encoding="utf-8")
    init_db(db_path)

    # When
    result = import_positions(db_path, "20260706", input_path)

    # Then
    with sqlite3.connect(db_path) as conn:
        position_count = conn.execute("SELECT COUNT(*) FROM positions").fetchone()[0]
        run_row = conn.execute(
            "SELECT position_count, status, error_message FROM position_import_runs"
        ).fetchone()
    assert result.status == "FAILED"
    assert position_count == 0
    assert run_row == (0, "FAILED", "POSITION_LEDGER_MISSING_REQUIRED_FIELDS: available_shares")


def test_cli_positions_import_writes_positions(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    # Given
    db_path = tmp_path / "trading_x.db"
    input_path = tmp_path / "positions.json"
    input_path.write_text(_ledger_text(), encoding="utf-8")
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "trading_x",
            "--db",
            str(db_path),
            "positions",
            "import",
            "--date",
            "20260706",
            "--input",
            str(input_path),
        ],
    )

    # When
    exit_code = cli.main()

    # Then
    output = capsys.readouterr().out
    with sqlite3.connect(db_path) as conn:
        count = conn.execute("SELECT COUNT(*) FROM positions").fetchone()[0]
    assert exit_code == 0
    assert "positions_import=SUCCESS 20260706 positions=1" in output
    assert count == 1