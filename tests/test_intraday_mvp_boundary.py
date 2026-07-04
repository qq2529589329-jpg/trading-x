from pathlib import Path
import sys

import pytest

from trading_x import cli


def test_intraday_replay_mvp_runtime_keeps_deferred_boundaries() -> None:
    source_paths = sorted(Path("src/trading_x").glob("intraday*.py"))
    forbidden_tokens = (
        "SELL_TRIGGER",
        "A_STRONG",
        "mootdx",
        "tencent",
        "Tencent",
        "realtime",
        "real_time",
        "live_watch",
        "LiveWatch",
        "SELL_WARN",
        "available_shares",
        "entry_date",
        "T+1",
        "T_PLUS_ONE",
        "sell_guidance",
        "SellGuidance",
        "\u53ef\u5356",
    )

    violations = [
        f"{path}:{token}"
        for path in source_paths
        for token in forbidden_tokens
        if token in path.read_text(encoding="utf-8")
    ]

    assert violations == []


def test_intraday_watch_cli_requires_date(monkeypatch: pytest.MonkeyPatch) -> None:
    monkeypatch.setattr(sys, "argv", ["trading_x", "watch"])

    with pytest.raises(SystemExit) as exc_info:
        cli.main()

    assert exc_info.value.code == 2
