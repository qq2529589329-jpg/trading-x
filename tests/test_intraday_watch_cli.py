from pathlib import Path
import sys

import pytest

from intraday_replay_fixtures import PlanFixture, alert_rows, insert_plan, write_replay_csv
from trading_x import cli
from trading_x.db import init_db


def test_cli_watch_fake_provider_writes_alerts(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    db_path = tmp_path / "trading_x.db"
    input_path = tmp_path / "watch.csv"
    init_db(db_path)
    insert_plan(db_path, PlanFixture(official_pre_close=10.0, volume_min_abs_amount=1000.0))
    write_replay_csv(input_path, "20260630,09:36:00,300001.SZ,12.00,10000,1000,12.00,11.80\n")
    monkeypatch.setattr(
        sys,
        "argv",
        ["trading_x", "--db", str(db_path), "watch", "--date", "20260630", "--input", str(input_path)],
    )

    exit_code = cli.main()

    output = capsys.readouterr().out
    assert exit_code == 0
    assert "watch=SUCCESS 20260630 alerts=1" in output
    assert alert_rows(db_path) == [("BUY_TRIGGER", "B_BUY_TRIGGERED")]


def test_cli_watch_boundary_exposes_only_read_only_fake_mode(
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    monkeypatch.setattr(sys, "argv", ["trading_x", "watch", "--help"])

    with pytest.raises(SystemExit) as exc_info:
        cli.main()

    output = capsys.readouterr().out.lower()
    assert exc_info.value.code == 0
    assert "--date" in output
    assert "--input" in output
    assert "order" not in output
    assert "sell" not in output
    assert "position" not in output
    assert "t+1" not in output
    assert "a-strong" not in output
    assert "l3" not in output
    assert "realtime" not in output
