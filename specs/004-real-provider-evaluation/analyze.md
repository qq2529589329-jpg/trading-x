# Analyze: Real Provider Evaluation

## Constitution Alignment

- `Discipline Before Recommendation`: aligned. The feature writes evaluation evidence only and does not produce trade instructions.
- `Structured Plans Before Alerts`: aligned. The feature does not produce alerts and does not parse Markdown plans.
- `Replay Before Live Watch`: aligned. Real provider work remains evaluation-only.
- `Reproducible Runs Before Tuning`: aligned. Provider decisions depend on captured field evidence and reason codes.
- `No Sell Semantics Without Positions`: aligned. No sell or position semantics are introduced.

## Spec / Plan / Tasks Consistency

- The spec requires evaluation isolation; plan and tasks keep outputs to provider evaluation artifacts.
- The spec requires cumulative volume and timestamp gates; data model, contract, and tasks include both.
- The spec requires replay and fake watch stability; tasks include full replay and parity verification.
- The spec defers real-provider watch enablement; plan and tasks keep adapters disabled.

## Boundary Check

- No automatic orders.
- No `SELL_TRIGGER`.
- No positions or T+1 guidance.
- No A-class or L3 scope.
- No all-market scanning.
- No change to `watch` default provider.

## Open Decisions For Implementation

- Whether provider evaluation artifacts should live under `data/provider_eval/` or `reports/provider_eval/`.
- Whether raw provider payloads are persisted as hashes only or saved in full under an explicit user-controlled flag.

Both decisions can be made during implementation without changing strategy semantics.
