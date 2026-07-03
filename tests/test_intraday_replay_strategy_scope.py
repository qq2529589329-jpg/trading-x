from pathlib import Path

from intraday_replay_fixtures import PlanFixture, alert_rows, insert_plan, write_replay_csv
from trading_x.db import init_db
from trading_x.intraday import run_replay
from trading_x.types import StrategyType


def test_replay_ignores_non_b_class_intraday_plans(tmp_path: Path) -> None:
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
    write_replay_csv(input_path, "20260630,09:36:00,300001.SZ,12.00,10000,1000,12.00,11.80\n")

    result = run_replay(db_path, "20260630", input_path, tmp_path / "reports")

    assert result.status == "SUCCESS"
    assert result.plan_count == 0
    assert result.alert_count == 0
    assert alert_rows(db_path) == []
