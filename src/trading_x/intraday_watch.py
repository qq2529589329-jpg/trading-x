from collections.abc import Collection, Iterable, Mapping
from dataclasses import dataclass
from pathlib import Path
import sqlite3
from typing import Protocol, Self

from trading_x.intraday_alerts import disable_invalid_plans, evaluate_replay, load_plans
from trading_x.intraday_models import IntradayAlert, REQUIRED_REPLAY_COLUMNS, ReplayBar
from trading_x.intraday_replay_csv import bar_from_replay_row

IntradaySnapshot = ReplayBar


class IntradayProviderInputError(ValueError):
    reason_code: str

    def __init__(self, reason_code: str) -> None:
        self.reason_code = reason_code
        super().__init__(reason_code)


class IntradayDataProvider(Protocol):
    def snapshots(self, symbols: Collection[str]) -> list[IntradaySnapshot]: ...


@dataclass(frozen=True, slots=True)
class FakeIntradayProvider:
    rows: tuple[IntradaySnapshot, ...]

    @classmethod
    def from_rows(cls, rows: Iterable[Mapping[str, str]]) -> Self:
        snapshots: list[IntradaySnapshot] = []
        for row in rows:
            missing = sorted(REQUIRED_REPLAY_COLUMNS - set(row))
            if missing:
                raise IntradayProviderInputError(
                    "WATCH_SNAPSHOT_MISSING_REQUIRED_COLUMNS: " + ",".join(missing)
                )
            try:
                snapshots.append(bar_from_replay_row(row))
            except (KeyError, TypeError, ValueError) as exc:
                raise IntradayProviderInputError("WATCH_SNAPSHOT_INVALID_ROW") from exc
        return cls(tuple(snapshots))

    def snapshots(self, symbols: Collection[str]) -> list[IntradaySnapshot]:
        return [row for row in self.rows if row.ts_code in symbols]


def run_fake_watch(
    db_path: Path,
    trade_date: str,
    provider: IntradayDataProvider,
) -> list[IntradayAlert]:
    with sqlite3.connect(db_path) as conn:
        conn.row_factory = sqlite3.Row
        plans = load_plans(conn, trade_date)
        disable_invalid_plans(conn, plans)
        active_plans = [plan for plan in plans if plan.is_valid]
        snapshots = provider.snapshots({plan.ts_code for plan in active_plans})
        return evaluate_replay(conn, active_plans, snapshots)
