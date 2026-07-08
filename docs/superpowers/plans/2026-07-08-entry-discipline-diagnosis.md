# 2026-07-08 Entry Discipline Diagnosis

## Scope

This diagnosis uses the trusted research run only:

```text
run_id=research-4add1fabaa2bea1a
strategy_type=A_SPACE_LEADER
backtest_trust_audit=PASS issues=0
candidate_count=440 order_count=440 trade_count=102
```

No strategy logic was changed. No threshold tuning was performed.

## Rule Boundary

For this run, `A_SPACE_LEADER` materializes the plan from the signal day's limit-up price:

```text
entry_low = signal_up_limit
entry_high = signal_up_limit
breakout_price = signal_up_limit
```

Decision flow:

```text
BUY_FILLED
= next_open <= signal_up_limit AND next_high >= signal_up_limit

OPEN_ABOVE_ENTRY_HIGH
= next_open > signal_up_limit
```

So `OPEN_ABOVE_ENTRY_HIGH` is not a random high-chase bucket. It is the bucket where the next day opens above the prior signal day's limit-up plan price.

## Core Finding

The current rule cancels the stronger continuation bucket and buys the weaker retest bucket.

| Bucket | Orders | 1D avg | 3D avg | 5D avg | 10D avg |
|---|---:|---:|---:|---:|---:|
| BUY_FILLED | 120 | -0.0933% | -0.8241% | -0.0648% | -0.9957% |
| OPEN_ABOVE_ENTRY_HIGH | 245 | 0.9095% | 1.5697% | 1.1254% | 3.0236% |

The gap survives an executable-price check. If `OPEN_ABOVE_ENTRY_HIGH` is measured from the actual next open instead of from the close, its next-close return is still positive:

| Bucket | Entry metric | N | Avg return | Win rate |
|---|---|---:|---:|---:|
| BUY_FILLED | fill to next close | 120 | -0.0933% | 41.6667% |
| BUY_FILLED | open to next close | 120 | 1.7192% | 60.0000% |
| OPEN_ABOVE_ENTRY_HIGH | open to next close | 243 | 1.0598% | 56.7901% |
| OPEN_ABOVE_ENTRY_HIGH | close to next close | 243 | 0.9095% | 51.4403% |

## Shape Difference

| Metric | BUY_FILLED | OPEN_ABOVE_ENTRY_HIGH |
|---|---:|---:|
| avg open gap vs plan | -1.3720% | 2.9730% |
| avg high gap vs plan | 4.8275% | 6.8671% |
| avg close vs open | 2.1664% | 0.0914% |
| close > open rate | 65.0000% | 53.4694% |

Read: `BUY_FILLED` often recovers intraday after a weak open, but that recovery does not persist. `OPEN_ABOVE_ENTRY_HIGH` does not need a strong intraday candle; it starts stronger and preserves strength into later horizons.

## Candidate Quality Difference

| Metric | BUY_FILLED | OPEN_ABOVE_ENTRY_HIGH |
|---|---:|---:|
| avg rank | 3.0833 | 3.0327 |
| avg theme_strength_score | 69.7500 | 74.2632 |
| avg total_mv | 7,331,423.94 | 11,188,076.91 |
| avg turnover_rate | 16.5610 | 12.4762 |
| avg signal amount | 6,289,224.50 | 7,006,051.77 |

Read: the canceled high-open bucket has stronger theme score, larger capitalization, lower turnover, and higher signal-day amount. That is more consistent with institutionally stronger continuation than with pure noise chasing.

## Capital Constraint Note

`BUY_FILLED` has 120 orders but only 102 actual trades. The 18 missing trades all have implied 100-share board-lot size of zero under the current 10,000 cash cap.

```text
missing BUY_FILLED trades=18
avg implied fill=300.28
min implied fill=101.42
max implied fill=891.00
zero_share_count=18
```

This is not the main no-edge cause, but it matters for later capital model review.

## Hypothesis

The current entry discipline is too conservative for `A_SPACE_LEADER` daily-proxy data.

It blocks next-day high-open continuation, even though this bucket is the only large bucket with positive follow-through. It then buys weaker flat/low-open retests, which show intraday recovery but negative follow-through.

## Next Testable Change

Do not optimize thresholds yet. Test exactly one structural hypothesis first:

```text
A_GAP_CONTINUATION_WATCH
Allow OPEN_ABOVE_ENTRY_HIGH only when:
1. next_open > signal_up_limit;
2. next_open gap is not extreme;
3. next day does not immediately fail back below signal_up_limit;
4. candidate has strong theme/liquidity evidence.
```

The first implementation should be a separate reason path, not a replacement for `BUY_FILLED`:

```text
OPEN_ABOVE_ENTRY_HIGH -> A_GAP_CONTINUATION_CANDIDATE
```

Acceptance gate remains unchanged:

```text
static edge first; walk-forward only after positive static edge; optimization last.
```