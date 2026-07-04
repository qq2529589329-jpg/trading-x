# Provider Evaluation Checklist

## Boundary

Real intraday providers stay disabled until one source proves field completeness against this checklist. `watch` may only run through fake replay-style snapshots before that proof exists.

## Candidate Sources

| Source | Status | Notes |
| --- | --- | --- |
| mootdx | Not approved | Needs sampled snapshots for all required fields. |
| Tencent snapshot | Not approved | Needs sampled snapshots for all required fields. |

## Required Snapshot Fields

| Field | Required Evidence | Approval Gate |
| --- | --- | --- |
| timestamp | Snapshot carries an exchange-time or provider-time value precise enough to order ticks. | Must map to `quote_time`. |
| price | Current traded price is present and positive. | Must map to `price`. |
| cumulative amount | 09:30-to-now cumulative turnover amount is present and monotonic. | Must map to `amount_since_open`. |
| cumulative volume | 09:30-to-now cumulative traded volume is present and monotonic. | Must map to `volume_since_open`; provider is rejected if missing. |
| high/low | Intraday or current-bar high/low are present and internally consistent. | Must map to `bar_high` and `bar_low`. |
| previous close | Official previous close is present or can be joined from trusted daily/limit-price tables. | Must not override `PreCloseProvider` without reconciliation. |
| limit price | Up/down limit price is present or can be joined from trusted daily limit-price tables. | Must be available before live risk rules depend on it. |
| coverage | All symbols from active `intraday_plans` can be queried. | Partial coverage keeps provider disabled. |
| latency | Delay is measured during 09:30-10:00 and 14:30-15:00 windows. | Threshold must be documented before approval. |
| stability | Missing/invalid snapshots, retries, and disconnects are counted. | Failure rate must be documented before approval. |
| compliance use | Usage boundary is reviewed for redistribution, automation, and rate limits. | Unknown compliance status keeps provider disabled. |

## Sampling Record

For each source, record at least one trading-day sample before approval:

| Source | Date | Symbols | timestamp | price | amount | volume | high/low | pre-close | limit-price | coverage | latency | stability | compliance | Decision |
| --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- | --- |
| mootdx | TBD | TBD | TBD | TBD | TBD | TBD | TBD | TBD | TBD | TBD | TBD | TBD | TBD | Disabled |
| Tencent snapshot | TBD | TBD | TBD | TBD | TBD | TBD | TBD | TBD | TBD | TBD | TBD | TBD | TBD | Disabled |

## Approval Rule

A real provider may be enabled only after all required fields are proven complete, conversion to `IntradaySnapshot` is covered by tests, and fake-provider parity remains green.
