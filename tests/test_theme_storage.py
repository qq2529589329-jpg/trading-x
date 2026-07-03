from pathlib import Path
import sqlite3

from trading_x.db import init_db
from trading_x.theme_models import ThemeMember
from trading_x.theme_storage import persist_theme_members


def test_persist_theme_members_upserts_theme_members(tmp_path: Path) -> None:
    db_path = tmp_path / "trading_x.db"
    init_db(db_path)
    old_member = ThemeMember(
        ts_code="300124.SZ",
        name="汇川技术",
        industry="自动化设备",
        theme_primary="机器人",
        theme_tags="机器人;智能制造",
        theme_source="manual",
        confidence="MEDIUM",
        updated_at="2026-06-30",
        notes="旧备注",
    )
    new_member = ThemeMember(
        ts_code="300124.SZ",
        name="汇川技术",
        industry="自动化设备",
        theme_primary="AI应用",
        theme_tags="AI应用;智能制造",
        theme_source="manual",
        confidence="MEDIUM",
        updated_at="2026-06-30",
        notes="新备注",
    )

    persist_theme_members(db_path, [old_member, new_member])

    with sqlite3.connect(db_path) as conn:
        row = conn.execute(
            "SELECT theme_primary, theme_tags, notes FROM theme_members WHERE ts_code = ?",
            ("300124.SZ",),
        ).fetchone()

    assert row == ("AI应用", "AI应用;智能制造", "新备注")
