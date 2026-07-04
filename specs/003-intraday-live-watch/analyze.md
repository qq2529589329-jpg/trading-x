# Analyze: Intraday Live Watch

## Consistency Checks

- Constitution: aligned with replay-before-live and no-sell-without-positions principles.
- Spec to plan: aligned. Both require fake provider parity before real provider work.
- Data model to contract: aligned. Snapshot schema uses the Replay MVP bar field set.
- Tasks to spec: aligned. Tasks start with tests and fake provider; real providers remain evaluation-only.

## Deliberate Non-Goals

- No automatic orders.
- No `SELL_TRIGGER`.
- No positions, T+1, available-share guidance, or sell advice.
- No A-class or L3 order-book behavior.
- No all-market scan.
- No real provider default source in the first implementation.
- No new watch-run table until fake-provider behavior proves the metadata need.

## Open Questions For Implementation

- Whether the watch command should run one snapshot batch and exit, or loop with a bounded polling count for fake-provider tests.
- Whether provider source evaluation belongs in docs only or should have a small CLI report.
- Whether later real provider code should live under `src/trading_x/intraday_provider_*.py` or a dedicated package after more than one source is proven useful.

## Current Recommendation

Implement the first slice as fake-provider parity:

1. Build provider snapshots from replay fixture CSV rows.
2. Reuse the existing B-class evaluation path.
3. Assert alert type and `reason_code` parity against replay fixture expectations.
4. Keep the CLI read-only and fake-provider-only until the parity tests pass in CI.
