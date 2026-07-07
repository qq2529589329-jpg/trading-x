from pathlib import Path
import json
import sqlite3

from jsonschema import Draft202012Validator

from trading_x import reports
from trading_x.capabilities import API_DEFINITIONS, ApiCheckResult, persist_capabilities
from trading_x.candidate_models import CandidateReport
from trading_x.db import init_db
from trading_x.reports import generate_report
from trading_x.types import CandidateGrade, Confidence, DataCapabilityLevel, StrategyType


CONTRACT_PATH = (
    Path(__file__).parents[1]
    / "specs"
    / "001-ai-stock-selection-v1"
    / "contracts"
    / "report-schema.json"
)


def test_degraded_report_generates_json_markdown_and_snapshot(tmp_path: Path) -> None:
    db_path = tmp_path / "trading_x.db"
    report_dir = tmp_path / "reports"
    init_db(db_path)
    persist_capabilities(
        db_path,
        [
            ApiCheckResult(
                api_name="daily",
                available=False,
                error_code="permission_denied",
                error_msg="daily unavailable",
            )
        ],
    )

    snapshot = generate_report(db_path, "20260701", report_dir)

    json_path = report_dir / "20260701_report.json"
    md_path = report_dir / "20260701_report.md"
    assert json_path.exists()
    assert md_path.exists()
    assert snapshot.data_capability == DataCapabilityLevel.DEGRADED
    assert snapshot.candidates == []
    assert "今日无符合纪律候选" in md_path.read_text(encoding="utf-8")

    with sqlite3.connect(db_path) as conn:
        row = conn.execute(
            "SELECT report_snapshot_json FROM reports WHERE trade_date = ?",
            ("20260701",),
        ).fetchone()

    assert row is not None
    assert json.loads(row[0]) == json.loads(json_path.read_text(encoding="utf-8"))

    with sqlite3.connect(db_path) as conn:
        run_row = conn.execute(
            "SELECT p0_complete FROM candidate_runs WHERE trade_date = ?",
            ("20260701",),
        ).fetchone()
        snapshot_count = conn.execute("SELECT COUNT(*) FROM candidate_snapshots").fetchone()[0]

    assert run_row == (0,)
    assert snapshot_count == 0


def test_report_rerun_for_same_day_is_stable(tmp_path: Path) -> None:
    db_path = tmp_path / "trading_x.db"
    report_dir = tmp_path / "reports"
    init_db(db_path)

    first = generate_report(db_path, "20260701", report_dir)
    second = generate_report(db_path, "20260701", report_dir)

    assert first.to_json_text() == second.to_json_text()


def test_report_json_matches_contract_schema(tmp_path: Path) -> None:
    db_path = tmp_path / "trading_x.db"
    report_dir = tmp_path / "reports"
    init_db(db_path)

    generate_report(db_path, "20260701", report_dir)

    schema = json.loads(CONTRACT_PATH.read_text(encoding="utf-8"))
    payload = json.loads((report_dir / "20260701_report.json").read_text(encoding="utf-8"))
    Draft202012Validator(schema).validate(payload)


def test_candidate_plan_fields_are_written_to_json_and_markdown(
    tmp_path: Path,
    monkeypatch,
) -> None:
    db_path = tmp_path / "trading_x.db"
    report_dir = tmp_path / "reports"
    init_db(db_path)
    persist_capabilities(db_path, [ApiCheckResult(api_name="daily", available=True)])
    with sqlite3.connect(db_path) as conn:
        conn.execute(
            "INSERT INTO data_completeness_summary ("
            "trade_date, p0_complete, p1_complete, data_capability, latest_complete_date, "
            "partial_reason, checked_at"
            ") VALUES (?, ?, ?, ?, ?, ?, ?)",
            ("20260701", 1, 0, "FULL", None, None, "2026-07-01T15:00:00+00:00"),
        )
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
    monkeypatch.setattr(reports, "select_candidates", lambda *args: [candidate])

    reports.generate_report(db_path, "20260701", report_dir)

    payload = json.loads((report_dir / "20260701_report.json").read_text(encoding="utf-8"))
    markdown = (report_dir / "20260701_report.md").read_text(encoding="utf-8")
    first = payload["candidates"][0]
    assert first["strategy_type"] == StrategyType.B_CAPACITY_LEADER
    assert first["candidate_grade"] == CandidateGrade.B_CORE
    assert first["entry_reason"] == "所属机器人题材今日强度排名第 1。"
    assert first["theme_confidence"] == Confidence.MEDIUM
    assert "- 买入观察条件：明日只观察放量突破或回踩承接。" in markdown
    assert "- 放弃条件：跌回平台内则放弃。" in markdown
    assert "- 最大追高限制：不追高超过计划买点 5%。" in markdown
    assert "- theme_confidence：MEDIUM" in markdown

    with sqlite3.connect(db_path) as conn:
        row = conn.execute(
            "SELECT cr.data_capability, cs.rank, cs.ts_code, cs.theme_name "
            "FROM candidate_runs cr "
            "JOIN candidate_snapshots cs ON cs.run_id = cr.run_id "
            "WHERE cr.trade_date = ?",
            ("20260701",),
        ).fetchone()

    assert row == (DataCapabilityLevel.FULL, 1, "300001.SZ", "机器人")


def test_report_includes_new_rule_compatibility_section_after_20260706(tmp_path: Path) -> None:
    db_path = tmp_path / "trading_x.db"
    report_dir = tmp_path / "reports"
    init_db(db_path)

    generate_report(db_path, "20260706", report_dir)

    payload = json.loads((report_dir / "20260706_report.json").read_text(encoding="utf-8"))
    markdown = (report_dir / "20260706_report.md").read_text(encoding="utf-8")
    assert payload["new_rule_compatibility"] == {
        "trading_rule_version": "20260706",
        "mainboard_st_limit_ratio": 0.10,
        "post_close_fixed_price_scope": "ALL_A_SHARES_ETF",
        "normal_emotion_excludes_st": True,
        "data_rule_match": True,
        "post_close_data_available": False,
        "system_action": "ALLOW_REPORT",
    }
    assert "## 新规兼容检查" in markdown
    assert "- 交易规则版本：20260706" in markdown
    assert "- 主板 ST 涨跌幅：10%" in markdown
    assert "- 盘后固定价格交易：全部 A 股 / ETF" in markdown
    assert "- 普通股情绪是否剔除 ST：是" in markdown
    assert "- 数据源涨跌停价是否匹配新规：是" in markdown
    assert "- 盘后固定价格数据：unavailable" in markdown
    assert "- 成交额口径：可能包含盘后固定价格成交" in markdown
    assert "- 系统动作：允许正常生成日报" in markdown


def test_report_splits_normal_and_st_market_emotion(tmp_path: Path) -> None:
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
            ("20260706", 1, 1, "FULL", None, None, "2026-07-06T15:00:00+00:00"),
        )
        stocks = (
            ("600001.SH", "600001", "普通涨停", 0),
            ("600002.SH", "600002", "普通跌停", 0),
            ("600003.SH", "600003", "ST一号", 1),
            ("600004.SH", "600004", "ST二号", 1),
        )
        conn.executemany(
            "INSERT INTO stock_universe ("
            "ts_code, symbol, name, exchange, market, list_date, "
            "is_st, is_delisting_risk, included, excluded_reason"
            ") VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            [
                (ts_code, symbol, name, "SSE", "主板", "20200101", is_st, 0, 1, None)
                for ts_code, symbol, name, is_st in stocks
            ],
        )
        conn.executemany(
            "INSERT INTO daily_quotes ("
            "trade_date, ts_code, open, high, low, close, pre_close, pct_chg, vol, amount"
            ") VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            [
                ("20260706", "600001.SH", 10.0, 11.0, 9.9, 11.0, 10.0, 10.0, 1000.0, 100000.0),
                ("20260706", "600002.SH", 10.0, 10.1, 9.0, 9.0, 10.0, -10.0, 1000.0, 100000.0),
                ("20260706", "600003.SH", 10.0, 11.0, 9.9, 11.0, 10.0, 10.0, 1000.0, 100000.0),
                ("20260706", "600004.SH", 10.0, 11.0, 9.9, 11.0, 10.0, 10.0, 1000.0, 100000.0),
            ],
        )
        conn.executemany(
            "INSERT INTO limit_events ("
            "trade_date, ts_code, limit_type, is_limit_close, first_limit_time, last_limit_time, "
            "open_times, limit_break_count, seal_amount, event_confidence, data_source"
            ") VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            [
                ("20260706", "600001.SH", "UP", 1, "09:45:00", "15:00:00", 0, 0, 1000.0, "HIGH", "fixture"),
                ("20260706", "600002.SH", "DOWN", 1, "10:00:00", "15:00:00", 0, 0, 1000.0, "HIGH", "fixture"),
                ("20260706", "600003.SH", "UP", 1, "09:45:00", "15:00:00", 0, 0, 1000.0, "HIGH", "fixture"),
                ("20260706", "600004.SH", "UP", 1, "10:15:00", "15:00:00", 0, 0, 1000.0, "HIGH", "fixture"),
            ],
        )

    generate_report(db_path, "20260706", report_dir)

    payload = json.loads((report_dir / "20260706_report.json").read_text(encoding="utf-8"))
    markdown = (report_dir / "20260706_report.md").read_text(encoding="utf-8")
    assert payload["market_emotion"] == {
        "core_market_emotion_score": -5.0,
        "normal_limit_up_count": 1,
        "normal_limit_down_count": 1,
        "normal_break_limit_rate": 0.0,
        "normal_highest_board": None,
        "normal_limit_premium": 10.0,
        "st_speculation_score": 20.0,
        "st_limit_up_count": 2,
        "st_limit_down_count": 0,
        "st_highest_board": None,
    }
    assert "## 普通股短线情绪" in markdown
    assert "## ST 投机情绪" in markdown
    assert "交易结论：不因 ST 活跃提高普通龙头战法仓位" in markdown


def test_report_degrades_to_observation_when_limit_prices_mismatch_new_rules(tmp_path: Path) -> None:
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
            ("20260706", 1, 1, "FULL", None, None, "2026-07-06T15:00:00+00:00"),
        )
        conn.execute(
            "INSERT INTO stock_universe ("
            "ts_code, symbol, name, exchange, market, list_date, "
            "is_st, is_delisting_risk, included, excluded_reason"
            ") VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)",
            ("600001.SH", "600001", "ST风险", "SSE", "主板", "20200101", 1, 0, 1, None),
        )
        conn.execute(
            "INSERT INTO stk_limit_prices (trade_date, ts_code, pre_close, up_limit, down_limit) "
            "VALUES (?, ?, ?, ?, ?)",
            ("20260706", "600001.SH", 10.0, 10.5, 9.5),
        )

    snapshot = generate_report(db_path, "20260706", report_dir)

    payload = json.loads((report_dir / "20260706_report.json").read_text(encoding="utf-8"))
    markdown = (report_dir / "20260706_report.md").read_text(encoding="utf-8")
    assert not snapshot.allow_new_position
    assert payload["new_rule_compatibility"]["data_rule_match"] is False
    assert payload["new_rule_compatibility"]["system_action"] == "DEGRADE_TO_OBSERVATION"
    assert any("DATA_RULE_MISMATCH" in item for item in payload["risk_blocks"])
    assert "- 数据源涨跌停价是否匹配新规：否" in markdown
    assert "- 系统动作：降级为观察" in markdown