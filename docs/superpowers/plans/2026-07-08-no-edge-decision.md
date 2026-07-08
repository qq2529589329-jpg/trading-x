# 2026-07-08 No-Edge Decision

## Decision

Status: `STATIC_EDGE_FAIL`

Do not run walk-forward yet. Do not optimize thresholds, filters, position sizing, or stop rules yet.

## Evidence

Backtest trust gate passed:

```text
backtest_trust_audit=PASS run_id=research-4add1fabaa2bea1a issues=0
```

Static edge report:

```text
research_edge=SUCCESS run_id=research-4add1fabaa2bea1a buy_filled=102 benchmark=430
```

Overall `BUY_FILLED` excess versus all-order candidate benchmark:

| Horizon | BUY_FILLED avg | Benchmark avg | Excess avg |
|---:|---:|---:|---:|
| 1 | -0.0933% | 0.2959% | -0.3892% |
| 3 | -0.8241% | 0.3382% | -1.1623% |
| 5 | -0.0648% | 0.2913% | -0.3562% |
| 10 | -0.9957% | 2.0079% | -3.0036% |

## Read

The current `BUY_FILLED` rule does not show edge on the trusted static sample. The sample is also concentrated in `2026` and `HOT`, so there is no useful year/regime diversity for walk-forward yet.

The strongest warning is that `OPEN_ABOVE_ENTRY_HIGH` is positive in the benchmark split while filled trades are negative. That suggests the current entry discipline may be excluding stronger continuations or entering weaker breakouts. This is a hypothesis to test, not a reason to optimize parameters.

## Next Allowed Work

1. Diagnose `BUY_FILLED` versus `OPEN_ABOVE_ENTRY_HIGH` using existing trusted backtest data.
2. Form one revised entry hypothesis before changing code.
3. Re-run static edge after the hypothesis is implemented.
4. Only if static edge turns positive, proceed to 1Y/2Y walk-forward.

## Not Allowed Yet

- No walk-forward.
- No parameter search.
- No threshold tuning.
- No position or stop optimization.
- No strategy promotion based on this run.