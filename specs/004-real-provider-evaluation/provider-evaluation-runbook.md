# Provider Evaluation Runbook

## Current Boundary

Real provider adapters remain disabled in this specification. `watch` still uses fake replay-style input only.

## Manual Evaluation Command

Capture provider rows into a normalized JSON sample file that matches `contracts/provider-snapshot-sample-schema.json`, then run evaluation explicitly:

```powershell
uv run python -m trading_x provider-evaluate --source mootdx --date YYYYMMDD --symbols 300001.SZ,600001.SH --sample data/provider_samples/YYYYMMDD_mootdx.json --output-dir reports/provider_eval --compliance-use-status unknown
uv run python -m trading_x provider-evaluate --source tencent_snapshot --date YYYYMMDD --symbols 300001.SZ,600001.SH --sample data/provider_samples/YYYYMMDD_tencent_snapshot.json --output-dir reports/provider_eval --compliance-use-status unknown
```

The command writes provider evaluation artifacts only. It must not write `intraday_alerts`, `intraday_alert_locks`, `intraday_plans`, orders, positions, or watch alerts.

Real source adapters remain disabled until a later specification proves field completeness, compliance-use status, and fake watch parity.
