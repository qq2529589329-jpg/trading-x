from pathlib import Path
import sqlite3

from trading_x.theme_models import ThemeMember


def persist_theme_members(db_path: Path, members: list[ThemeMember]) -> None:
    with sqlite3.connect(db_path) as conn:
        conn.executemany(
            "INSERT INTO theme_members ("
            "ts_code, name, industry, theme_primary, theme_tags, theme_tier, theme_weight, "
            "theme_source, confidence, updated_at, notes"
            ") VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?) "
            "ON CONFLICT(ts_code) DO UPDATE SET "
            "name = excluded.name, industry = excluded.industry, "
            "theme_primary = excluded.theme_primary, theme_tags = excluded.theme_tags, "
            "theme_tier = excluded.theme_tier, theme_weight = excluded.theme_weight, "
            "theme_source = excluded.theme_source, confidence = excluded.confidence, "
            "updated_at = excluded.updated_at, notes = excluded.notes",
            [
                (
                    member.ts_code,
                    member.name,
                    member.industry,
                    member.theme_primary,
                    member.theme_tags,
                    member.theme_tier,
                    member.theme_weight,
                    member.theme_source,
                    member.confidence,
                    member.updated_at,
                    member.notes,
                )
                for member in members
            ],
        )
