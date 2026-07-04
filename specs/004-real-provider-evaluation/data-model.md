# Data Model: Real Provider Evaluation

## Entity: ProviderEvaluationRun

Represents one evaluation attempt for a candidate real intraday source.

| Field | Type | Required | Notes |
| --- | --- | --- | --- |
| `id` | string | yes | Stable run identifier, such as date plus source plus timestamp. |
| `trade_date` | string | yes | `YYYYMMDD`. |
| `source` | string | yes | `mootdx` or `tencent_snapshot`. |
| `symbols_requested` | array[string] | yes | Symbols requested from the source. |
| `symbols_covered` | array[string] | yes | Symbols with valid source responses. |
| `symbols_missing` | array[string] | yes | Requested symbols without valid source responses. |
| `sample_count` | integer | yes | Number of normalized samples accepted for analysis. |
| `field_status` | object | yes | Per-field status for required evidence. |
| `latency_ms_min` | integer | no | Minimum observed request latency. |
| `latency_ms_p50` | integer | no | Median observed request latency. |
| `latency_ms_max` | integer | no | Maximum observed request latency. |
| `stability_status` | string | yes | `pass`, `fail`, or `unmeasured`. |
| `compliance_use_status` | string | yes | `approved`, `rejected`, or `unknown`. |
| `decision` | string | yes | `disabled_for_live_watch`, `disabled_for_buy_trigger`, or `candidate_only`. |
| `reason_codes` | array[string] | yes | Machine-readable reasons for the decision. |
| `started_at` | string | yes | ISO-like local timestamp. |
| `ended_at` | string | yes | ISO-like local timestamp. |

## Entity: ProviderSnapshotSample

One normalized provider snapshot row. It uses the same market fields as replay/fake watch snapshots plus evaluation evidence.

| Field | Type | Required | Notes |
| --- | --- | --- | --- |
| `trade_date` | string | yes | `YYYYMMDD`. |
| `quote_time` | string | yes | Provider or exchange timestamp mapped to local quote time. |
| `ts_code` | string | yes | Stock code in existing project format. |
| `price` | number | yes | Current traded price. |
| `amount_since_open` | number | yes | Cumulative turnover amount from open. |
| `volume_since_open` | number | yes | Cumulative traded volume from open. |
| `bar_high` | number | yes | Intraday or current-bar high used by the provider. |
| `bar_low` | number | yes | Intraday or current-bar low used by the provider. |
| `previous_close` | number | no | Provider previous close, if available. |
| `limit_up` | number | no | Up-limit price, if available. |
| `limit_down` | number | no | Down-limit price, if available. |
| `source` | string | yes | Candidate provider source. |
| `latency_ms` | integer | yes | Request latency observed for this sample. |
| `raw_payload_sha256` | string | no | Hash of raw payload when raw data is available. |
| `validation_status` | string | yes | `accepted` or `rejected`. |
| `reason_codes` | array[string] | yes | Machine-readable validation reasons. |

## Decision Rules

- Missing `volume_since_open` adds `PROVIDER_VOLUME_MISSING` and sets decision to `disabled_for_buy_trigger`.
- Missing or unordered `quote_time` adds `PROVIDER_TIMESTAMP_UNTRUSTED` and sets decision to `disabled_for_live_watch`.
- Missing coverage for requested symbols adds `PROVIDER_COVERAGE_PARTIAL` and keeps the source disabled.
- `compliance_use_status = unknown` adds `PROVIDER_COMPLIANCE_UNKNOWN` and keeps the source disabled.
