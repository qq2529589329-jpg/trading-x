# A_GAP_CONTINUATION Month Filter Check

Date: 2026-07-08
run_id: research-4add1fabaa2bea1a

## Purpose

Check whether `A_GAP_CONTINUATION_CANDIDATE` is driven by only a few months, especially the weak `202602` sample.

This is research only. It does not change trading rules, tune parameters, or turn the watch bucket into a filled trade.

## Comparison

| scenario | horizon | n | avg | median | win_rate |
|---|---:|---:|---:|---:|---:|
| all | 1 | 60 | 1.9101% | 1.4469% | 66.6667% |
| all | 3 | 59 | 4.2077% | 2.5974% | 66.1017% |
| all | 5 | 57 | 1.6761% | 2.6395% | 56.1404% |
| all | 10 | 52 | 3.5035% | 2.5511% | 53.8462% |
| exclude_202602 | 1 | 58 | 1.9780% | 1.8672% | 67.2414% |
| exclude_202602 | 3 | 57 | 4.3518% | 3.2240% | 64.9123% |
| exclude_202602 | 5 | 55 | 1.9657% | 3.1816% | 58.1818% |
| exclude_202602 | 10 | 50 | 4.2283% | 4.1661% | 56.0000% |
| liquid_months_n>=5 | 1 | 57 | 1.8995% | 1.4494% | 66.6667% |
| liquid_months_n>=5 | 3 | 57 | 4.3518% | 3.2240% | 64.9123% |
| liquid_months_n>=5 | 5 | 55 | 1.9657% | 3.1816% | 58.1818% |
| liquid_months_n>=5 | 10 | 50 | 4.2283% | 4.1661% | 56.0000% |

`liquid_months_n>=5`: `202603,202604,202605,202606`.

## Conclusion

1. Removing `202602` improves 5D/10D average return, median return, and win rate.
2. `liquid_months_n>=5` is almost identical to `exclude_202602`, because the current low-sample months are mainly `202602` and long-horizon-incomplete `202607`.
3. The evidence supports that month context affects A_GAP quality, but samples are still concentrated in 2026. This should not become a trading gate yet.

## Next Step

Add a monthly stability table for `A_GAP_CONTINUATION_CANDIDATE`: each month should show whether 1D/3D/5D/10D are positive, median-positive, and sufficiently sampled. Only discuss strategy gating after that stability report survives.
