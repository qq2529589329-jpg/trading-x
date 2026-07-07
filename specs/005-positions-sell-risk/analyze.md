# Analysis: Positions Sell Risk MVP

## Constitution Alignment

- Structured positions are required before sell-side alerts.
- Replay and watch must not infer held positions from candidate plans or alerts.
- Sell-side alerts are still alerts only; broker write APIs and automatic orders remain out of scope.
- Input SHA-256 is required for position import reproducibility.

## Spec Consistency

- `spec.md` requires no `SELL_TRIGGER` without a same-date position row.
- `data-model.md` provides `positions` and `position_import_runs` as the machine truth.
- `tasks.md` keeps parser, persistence, sell semantics, and regression verification separate.
- `contracts/position-ledger-schema.json` requires `available_shares`, which is needed for T+1 risk handling.

## Boundary Check

- `002-intraday-replay-mvp` remains the buy-side replay baseline.
- `003-intraday-live-watch` remains read-only watch.
- `004-real-provider-evaluation` remains source evaluation only.
- `005-positions-sell-risk` is the first specification line where sell-side alert names may exist.

## Result

No contradictions found across the specification artifacts.

## Completed Consistency Check

- Position import writes structured positions rows and import-run reproducibility metadata before sell-side replay runs.
- No-position stop breaks remain buy-plan invalidation only: ENTRY_CANCELLED, not sell-side alerts.
- Held-position stop breaks emit SELL_TRIGGER when `available_shares` > 0 and lock the same-day terminal alert in intraday_alert_locks.
- Held positions with `available_shares` = 0 emit risk-only RISK_ALERT / SELL_BLOCKED_T1_NO_AVAILABLE_SHARES, not executable sell triggers.
- Buy-side Replay MVP reason codes remain stable on the fixed data/replay/20260630.csv fixture.
- Verification completed with uv run pytest -q, uv run pyright, uv run ruff check, one CLI position import, one Replay MVP fixture run, and one stop-break sell replay run.
