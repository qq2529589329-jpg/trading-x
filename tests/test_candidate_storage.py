from pathlib import Path
import sqlite3

from trading_x.candidate_models import CandidateReport
from trading_x.candidate_storage import persist_candidates
from trading_x.db import init_db
from trading_x.types import CandidateGrade, Confidence, StrategyType


def test_persist_candidates_writes_candidate_table(tmp_path: Path) -> None:
    db_path = tmp_path / "trading_x.db"
    init_db(db_path)
    candidate = CandidateReport(
        ts_code="300001.SZ",
        name="容量龙",
        strategy_type=StrategyType.B_CAPACITY_LEADER,
        candidate_grade=CandidateGrade.B_CORE,
        theme_name="机器人",
        theme_tags="机器人;智能制造",
        theme_rank_today=1,
        theme_strength_score=88.0,
        theme_position="成交额第 1，涨幅第 2",
        entry_reason="所属机器人题材今日强度排名第 1。",
        veto_items="P0 风控通过。",
        buy_observation="明日只观察放量突破或回踩承接。",
        abandon_conditions="跌回平台内则放弃。",
        max_chase_limit="不追高超过计划买点 5%。",
        structural_stop="跌破当日低点 19.80。",
        suggested_position="观察仓 10%-20%。",
        max_loss="单笔最大亏损控制在总资金 1% 内。",
        data_confidence=Confidence.MEDIUM,
        theme_confidence=Confidence.MEDIUM,
        event_confidence=Confidence.UNAVAILABLE,
    )

    with sqlite3.connect(db_path) as conn:
        persist_candidates(conn, "20260701", [candidate])
        row = conn.execute(
            "SELECT strategy_type, candidate_grade, theme_name, entry_reason "
            "FROM candidates WHERE trade_date = ? AND ts_code = ?",
            ("20260701", "300001.SZ"),
        ).fetchone()

    assert row == (
        StrategyType.B_CAPACITY_LEADER,
        CandidateGrade.B_CORE,
        "机器人",
        "所属机器人题材今日强度排名第 1。",
    )
