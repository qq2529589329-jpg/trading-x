from pathlib import Path
import sqlite3
import sys

import pytest

from intraday_replay_fixtures import PlanFixture, alert_rows, insert_plan, seed_b_candidate, write_replay_csv
from trading_x import cli
from trading_x.db import init_db
from trading_x.intraday import materialize_intraday_plans, run_replay
from trading_x.types import CandidateGrade, StrategyType


def test_materialize_a_class_intraday_plan_from_structured_candidate(tmp_path: Path) -> None:
    db_path = tmp_path / "trading_x.db"
    init_db(db_path)
    _seed_a_candidate(db_path)

    count = materialize_intraday_plans(db_path, "20260630", strategy_type=StrategyType.A_SPACE_LEADER)

    with sqlite3.connect(db_path) as conn:
        row = conn.execute(
            "SELECT strategy_type, entry_low, entry_high, breakout_price, stop_price, volume_gate_enabled "
            "FROM intraday_plans WHERE trade_date = ?",
            ("20260630",),
        ).fetchone()
    assert count == 1
    assert row == (StrategyType.A_SPACE_LEADER, 11.0, 11.0, 11.0, 10.23, 0)


def test_replay_a_class_explicit_strategy_writes_a_buy_trigger(tmp_path: Path) -> None:
    db_path = tmp_path / "trading_x.db"
    input_path = tmp_path / "replay.csv"
    init_db(db_path)
    insert_plan(
        db_path,
        PlanFixture(
            official_pre_close=10.0,
            volume_min_abs_amount=1000.0,
            strategy_type=StrategyType.A_SPACE_LEADER,
        ),
    )
    write_replay_csv(input_path, "20260630,09:36:00,300001.SZ,11.00,11000,1000,11.00,10.80\n")

    result = run_replay(
        db_path,
        "20260630",
        input_path,
        tmp_path / "reports",
        strategy_type=StrategyType.A_SPACE_LEADER,
    )

    assert result.status == "SUCCESS"
    assert result.alert_count == 1
    assert alert_rows(db_path) == [("BUY_TRIGGER", "A_BUY_TRIGGERED")]


def test_cli_plans_materialize_accepts_a_class_strategy(
    tmp_path: Path,
    monkeypatch: pytest.MonkeyPatch,
    capsys: pytest.CaptureFixture[str],
) -> None:
    db_path = tmp_path / "trading_x.db"
    init_db(db_path)
    _seed_a_candidate(db_path)
    monkeypatch.setattr(
        sys,
        "argv",
        [
            "trading_x",
            "--db",
            str(db_path),
            "plans",
            "materialize",
            "--date",
            "20260630",
            "--strategy",
            StrategyType.A_SPACE_LEADER,
        ],
    )

    exit_code = cli.main()

    with sqlite3.connect(db_path) as conn:
        plan_count = conn.execute(
            "SELECT COUNT(*) FROM intraday_plans WHERE strategy_type = ?",
            (StrategyType.A_SPACE_LEADER,),
        ).fetchone()[0]
    output = capsys.readouterr().out
    assert exit_code == 0
    assert "intraday_plans=1 20260630" in output
    assert plan_count == 1


def _seed_a_candidate(db_path: Path) -> None:
    seed_b_candidate(db_path, pre_close=10.0)
    with sqlite3.connect(db_path) as conn:
        conn.execute(
            "UPDATE daily_quotes SET high = ?, low = ?, close = ? WHERE trade_date = ? AND ts_code = ?",
            (11.0, 10.2, 11.0, "20260630", "300001.SZ"),
        )
        conn.execute(
            "UPDATE candidates SET strategy_type = ?, candidate_grade = ? WHERE trade_date = ? AND ts_code = ?",
            (StrategyType.A_SPACE_LEADER, CandidateGrade.A_LITE, "20260630", "300001.SZ"),
        )
