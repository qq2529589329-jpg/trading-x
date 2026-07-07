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
