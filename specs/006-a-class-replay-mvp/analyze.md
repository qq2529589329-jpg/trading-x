# Analyze: A-Class Replay MVP

## Consistency Check

- Constitution vs spec: aligned. No live watch, no sell semantics, no Markdown-derived prices.
- Spec vs plan: aligned. A-class replay is explicit via `--strategy`; default B behavior remains the source of 002 compatibility.
- Plan vs tasks: aligned. Tasks cover strategy parameterization, A-specific reason code, CLI surface, and verification.
- 002 boundary: aligned. A-class support is a new explicit strategy path and does not change B-class default replay.

## Open Constraints

- `intraday_replay_runs` does not store `strategy_type`; this MVP keeps the existing schema to avoid a schema change. If same-date A/B replay audit ambiguity becomes material, add `strategy_type` in a later spec.
- A-class trigger rules are intentionally minimal. A_STRONG/L3/realtime semantics remain out of scope.

## Daily Shortcut Check

- `replay --materialize` reuses existing structured plan materialization; no Markdown parsing or new data source is introduced.
- Default strategy remains B-class unless `--strategy A_SPACE_LEADER` is supplied.
