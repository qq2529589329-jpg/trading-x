# Provider Evaluation Runbook

## Current Boundary

Real provider adapters remain disabled in this specification. `watch` still uses fake replay-style input only.

## Plan Symbol Export

After materializing intraday plans, export the exact planned symbols for provider sampling:

```powershell
uv run python -m trading_x plans symbols --date YYYYMMDD --strategy A_SPACE_LEADER
uv run python -m trading_x plans symbols --date YYYYMMDD --strategy B_CAPACITY_LEADER
```

Use this output as the provider sample universe. Do not type symbols from Markdown reports.

## Manual Evaluation Command

Capture provider rows into a normalized JSON sample file that matches `contracts/provider-snapshot-sample-schema.json`, then run evaluation explicitly:

```powershell
uv run python -m trading_x provider-evaluate --source mootdx --date YYYYMMDD --symbols 300001.SZ,600001.SH --sample data/provider_samples/YYYYMMDD_mootdx.json --output-dir reports/provider_eval --compliance-use-status unknown
uv run python -m trading_x provider-evaluate --source tencent_snapshot --date YYYYMMDD --symbols 300001.SZ,600001.SH --sample data/provider_samples/YYYYMMDD_tencent_snapshot.json --output-dir reports/provider_eval --compliance-use-status unknown
```

The command writes provider evaluation artifacts only. It must not write `intraday_alerts`, `intraday_alert_locks`, `intraday_plans`, orders, positions, or watch alerts.

## Replay CSV Export

After a sample validates, export it to the Replay MVP CSV contract explicitly:

```powershell
uv run python -m trading_x provider-export-replay --source mootdx --date YYYYMMDD --sample data/provider_samples/YYYYMMDD_mootdx.json --output data/replay/YYYYMMDD.csv
```

This is offline normalization only. It does not enable live watch or choose a default provider.

Real source adapters remain disabled until a later specification proves field completeness, compliance-use status, and fake watch parity.
