from pathlib import Path
import json
import sqlite3
import sys

from acceptance_fixtures import (
    TenDayP0Adapter,
    generated_ten_day_reports,
    persist_basic_capabilities,
)
from trading_x import cli
from trading_x.acceptance import run_acceptance
from trading_x.db import init_db
from trading_x.reports import generate_report
from trading_x.tushare_adapter import update_p0_data
from trading_x.types import DataCapabilityLevel


def test_ten_day_v1_acceptance_fixture_is_stable(tmp_path: Path) -> None:
    db_path = tmp_path / "trading_x.db"
    report_dir = tmp_path / "reports"
    init_db(db_path)
    persist_basic_capabilities(db_path)

    for day in range(1, 11):
        trade_date = f"202607{day:02d}"
        update_p0_data(db_path, trade_date, TenDayP0Adapter())
        update_p0_data(db_path, trade_date, TenDayP0Adapter())

        first = generate_report(db_path, trade_date, report_dir)
        second = generate_report(db_path, trade_date, report_dir)
        json_path = report_dir / f"{trade_date}_report.json"
        md_path = report_dir / f"{trade_date}_report.md"
        payload = json.loads(json_path.read_text(encoding="utf-8"))
        markdown = md_path.read_text(encoding="utf-8")

        assert first.to_json_text() == second.to_json_text()
        assert first.data_capability == DataCapabilityLevel.BASIC
        assert first.market_status
        assert first.allow_new_position is False
        assert 0 <= len(payload["candidates"]) <= 5
        assert payload["candidates"] == []
        assert "今日无符合纪律候选" in markdown
        assert "禁止新开仓" in markdown
        assert "secret-token" not in json_path.read_text(encoding="utf-8")
        assert "secret-token" not in markdown

    with sqlite3.connect(db_path) as conn:
        assert conn.execute("SELECT COUNT(*) FROM stock_universe").fetchone()[0] == 1
        assert conn.execute("SELECT COUNT(*) FROM daily_quotes").fetchone()[0] == 10
        assert conn.execute("SELECT COUNT(*) FROM daily_basic").fetchone()[0] == 10
        assert conn.execute("SELECT COUNT(*) FROM stk_limit_prices").fetchone()[0] == 10
        assert conn.execute("SELECT COUNT(*) FROM reports").fetchone()[0] == 10


def test_acceptance_cli_passes_for_ten_generated_days(
    tmp_path: Path,
    monkeypatch,
    capsys,
) -> None:
    db_path = tmp_path / "trading_x.db"
    report_dir = tmp_path / "reports"
    dates = generated_ten_day_reports(db_path, report_dir)
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "trading_x",
            "--db",
            str(db_path),
            "acceptance",
            "--dates",
            ",".join(dates),
            "--report-dir",
            str(report_dir),
        ],
    )

    assert cli.main() == 0

    output = capsys.readouterr().out
    assert "acceptance=PASS" in output
    assert "days=10" in output


def test_acceptance_cli_uses_recent_report_dates(
    tmp_path: Path,
    monkeypatch,
    capsys,
) -> None:
    db_path = tmp_path / "trading_x.db"
    report_dir = tmp_path / "reports"
    generated_ten_day_reports(db_path, report_dir)
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "trading_x",
            "--db",
            str(db_path),
            "acceptance",
            "--last-n",
            "10",
            "--report-dir",
            str(report_dir),
        ],
    )

    assert cli.main() == 0

    output = capsys.readouterr().out
    assert "acceptance=PASS" in output
    assert "days=10" in output


def test_acceptance_cli_uses_recent_complete_report_dates(
    tmp_path: Path,
    monkeypatch,
    capsys,
) -> None:
    db_path = tmp_path / "trading_x.db"
    report_dir = tmp_path / "reports"
    generated_ten_day_reports(db_path, report_dir)
    generate_report(db_path, "20260711", report_dir)
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "trading_x",
            "--db",
            str(db_path),
            "acceptance",
            "--last-complete-n",
            "10",
            "--report-dir",
            str(report_dir),
        ],
    )

    assert cli.main() == 0

    output = capsys.readouterr().out
    assert "acceptance=PASS" in output
    assert "days=10" in output


def test_acceptance_cli_lists_incomplete_report_dates(
    tmp_path: Path,
    monkeypatch,
    capsys,
) -> None:
    db_path = tmp_path / "trading_x.db"
    report_dir = tmp_path / "reports"
    generated_ten_day_reports(db_path, report_dir)
    generate_report(db_path, "20260711", report_dir)
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "trading_x",
            "--db",
            str(db_path),
            "acceptance",
            "--list-incomplete",
            "--report-dir",
            str(report_dir),
        ],
    )

    assert cli.main() == 0

    output = capsys.readouterr().out
    assert "incomplete_reports=1" in output
    assert "- 20260711: daily_quotes,daily_basic,stk_limit_prices" in output


def test_acceptance_cli_fails_when_less_than_ten_days(
    tmp_path: Path,
    monkeypatch,
    capsys,
) -> None:
    db_path = tmp_path / "trading_x.db"
    report_dir = tmp_path / "reports"
    dates = generated_ten_day_reports(db_path, report_dir)[:9]
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "trading_x",
            "--db",
            str(db_path),
            "acceptance",
            "--dates",
            ",".join(dates),
            "--report-dir",
            str(report_dir),
        ],
    )

    assert cli.main() == 1

    output = capsys.readouterr().out
    assert "acceptance=FAIL" in output
    assert "至少需要 10 个交易日" in output


def test_acceptance_fails_when_markdown_report_is_missing(tmp_path: Path) -> None:
    db_path = tmp_path / "trading_x.db"
    report_dir = tmp_path / "reports"
    dates = generated_ten_day_reports(db_path, report_dir)
    (report_dir / "20260701_report.md").unlink()

    result = run_acceptance(db_path, report_dir, dates)

    assert result.passed is False
    assert "20260701: Markdown 报告缺失。" in result.failures


def test_acceptance_checks_env_file_token_leak(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.chdir(tmp_path)
    monkeypatch.delenv("TUSHARE_TOKEN", raising=False)
    db_path = tmp_path / "trading_x.db"
    report_dir = tmp_path / "reports"
    dates = generated_ten_day_reports(db_path, report_dir)
    token = "secret-token-from-env-file"
    (tmp_path / ".env").write_text(f"TUSHARE_TOKEN={token}\n", encoding="utf-8")
    report_path = report_dir / "20260701_report.md"
    report_path.write_text(report_path.read_text(encoding="utf-8") + token, encoding="utf-8")

    result = run_acceptance(db_path, report_dir, dates)

    assert result.passed is False
    assert "20260701: 报告疑似泄露 TUSHARE_TOKEN。" in result.failures
