from pathlib import Path
import sys

import pytest

from intraday_replay_fixtures import PlanFixture, insert_plan
from trading_x import cli
from trading_x.db import init_db
from trading_x.types import StrategyType


def test_cli_plans_symbols_prints_strategy_plan_symbols(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    db_path = tmp_path / "trading_x.db"
    init_db(db_path)
    insert_plan(
        db_path,
        PlanFixture(
            official_pre_close=10.0,
            volume_min_abs_amount=1000.0,
            strategy_type=StrategyType.A_SPACE_LEADER,
        ),
    )
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "trading_x",
            "--db",
            str(db_path),
            "plans",
            "symbols",
            "--date",
            "20260630",
            "--strategy",
            StrategyType.A_SPACE_LEADER,
        ],
    )

    exit_code = cli.main()

    assert exit_code == 0
    assert capsys.readouterr().out == "300001.SZ\n"
